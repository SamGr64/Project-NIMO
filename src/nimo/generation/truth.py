from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from nimo.generation.accounts import SyntheticAccount
from nimo.generation.latent_profile import LatentProfile


def write_ground_truth(
    *,
    output_dir: Path,
    profile: LatentProfile,
    accounts: list[SyntheticAccount],
    process_truth: dict[str, Any],
    transactions: pd.DataFrame,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "warning": "Private synthetic ground truth. Core analysis must never read this file.",
        "profile": profile.as_dict(),
        "accounts": [account.as_dict() for account in accounts],
        "processes": process_truth,
        "transaction_truth": transactions[
            [
                "account_key",
                "booking_date",
                "amount",
                "category_truth",
                "process_truth",
                "behaviours_truth",
                "event_id",
            ]
        ].assign(booking_date=lambda frame: frame["booking_date"].astype(str)).to_dict(orient="records"),
    }
    path = output_dir / "ground_truth.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path
