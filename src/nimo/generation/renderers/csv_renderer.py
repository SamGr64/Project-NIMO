from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from nimo.generation.accounts import SyntheticAccount
from nimo.generation.seeds import child_seed


class SeededCsvStatementRenderer:
    def __init__(self, *, seed: int, statement_config: dict[str, Any]) -> None:
        self.seed = seed
        self.statement_config = statement_config

    def render(
        self,
        transactions: pd.DataFrame,
        account: SyntheticAccount,
        output_dir: Path,
        *,
        format_name: str = "seeded_random",
    ) -> Path:
        formats = self.statement_config.get("formats", {})
        if not formats:
            raise ValueError("No statement formats are configured")
        rng = np.random.default_rng(child_seed(self.seed, f"renderer:{account.key}"))
        chosen = format_name
        if chosen == "seeded_random":
            chosen = str(rng.choice(sorted(formats)))
        if chosen not in formats:
            raise ValueError(f"Unknown statement format: {chosen}")
        config = formats[chosen]

        account_rows = transactions.loc[transactions["account_key"] == account.key].copy()
        account_rows = account_rows.sort_values("booking_date", kind="stable").reset_index(drop=True)
        columns = config.get("columns", {})
        output = pd.DataFrame()
        output[columns.get("date", "date")] = pd.to_datetime(account_rows["booking_date"]).dt.strftime(
            config.get("date_format", "%Y-%m-%d")
        )
        output[columns.get("description", "description")] = account_rows["description"]

        amount_mode = config.get("amount_mode", "signed")
        if amount_mode == "split":
            credits_name = columns.get("credits", "credits")
            debits_name = columns.get("debits", "debits")
            output[credits_name] = account_rows["amount"].where(account_rows["amount"] > 0).round(2)
            output[debits_name] = (-account_rows["amount"]).where(account_rows["amount"] < 0).round(2)
        else:
            output[columns.get("amount", "amount")] = account_rows["amount"].round(2)

        if config.get("include_balance", False):
            output[columns.get("balance", "balance")] = account_rows["running_balance"].round(2)

        metadata = {
            "currency": account.currency,
            "bank_name": account.bank_name,
            "account_number": account.account_number,
            "sort_code": account.sort_code,
            "account_name": account.name,
        }
        for canonical, value in metadata.items():
            if canonical in columns:
                output[columns[canonical]] = value

        output_dir.mkdir(parents=True, exist_ok=True)
        safe_account = re.sub(r"[^a-z0-9]+", "_", account.name.lower()).strip("_")
        start = min(account_rows["booking_date"]).isoformat()
        end = max(account_rows["booking_date"]).isoformat()
        path = output_dir / f"{safe_account}_{start}_{end}_{chosen}.csv"
        output.to_csv(path, index=False)
        return path
