from __future__ import annotations

from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Modes = Literal["merge", "split"]


class StatementLengthConfig(BaseModel):
    mean: float = Field(default=40, gt=0)
    std: float = Field(default=10, gt=0)
    minimum: int = Field(default=1, ge=1)


class DateGenerationConfig(BaseModel):
    year_range: tuple[int, int] = (2000, 2025)

    @field_validator("year_range")
    @classmethod
    def validate_year_range(cls, value: tuple[int, int]) -> tuple[int, int]:
        lower, upper = value
        if lower > upper:
            raise ValueError("date_generation.year_range lower bound exceeds upper bound")
        if lower < 1 or upper > 9999:
            raise ValueError("date_generation.year_range must contain valid calendar years")
        return value


class AmountGenerationConfig(BaseModel):
    positive_centre: float = Field(default=20, gt=0)
    negative_centre: float = Field(default=-20, le=0)
    positive_std: float = Field(default=5, gt=0)
    negative_std: float = Field(default=5, gt=0)
    deposit_probability: float = Field(default=0.5, ge=0, le=1)
    decimal_places: int = 2
    forbid_zero: bool = True


class ModesConfig(BaseModel):
    merge: float = Field(default=1, ge=0)
    split: float = Field(default=0, ge=0)
    append_format: str = "{amount:.2f} {currency}"
    description_format: str = "{transaction_type} {description}"
    currency: str = "GBP"

    @model_validator(mode="after")
    def weights(self) -> "ModesConfig":
        if self.merge + self.split <= 0:
            raise ValueError("At least one amount mode weight must be positive")
        return self


class FieldInclusionConfig(BaseModel):
    required: list[str] = ["date", "bank_name", "account_number", "sort_code", "amount"]
    optional_probabilities: dict[str, float] = {}

    @field_validator("optional_probabilities")
    @classmethod
    def validate_probabilities(cls, value: dict[str, float]) -> dict[str, float]:
        invalid = {key: probability for key, probability in value.items() if not 0 <= probability <= 1}
        if invalid:
            raise ValueError(f"Optional field probabilities must be between 0 and 1: {invalid}")
        return value


class AccountNumberConfig(BaseModel):
    digits: int = Field(default=8, ge=1, le=32)


class SortCodeConfig(BaseModel):
    digits: int = Field(default=6, ge=2, le=32)
    hyphen_probability: float = Field(default=1, ge=0, le=1)

    @field_validator("digits")
    @classmethod
    def validate_even_digits(cls, value: int) -> int:
        if value % 2:
            raise ValueError("sort_code.digits must be even so it can be grouped in pairs")
        return value


class IdentifierConfig(BaseModel):
    bank_id_length: int = Field(default=8, ge=1, le=64)


class OutputConfig(BaseModel):
    filename_template: str = "sample_{bank_id}_{seed}.csv"
    column_order: list[str] = [
                "date", "bank_name", "account_number",
                "sort_code", "account_type", "transaction_type", "description",
                "amount", "deposits", "withdrawals", "currency", "running_balance",
            ]
    prevent_overwrite: bool = True


class AnalysisConfig(BaseModel):
    constant_fields: list[str] = ["bank_name", "account_number", "sort_code", "account_type", "currency"]
    amount_histogram_bins: int = Field(default=12, ge=1)
    date_frequency: str = "D"
    show_plots: bool = True
    save_plots: bool = False
    plot_directory: Path = Path("data/statements")
    plot_format: str = "png"


class GeneratorPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    default_seed: int = 42
    default_path: Path = Path("data/sample_statements")
    default_banks: list[str] = ["Placeholder Bank"]
    statement_length: StatementLengthConfig
    date_generation: DateGenerationConfig
    amount_generation: AmountGenerationConfig
    amount_modes: ModesConfig
    currency_modes: ModesConfig
    descript_modes: ModesConfig
    field_inclusion: FieldInclusionConfig
    account_number: AccountNumberConfig
    sort_code: SortCodeConfig
    identifiers: IdentifierConfig
    account_types: list[str | list[str]] = ["Basic Account"]
    transaction_types: dict[str, list[Any]] = {"deposit_type": ["CR"],
                                               "withdrawal_types": ["DR"],
                                               "either": []}
    descriptions: dict[str, list[str]] = {"deposit": ["Credit transaction"], 
                                          "withdrawal": ["Debit transaction"],
                                          "either": ["Account transaction"]}
    aliases: dict[str, list[str]] = {
        "date": ["date"],
        "bank_name": ["bank_name"],
        "account_number": ["account_number"],
        "sort_code": ["sort_code"],
        "amount": ["amount"],
        "deposits": ["deposits"],
        "withdrawals": ["withdrawals"],
        "currency": ["currency"],
        "description": ["description"],
        "account_type": ["account_type"],
        "transaction_type": ["transaction_type"],
        "running_balance": ["running_balance"],
    }
    output: OutputConfig
    analysis: AnalysisConfig

    @field_validator("default_banks")
    @classmethod
    def validate_banks(cls, value: str | list[str]) -> str | list[str]:
        banks = [value] if isinstance(value, str) else value
        cleaned = [bank.strip() for bank in banks if isinstance(bank, str) and bank.strip()]
        if not cleaned:
            raise ValueError("default_banks must contain at least one bank")
        return cleaned[0] if isinstance(value, str) else cleaned

    @field_validator("aliases")
    @classmethod
    def validate_aliases(cls, value: dict[str, list[str]]) -> dict[str, list[str]]:
        invalid = [field for field, aliases in value.items() if not aliases]
        if invalid:
            raise ValueError(f"Alias groups may not be empty: {invalid}")
        return value
