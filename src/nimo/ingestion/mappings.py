from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable


def normalise_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


@dataclass(frozen=True, slots=True)
class ColumnMapping:
    date: str
    description: str
    amount: str | None = None
    credits: str | None = None
    debits: str | None = None
    balance: str | None = None
    currency: str | None = None
    bank_name: str | None = None
    account_number: str | None = None
    sort_code: str | None = None
    account_name: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


def detect_mapping(
    columns: Iterable[str],
    statement_config: dict[str, Any],
    overrides: dict[str, str] | None = None,
) -> ColumnMapping:
    aliases = statement_config.get("aliases", {})
    by_normalised = {normalise_header(column): str(column) for column in columns}
    resolved: dict[str, str | None] = {}

    for canonical, candidates in aliases.items():
        found = None
        for candidate in (canonical, *(candidates or [])):
            found = by_normalised.get(normalise_header(candidate))
            if found is not None:
                break
        resolved[canonical] = found

    for canonical, column in (overrides or {}).items():
        if column not in by_normalised.values():
            raise KeyError(f"Column override {column!r} for {canonical!r} is not in the statement")
        resolved[canonical] = column

    missing = [key for key in ("date", "description") if not resolved.get(key)]
    if missing:
        raise KeyError(f"Could not resolve required statement columns: {', '.join(missing)}")

    if not resolved.get("amount") and not (
        resolved.get("credits") and resolved.get("debits")
    ):
        raise KeyError("Could not resolve a signed amount column or a credits/debits pair")

    return ColumnMapping(
        date=str(resolved["date"]),
        description=str(resolved["description"]),
        amount=resolved.get("amount"),
        credits=resolved.get("credits"),
        debits=resolved.get("debits"),
        balance=resolved.get("balance"),
        currency=resolved.get("currency"),
        bank_name=resolved.get("bank_name"),
        account_number=resolved.get("account_number"),
        sort_code=resolved.get("sort_code"),
        account_name=resolved.get("account_name"),
    )
