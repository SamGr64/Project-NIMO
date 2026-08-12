from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

from nimo.ingestion.mappings import ColumnMapping


@dataclass(frozen=True, slots=True)
class StatementMetadata:
    account_name: str
    bank_name: str | None
    account_number: str | None
    sort_code: str | None
    currency: str
    account_type: str
    opening_balance: float


def _first_text(series: pd.Series | None) -> str | None:
    if series is None:
        return None
    values = series.dropna().astype(str).map(str.strip)
    values = values[values != ""]
    return None if values.empty else str(values.iloc[0])


def parse_money(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    text = series.astype("string").fillna("").str.strip()
    negative_parentheses = text.str.match(r"^\(.*\)$")
    cleaned = (
        text.str.replace(",", "", regex=False)
        .str.replace("(", "", regex=False)
        .str.replace(")", "", regex=False)
        .str.extract(r"([-+]?\d+(?:\.\d+)?)", expand=False)
    )
    values = pd.to_numeric(cleaned, errors="coerce")
    values.loc[negative_parentheses & values.notna()] *= -1
    return values


def normalise_merchant(description: str) -> str:
    text = str(description).upper().strip()
    text = re.sub(r"\b\d{4,}\b", "", text)
    text = re.sub(r"[^A-Z0-9& ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()[:260]


def normalise_statement(
    frame: pd.DataFrame,
    mapping: ColumnMapping,
    *,
    account_name_override: str | None = None,
    account_type_override: str | None = None,
    currency_default: str = "GBP",
) -> tuple[pd.DataFrame, StatementMetadata, list[str]]:
    warnings: list[str] = []
    raw_dates = frame[mapping.date].astype("string").str.strip()
    iso_share = float(raw_dates.str.match(r"^\d{4}-\d{2}-\d{2}").fillna(False).mean())
    dates = pd.to_datetime(
        raw_dates,
        errors="coerce",
        format="mixed",
        dayfirst=iso_share < 0.80,
    )
    invalid_dates = int(dates.isna().sum())
    if invalid_dates:
        warnings.append(f"Ignored {invalid_dates} rows with invalid dates")

    if mapping.amount:
        amounts = parse_money(frame[mapping.amount])
    else:
        credits = parse_money(frame[str(mapping.credits)]).fillna(0.0)
        debits = parse_money(frame[str(mapping.debits)]).fillna(0.0).abs()
        amounts = credits - debits

    invalid_amounts = int(amounts.isna().sum())
    if invalid_amounts:
        warnings.append(f"Ignored {invalid_amounts} rows with invalid amounts")

    descriptions = frame[mapping.description].astype("string").fillna("").str.strip()
    valid = dates.notna() & amounts.notna() & descriptions.ne("")
    normalised = pd.DataFrame(
        {
            "source_row": frame.index.astype(int) + 2,
            "booking_date": dates.dt.date,
            "value_date": dates.dt.date,
            "description_raw": descriptions,
            "merchant_normalised": descriptions.map(normalise_merchant),
            "amount": amounts.astype(float),
        }
    ).loc[valid]

    currency = currency_default
    if mapping.currency:
        currency = _first_text(frame[mapping.currency]) or currency_default
    normalised["currency"] = currency

    if mapping.balance:
        normalised["running_balance"] = parse_money(frame[mapping.balance]).loc[valid].astype(float)
    else:
        normalised["running_balance"] = pd.NA

    bank_name = _first_text(frame[mapping.bank_name]) if mapping.bank_name else None
    account_number = _first_text(frame[mapping.account_number]) if mapping.account_number else None
    sort_code = _first_text(frame[mapping.sort_code]) if mapping.sort_code else None
    inferred_name = _first_text(frame[mapping.account_name]) if mapping.account_name else None
    account_name = account_name_override or inferred_name
    if account_name is None:
        suffix = account_number[-4:] if account_number and len(account_number) >= 4 else "Imported"
        account_name = f"{bank_name or 'Bank'} {suffix}"

    lowered = account_name.lower()
    account_type = account_type_override or (
        "savings" if any(token in lowered for token in ("saving", "isa")) else "current"
    )

    opening_balance = 0.0
    balance_values = pd.to_numeric(normalised["running_balance"], errors="coerce")
    if balance_values.notna().any():
        first_position = balance_values.first_valid_index()
        if first_position is not None:
            first_balance = float(balance_values.loc[first_position])
            first_amount = float(normalised.loc[first_position, "amount"])
            opening_balance = first_balance - first_amount

    normalised = normalised.reset_index(drop=True)
    if normalised.empty:
        raise ValueError("No valid transaction rows remained after normalisation")

    return (
        normalised,
        StatementMetadata(
            account_name=account_name,
            bank_name=bank_name,
            account_number=account_number,
            sort_code=sort_code,
            currency=currency,
            account_type=account_type,
            opening_balance=opening_balance,
        ),
        warnings,
    )
