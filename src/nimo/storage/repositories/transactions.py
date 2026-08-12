from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from nimo.storage.models import Account, Category, Transaction


class TransactionRepository:
    def supersede_date_range(
        self,
        session: Session,
        *,
        account_id: int,
        start_date: date,
        end_date: date,
        superseding_source_file_id: int,
    ) -> int:
        result = session.execute(
            update(Transaction)
            .where(
                Transaction.account_id == account_id,
                Transaction.is_active.is_(True),
                Transaction.booking_date >= start_date,
                Transaction.booking_date <= end_date,
            )
            .values(
                is_active=False,
                superseded_by_source_file_id=superseding_source_file_id,
                transfer_group_id=None,
            )
        )
        return int(result.rowcount or 0)

    def active_frame(
        self,
        session: Session,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        account_ids: list[int] | None = None,
        category_ids: list[int] | None = None,
    ) -> pd.DataFrame:
        statement = (
            select(
                Transaction.id,
                Transaction.transaction_uid,
                Transaction.account_id,
                Account.name.label("account_name"),
                Account.bank_name,
                Account.account_type,
                Transaction.source_file_id,
                Transaction.source_row,
                Transaction.booking_date,
                Transaction.value_date,
                Transaction.description_raw,
                Transaction.merchant_normalised,
                Transaction.amount,
                Transaction.currency,
                Transaction.running_balance,
                Transaction.category_id,
                Category.slug.label("category_slug"),
                Category.label.label("category_label"),
                Transaction.category_source,
                Transaction.category_confidence,
                Transaction.transfer_group_id,
            )
            .join(Account, Transaction.account_id == Account.id)
            .outerjoin(Category, Transaction.category_id == Category.id)
            .where(Transaction.is_active.is_(True))
            .order_by(Transaction.booking_date, Transaction.id)
        )
        if start_date is not None:
            statement = statement.where(Transaction.booking_date >= start_date)
        if end_date is not None:
            statement = statement.where(Transaction.booking_date <= end_date)
        if account_ids:
            statement = statement.where(Transaction.account_id.in_(account_ids))
        if category_ids:
            statement = statement.where(Transaction.category_id.in_(category_ids))

        rows = session.execute(statement).mappings().all()
        frame = pd.DataFrame(rows)
        if not frame.empty:
            frame["booking_date"] = pd.to_datetime(frame["booking_date"])
            if "value_date" in frame:
                frame["value_date"] = pd.to_datetime(frame["value_date"])
            frame["amount"] = frame["amount"].astype(float)
            frame["running_balance"] = pd.to_numeric(frame["running_balance"], errors="coerce")
        return frame
