from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def score_outliers(
    frame: pd.DataFrame,
    *,
    group_column: str = "category_slug",
    iqr_multiplier: float = 1.5,
    robust_z_threshold: float = 3.5,
) -> pd.DataFrame:
    columns = ["transaction_id", "scope_key", "amount_magnitude", "robust_z", "surprise_score", "is_outlier", "evidence"]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    working = frame.loc[frame["amount"] < 0].copy()
    if working.empty:
        return pd.DataFrame(columns=columns)
    working["scope_key"] = working.get(group_column, pd.Series(index=working.index, dtype=object)).fillna("uncategorised").astype(str)
    working["amount_magnitude"] = -pd.to_numeric(working["amount"], errors="coerce")
    rows: list[dict[str, Any]] = []
    for scope_key, group in working.groupby("scope_key", dropna=False):
        values = group["amount_magnitude"].to_numpy(dtype=float)
        median = float(np.median(values))
        mad = float(np.median(np.abs(values - median)))
        q1, q3 = [float(value) for value in np.quantile(values, [0.25, 0.75])]
        iqr = q3 - q1
        upper = q3 + iqr_multiplier * iqr
        sorted_values = np.sort(values)
        for record, value in zip(group.to_dict(orient="records"), values, strict=False):
            robust_z = 0.0 if mad <= 1e-12 else 0.67448975 * (value - median) / mad
            empirical_tail = max(1.0 / (len(values) + 1.0), float(np.count_nonzero(sorted_values >= value)) / len(values))
            surprise = -math.log10(empirical_tail)
            is_outlier = bool(value > upper or robust_z > robust_z_threshold)
            rows.append(
                {
                    "transaction_id": int(record["id"]),
                    "scope_key": str(scope_key),
                    "amount_magnitude": round(float(value), 6),
                    "robust_z": round(float(robust_z), 6),
                    "surprise_score": round(float(surprise), 6),
                    "is_outlier": is_outlier,
                    "evidence": {
                        "median": round(median, 6),
                        "mad": round(mad, 6),
                        "q1": round(q1, 6),
                        "q3": round(q3, 6),
                        "upper_fence": round(upper, 6),
                    },
                }
            )
    return pd.DataFrame(rows, columns=columns)
