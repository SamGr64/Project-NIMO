from __future__ import annotations

import hashlib
import json
import shutil
import uuid

import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from nimo.domain.models import ImportResult
from nimo.ingestion.csv_reader import read_statement_csv
from nimo.ingestion.mappings import detect_mapping
from nimo.ingestion.normalise import normalise_statement
from nimo.storage.database import Database
from nimo.storage.models import SourceFile, Transaction
from nimo.storage.repositories import AccountRepository, TransactionRepository
from nimo.users.workspace import UserWorkspace

IMPORTER_VERSION = "1.0"


class StatementIngestionPipeline:
    """Import one account statement using date-range supersession, never row equality."""

    def __init__(
        self,
        *,
        database: Database,
        workspace: UserWorkspace,
        statement_config: dict[str, Any],
        currency_default: str = "GBP",
    ) -> None:
        self.database = database
        self.workspace = workspace
        self.statement_config = statement_config
        self.currency_default = currency_default
        self.accounts = AccountRepository()
        self.transactions = TransactionRepository()

    def import_csv(
        self,
        path: Path,
        *,
        account_name: str | None = None,
        account_type: str | None = None,
        column_overrides: dict[str, str] | None = None,
    ) -> ImportResult:
        source_path = path.expanduser().resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"Statement file not found: {source_path}")
        digest = _sha256(source_path)

        with self.database.session() as session:
            duplicate = session.scalar(select(SourceFile).where(SourceFile.sha256 == digest))
            if duplicate is not None:
                return ImportResult(
                    source_file_id=duplicate.id,
                    account_id=duplicate.account_id,
                    imported_rows=0,
                    superseded_rows=0,
                    coverage_start=duplicate.coverage_start,
                    coverage_end=duplicate.coverage_end,
                    duplicate_file=True,
                    warnings=["This exact source file was already imported; no rows were added."],
                )

        raw = read_statement_csv(source_path)
        mapping = detect_mapping(raw.columns, self.statement_config, column_overrides)
        frame, metadata, warnings = normalise_statement(
            raw,
            mapping,
            account_name_override=account_name,
            account_type_override=account_type,
            currency_default=self.currency_default,
        )
        coverage_start = min(frame["booking_date"])
        coverage_end = max(frame["booking_date"])

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        stored_name = f"{timestamp}_{digest[:10]}_{source_path.name}"
        stored_path = self.workspace.raw_dir / stored_name
        stored_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, stored_path)

        with self.database.session() as session:
            account = self.accounts.get_or_create(
                session,
                name=metadata.account_name,
                bank_name=metadata.bank_name,
                account_number=metadata.account_number,
                sort_code=metadata.sort_code,
                account_type=metadata.account_type,
                currency=metadata.currency,
                opening_balance=metadata.opening_balance,
            )
            source = SourceFile(
                account_id=account.id,
                original_name=source_path.name,
                stored_path=str(stored_path.relative_to(self.workspace.root)),
                sha256=digest,
                coverage_start=coverage_start,
                coverage_end=coverage_end,
                row_count=len(frame),
                importer_version=IMPORTER_VERSION,
                mapping_json=json.dumps(mapping.as_dict(), sort_keys=True),
                warnings_json=json.dumps(warnings),
            )
            session.add(source)
            session.flush()

            # The newest statement is authoritative for every date in its coverage window.
            # No transaction-level equality rule is used; identical same-day rows are retained.
            superseded = self.transactions.supersede_date_range(
                session,
                account_id=account.id,
                start_date=coverage_start,
                end_date=coverage_end,
                superseding_source_file_id=source.id,
            )

            for row in frame.to_dict(orient="records"):
                running_balance = row.get("running_balance")
                if running_balance is None or pd.isna(running_balance):
                    running_balance = None
                session.add(
                    Transaction(
                        transaction_uid=str(uuid.uuid4()),
                        account_id=account.id,
                        source_file_id=source.id,
                        source_row=int(row["source_row"]),
                        booking_date=row["booking_date"],
                        value_date=row["value_date"],
                        description_raw=str(row["description_raw"]),
                        merchant_normalised=str(row["merchant_normalised"]),
                        amount=float(row["amount"]),
                        currency=str(row["currency"]),
                        running_balance=(
                            None if running_balance is None else float(running_balance)
                        ),
                    )
                )

            return ImportResult(
                source_file_id=source.id,
                account_id=account.id,
                imported_rows=len(frame),
                superseded_rows=superseded,
                coverage_start=coverage_start,
                coverage_end=coverage_end,
                warnings=warnings,
            )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
