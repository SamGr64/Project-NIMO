from __future__ import annotations

import json
import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy import or_, select

from nimo.storage.database import Database
from nimo.storage.models import Transaction, TransferMatch


class TransferDetector:
    """Detect, confirm and reject internal-account transfer pairs.

    Automatic matches are rebuilt whenever detection runs. Manual confirmations and
    rejections are durable while both referenced transactions remain active.
    """

    def __init__(self, *, database: Database, analysis_config: dict[str, Any]) -> None:
        self.database = database
        transfer_config = analysis_config.get("transfers", {})
        self.maximum_gap = int(transfer_config.get("maximum_date_gap_days", 2))
        self.minimum_confidence = float(transfer_config.get("minimum_confidence", 0.75))
        self.tokens = [str(token).lower() for token in transfer_config.get("description_tokens", [])]

    def detect(self) -> dict[str, int | float]:
        matched = 0
        preserved_manual = 0
        rejected_pairs: set[frozenset[int]] = set()
        with self.database.session() as session:
            # Remove stale decisions and prior automatic results. Manual confirmations
            # and rejections survive refreshes while both source transactions are active.
            existing_matches = list(session.scalars(select(TransferMatch)))
            for match in existing_matches:
                debit = session.get(Transaction, match.debit_transaction_id)
                credit = session.get(Transaction, match.credit_transaction_id)
                stale = (
                    debit is None
                    or credit is None
                    or not debit.is_active
                    or not credit.is_active
                )
                if stale or not match.is_manual:
                    if debit is not None and debit.transfer_group_id == match.group_id:
                        debit.transfer_group_id = None
                    if credit is not None and credit.transfer_group_id == match.group_id:
                        credit.transfer_group_id = None
                    session.delete(match)
                    continue

                pair = frozenset({match.debit_transaction_id, match.credit_transaction_id})
                if match.is_rejected:
                    debit.transfer_group_id = None
                    credit.transfer_group_id = None
                    rejected_pairs.add(pair)
                else:
                    debit.transfer_group_id = match.group_id
                    credit.transfer_group_id = match.group_id
                    preserved_manual += 1
            session.flush()

            rows = list(
                session.scalars(
                    select(Transaction)
                    .where(
                        Transaction.is_active.is_(True),
                        Transaction.amount != 0,
                        Transaction.transfer_group_id.is_(None),
                    )
                    .order_by(Transaction.booking_date, Transaction.id)
                )
            )
            credits: dict[int, list[Transaction]] = defaultdict(list)
            debits: dict[int, list[Transaction]] = defaultdict(list)
            for row in rows:
                cents = int(round(abs(row.amount) * 100))
                if row.amount > 0:
                    credits[cents].append(row)
                else:
                    debits[cents].append(row)

            used_credits: set[int] = set()
            for cents, debit_rows in debits.items():
                candidate_credits = credits.get(cents, [])
                for debit in debit_rows:
                    best: tuple[float, int, Transaction, dict[str, Any]] | None = None
                    for credit in candidate_credits:
                        pair = frozenset({debit.id, credit.id})
                        if (
                            credit.id in used_credits
                            or credit.account_id == debit.account_id
                            or pair in rejected_pairs
                        ):
                            continue
                        gap = abs((credit.booking_date - debit.booking_date).days)
                        if gap > self.maximum_gap:
                            continue
                        combined = f"{debit.description_raw} {credit.description_raw}".lower()
                        token_hits = [token for token in self.tokens if token in combined]
                        confidence = 0.60
                        confidence += 0.25 if gap == 0 else 0.18 if gap == 1 else 0.10
                        if token_hits:
                            confidence += 0.15
                        confidence = min(1.0, confidence)
                        evidence = {
                            "exact_amount": True,
                            "date_gap_days": gap,
                            "description_tokens": token_hits,
                            "method": "automatic",
                        }
                        candidate = (confidence, -gap, credit, evidence)
                        if best is None or candidate[:2] > best[:2]:
                            best = candidate
                    if best is None or best[0] < self.minimum_confidence:
                        continue
                    confidence, negative_gap, credit, evidence = best
                    gap = -negative_gap
                    group_id = str(uuid.uuid4())
                    debit.transfer_group_id = group_id
                    credit.transfer_group_id = group_id
                    used_credits.add(credit.id)
                    session.add(
                        TransferMatch(
                            group_id=group_id,
                            debit_transaction_id=debit.id,
                            credit_transaction_id=credit.id,
                            amount=abs(debit.amount),
                            date_gap_days=gap,
                            confidence=confidence,
                            is_manual=False,
                            is_rejected=False,
                            evidence_json=json.dumps(evidence, sort_keys=True),
                        )
                    )
                    matched += 1
        return {
            "matched_pairs": matched,
            "matched_transactions": matched * 2,
            "preserved_manual_pairs": preserved_manual,
            "rejected_pairs": len(rejected_pairs),
        }

    def confirm_pair(self, first_transaction_id: int, second_transaction_id: int) -> str:
        with self.database.session() as session:
            first = session.get(Transaction, first_transaction_id)
            second = session.get(Transaction, second_transaction_id)
            if first is None or second is None or not first.is_active or not second.is_active:
                raise KeyError("Both transfer transactions must exist and be active")
            if first.account_id == second.account_id:
                raise ValueError("An internal transfer must move between two different accounts")
            if first.amount == 0 or second.amount == 0 or first.amount * second.amount >= 0:
                raise ValueError("A transfer pair requires one debit and one credit")
            if abs(abs(first.amount) - abs(second.amount)) > 0.01:
                raise ValueError("Transfer debit and credit amounts must match")
            debit, credit = (first, second) if first.amount < 0 else (second, first)
            self._remove_matches_for_transactions(session, {debit.id, credit.id})
            group_id = str(uuid.uuid4())
            debit.transfer_group_id = group_id
            credit.transfer_group_id = group_id
            gap = abs((credit.booking_date - debit.booking_date).days)
            session.add(
                TransferMatch(
                    group_id=group_id,
                    debit_transaction_id=debit.id,
                    credit_transaction_id=credit.id,
                    amount=abs(debit.amount),
                    date_gap_days=gap,
                    confidence=1.0,
                    is_manual=True,
                    is_rejected=False,
                    evidence_json=json.dumps({"method": "manual_confirmation"}),
                )
            )
            return group_id

    def unmatch_group(self, group_id: str) -> bool:
        """Persistently reject a transfer match so automatic refresh cannot restore it."""
        with self.database.session() as session:
            match = session.scalar(select(TransferMatch).where(TransferMatch.group_id == group_id))
            if match is None:
                return False
            for transaction_id in (match.debit_transaction_id, match.credit_transaction_id):
                transaction = session.get(Transaction, transaction_id)
                if transaction is not None and transaction.transfer_group_id == group_id:
                    transaction.transfer_group_id = None
            match.is_manual = True
            match.is_rejected = True
            match.confidence = 1.0
            match.evidence_json = json.dumps({"method": "manual_rejection"})
            return True

    @staticmethod
    def _remove_matches_for_transactions(session, transaction_ids: set[int]) -> None:
        matches = list(
            session.scalars(
                select(TransferMatch).where(
                    or_(
                        TransferMatch.debit_transaction_id.in_(transaction_ids),
                        TransferMatch.credit_transaction_id.in_(transaction_ids),
                    )
                )
            )
        )
        for match in matches:
            for transaction_id in (match.debit_transaction_id, match.credit_transaction_id):
                transaction = session.get(Transaction, transaction_id)
                if transaction is not None and transaction.transfer_group_id == match.group_id:
                    transaction.transfer_group_id = None
            session.delete(match)
        session.flush()
