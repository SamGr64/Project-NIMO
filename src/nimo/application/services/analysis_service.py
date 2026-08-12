from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy import select

from nimo.analysis.accounts import account_summary, balance_history
from nimo.analysis.cashflow import cashflow_payload
from nimo.analysis.categories import category_summary, category_timeline
from nimo.analysis.overview import compute_overview_metrics, monthly_spending
from nimo.analysis.transfers import TransferDetector
from nimo.categorisation.service import CategorisationService
from nimo.storage.database import Database
from nimo.storage.models import Account
from nimo.storage.repositories import TransactionRepository


class AnalysisService:
    def __init__(
        self,
        *,
        database: Database,
        analysis_config: dict[str, Any],
        categorisation: CategorisationService,
        transfer_detector: TransferDetector,
    ) -> None:
        self.database = database
        self.analysis_config = analysis_config
        self.categorisation = categorisation
        self.transfer_detector = transfer_detector
        self.transactions = TransactionRepository()

    def transaction_frame(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        account_ids: list[int] | None = None,
        category_ids: list[int] | None = None,
    ) -> pd.DataFrame:
        with self.database.session() as session:
            return self.transactions.active_frame(
                session,
                start_date=start_date,
                end_date=end_date,
                account_ids=account_ids,
                category_ids=category_ids,
            )

    def account_opening_balances(self) -> dict[int, float]:
        with self.database.session() as session:
            return {
                account.id: float(account.opening_balance)
                for account in session.scalars(select(Account).where(Account.is_active.is_(True)))
            }

    def refresh(self) -> dict[str, Any]:
        categories = self.categorisation.auto_categorise()
        transfers = self.transfer_detector.detect()
        return {"categories": categories, "transfers": transfers}

    def overview(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        account_ids: list[int] | None = None,
    ):
        frame = self.transaction_frame(
            start_date=start_date,
            end_date=end_date,
            account_ids=account_ids,
        )
        decay = float(
            self.analysis_config.get("metrics", {}).get("recent_weight_decay", 0.85)
        )
        return compute_overview_metrics(
            frame,
            account_opening=self.account_opening_balances(),
            recent_weight_decay=decay,
        )

    def monthly(self, **filters: Any) -> pd.DataFrame:
        return monthly_spending(self.transaction_frame(**filters))

    def accounts(self, **filters: Any) -> pd.DataFrame:
        return account_summary(
            self.transaction_frame(**filters),
            self.account_opening_balances(),
        )

    def balances(self, **filters: Any) -> pd.DataFrame:
        return balance_history(
            self.transaction_frame(**filters),
            self.account_opening_balances(),
        )

    def categories(self, **filters: Any) -> pd.DataFrame:
        return category_summary(self.transaction_frame(**filters))

    def category_timeline(self, **filters: Any) -> pd.DataFrame:
        return category_timeline(self.transaction_frame(**filters))

    def cashflow(self, **filters: Any) -> dict[str, Any]:
        return cashflow_payload(self.transaction_frame(**filters), self.database)
