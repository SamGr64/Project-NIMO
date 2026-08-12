from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from nimo.storage.models import Account


class AccountRepository:
    def list(self, session: Session, *, active_only: bool = True) -> list[Account]:
        statement = select(Account).order_by(Account.name)
        if active_only:
            statement = statement.where(Account.is_active.is_(True))
        return list(session.scalars(statement))

    def get(self, session: Session, account_id: int) -> Account | None:
        return session.get(Account, account_id)

    def find_by_number(self, session: Session, account_number: str) -> Account | None:
        return session.scalar(select(Account).where(Account.account_number == account_number))

    def find_by_name(self, session: Session, name: str) -> Account | None:
        return session.scalar(select(Account).where(Account.name == name))

    def get_or_create(
        self,
        session: Session,
        *,
        name: str,
        bank_name: str | None,
        account_number: str | None,
        sort_code: str | None,
        account_type: str,
        currency: str,
        opening_balance: float = 0.0,
    ) -> Account:
        existing = None
        if account_number:
            existing = self.find_by_number(session, account_number)
        if existing is None:
            existing = self.find_by_name(session, name)
        if existing is not None:
            return existing
        account = Account(
            name=name,
            bank_name=bank_name,
            account_number=account_number,
            sort_code=sort_code,
            account_type=account_type,
            currency=currency,
            opening_balance=opening_balance,
        )
        session.add(account)
        session.flush()
        return account
