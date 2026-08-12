from __future__ import annotations

import pandas as pd


def category_summary(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["category", "spend", "income", "net", "transactions"])
    work = frame.loc[frame["transfer_group_id"].isna()].copy()
    work["category"] = work["category_label"].fillna("Uncategorised")
    rows: list[dict[str, object]] = []
    for category, group in work.groupby("category"):
        rows.append(
            {
                "category": category,
                "spend": float(-group.loc[group["amount"] < 0, "amount"].sum()),
                "income": float(group.loc[group["amount"] > 0, "amount"].sum()),
                "net": float(group["amount"].sum()),
                "transactions": len(group),
                "average_amount": float(group["amount"].abs().mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("spend", ascending=False).reset_index(drop=True)


def category_timeline(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["month", "category", "spend"])
    work = frame.loc[(frame["amount"] < 0) & frame["transfer_group_id"].isna()].copy()
    work["booking_date"] = pd.to_datetime(work["booking_date"])
    work["month"] = work["booking_date"].dt.to_period("M").dt.to_timestamp()
    work["category"] = work["category_label"].fillna("Uncategorised")
    return (
        work.assign(spend=-work["amount"])
        .groupby(["month", "category"], as_index=False)["spend"]
        .sum()
    )
