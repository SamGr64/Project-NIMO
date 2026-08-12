from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    user_name: str
    seed: int
    start_date: date
    end_date: date
    archetype: str | None = None
    questionnaire: dict[str, str] | None = None
    statement_format: str = "seeded_random"


@dataclass(slots=True)
class GenerationResult:
    user_name: str
    seed: int
    archetype: str
    statement_paths: list[Path]
    imported_rows: int
    account_count: int
    manifest_path: Path
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ImportResult:
    source_file_id: int | None
    account_id: int | None
    imported_rows: int
    superseded_rows: int
    coverage_start: date | None
    coverage_end: date | None
    duplicate_file: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class OverviewMetrics:
    total_balance: float
    total_income: float
    total_spend: float
    net_cash_flow: float
    savings_rate: float | None
    current_month_spend: float
    projected_month_end_spend: float | None
    weighted_monthly_spend: float | None
    yearly_spend: float
    active_accounts: int
    transaction_count: int
    uncategorised_count: int
    largest_debit: float | None
    largest_credit: float | None
    date_start: date | None
    date_end: date | None

    def as_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


@dataclass(frozen=True, slots=True)
class CashFlowLink:
    source: str
    target: str
    value: float
    flow_type: str
    confidence: float | None = None
