"""Shared utilities for statement generation and analysis."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Iterable, Mapping
import pandas as pd
import yaml


def normalise_text_aggressive(value: Any) -> str:
    """Convert labels to a stable snake-case representation."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip().casefold().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def cryptic_id(value: str, length: int) -> str:
    """Return a deterministic uppercase SHA-256 prefix."""
    digest = hashlib.sha256(normalise_text_aggressive(value).encode("utf-8")).hexdigest()
    return digest[:length].upper()


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Load YAML and require a mapping at the document root."""
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise TypeError("Top-level YAML value must be a mapping")
    return payload


def load_csv(path: Path) -> pd.DataFrame:
    """Load a CSV statement."""
    return pd.read_csv(path)


def dump_csv(path: Path, frame: pd.DataFrame, *, overwrite: bool) -> None:
    """Write a CSV, creating parents and optionally preventing overwrite."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    frame.to_csv(path, index=False)


def alias_candidates(policy: Mapping[str, Any], canonical_field: str) -> list[str]:
    """Return aliases from either canonical or legacy *_aliases YAML keys."""
    aliases = policy.get("aliases", {})
    if not isinstance(aliases, Mapping):
        return [canonical_field]

    candidates = aliases.get(canonical_field)
    if candidates is None:
        candidates = aliases.get(f"{canonical_field}_aliases")

    if isinstance(candidates, str):
        return [candidates]
    if isinstance(candidates, Iterable):
        return [str(value) for value in candidates]
    return [canonical_field]


def find_field_name(
    policy: Mapping[str, Any],
    canonical_field: str,
    columns: Iterable[str],
) -> str | None:
    """Find the actual CSV column corresponding to a canonical field."""
    actual_by_normalised = {
        normalise_text_aggressive(column): str(column)
        for column in columns
    }
    candidates = [canonical_field, *alias_candidates(policy, canonical_field)]
    for candidate in candidates:
        found = actual_by_normalised.get(normalise_text_aggressive(candidate))
        if found is not None:
            return found
    return None


def flatten_nested_strings(values: Iterable[Any]) -> list[str]:
    """Flatten one or more levels of nested string aliases, preserving order."""
    flattened: list[str] = []

    def visit(value: Any) -> None:
        if isinstance(value, (list, tuple, set)):
            for item in value:
                visit(item)
        elif value is not None:
            text = str(value)
            if text not in flattened:
                flattened.append(text)

    visit(list(values))
    return flattened


def numeric_series(series: pd.Series) -> pd.Series:
    """Parse numbers from numeric or currency-formatted values."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    extracted = (
        series.astype("string")
        .str.replace(",", "", regex=False)
        .str.extract(r"([-+]?\d+(?:\.\d+)?)", expand=False)
    )
    return pd.to_numeric(extracted, errors="coerce")


def canonical_amount_series(frame: pd.DataFrame, policy: Mapping[str, Any]) -> pd.Series:
    """Resolve a signed amount series from amount or split credit/debit fields."""
    amount_col = find_field_name(policy, "amount", frame.columns)
    if amount_col:
        return numeric_series(frame[amount_col])

    deposits_col = find_field_name(policy, "deposits", frame.columns)
    withdrawals_col = find_field_name(policy, "withdrawals", frame.columns)
    if deposits_col and withdrawals_col:
        deposits = numeric_series(frame[deposits_col]).fillna(0)
        withdrawals = numeric_series(frame[withdrawals_col]).fillna(0)
        return deposits - withdrawals

    raise KeyError("No amount column or deposits/withdrawals pair could be resolved")