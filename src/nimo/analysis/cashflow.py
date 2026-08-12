from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd
from sqlalchemy import select

from nimo.domain.models import CashFlowLink
from nimo.storage.database import Database
from nimo.storage.models import Account, Transaction, TransferMatch


def build_cashflow_links(frame: pd.DataFrame) -> list[CashFlowLink]:
    if frame.empty:
        return []
    totals: dict[tuple[str, str, str], float] = defaultdict(float)
    external = frame.loc[frame["transfer_group_id"].isna()].copy()
    for _, row in external.loc[external["amount"] > 0].iterrows():
        source = str(row.get("category_label") or "Income")
        target = str(row["account_name"])
        totals[(source, target, "income")] += float(row["amount"])
    for _, row in external.loc[external["amount"] < 0].iterrows():
        source = str(row["account_name"])
        target = str(row.get("category_label") or "Uncategorised")
        totals[(source, target, "outgoing")] += abs(float(row["amount"]))
    return [
        CashFlowLink(source=source, target=target, value=value, flow_type=flow_type)
        for (source, target, flow_type), value in sorted(totals.items())
        if value > 0
    ]


def internal_transfer_links(database: Database) -> list[CashFlowLink]:
    totals: dict[tuple[str, str], float] = defaultdict(float)
    confidences: dict[tuple[str, str], list[float]] = defaultdict(list)
    with database.session() as session:
        for match in session.scalars(
            select(TransferMatch).where(TransferMatch.is_rejected.is_(False))
        ):
            debit = session.get(Transaction, match.debit_transaction_id)
            credit = session.get(Transaction, match.credit_transaction_id)
            if debit is None or credit is None or not debit.is_active or not credit.is_active:
                continue
            debit_account = session.get(Account, debit.account_id)
            credit_account = session.get(Account, credit.account_id)
            if debit_account is None or credit_account is None:
                continue
            key = (debit_account.name, credit_account.name)
            totals[key] += float(match.amount)
            confidences[key].append(float(match.confidence))
    return [
        CashFlowLink(
            source=source,
            target=target,
            value=value,
            flow_type="internal_transfer",
            confidence=sum(confidences[(source, target)]) / len(confidences[(source, target)]),
        )
        for (source, target), value in sorted(totals.items())
    ]


def cashflow_payload(frame: pd.DataFrame, database: Database) -> dict[str, Any]:
    links = build_cashflow_links(frame) + internal_transfer_links(database)
    nodes = sorted({link.source for link in links} | {link.target for link in links})
    index = {node: position for position, node in enumerate(nodes)}
    return {
        "nodes": nodes,
        "links": [
            {
                "source": index[link.source],
                "target": index[link.target],
                "source_label": link.source,
                "target_label": link.target,
                "value": link.value,
                "flow_type": link.flow_type,
                "confidence": link.confidence,
            }
            for link in links
        ],
    }
