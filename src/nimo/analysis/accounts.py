from __future__ import annotations

import pandas as pd


def account_summary(frame: pd.DataFrame, account_opening: dict[int, float]) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "account_id",
                "account_name",
                "account_type",
                "balance",
                "income",
                "spend",
                "net_movement",
                "transaction_count",
            ]
        )
    rows: list[dict[str, object]] = []
    work = frame.sort_values(["booking_date", "id"], kind="stable")
    for account_id, group in work.groupby("account_id"):
        balances = pd.to_numeric(group["running_balance"], errors="coerce")
        balance = (
            float(balances.dropna().iloc[-1])
            if balances.notna().any()
            else float(account_opening.get(int(account_id), 0.0)) + float(group["amount"].sum())
        )
        external = group.loc[group["transfer_group_id"].isna()]
        rows.append(
            {
                "account_id": int(account_id),
                "account_name": str(group["account_name"].iloc[0]),
                "bank_name": group["bank_name"].iloc[0],
                "account_type": str(group["account_type"].iloc[0]),
                "balance": balance,
                "income": float(external.loc[external["amount"] > 0, "amount"].sum()),
                "spend": float(-external.loc[external["amount"] < 0, "amount"].sum()),
                "net_movement": float(group["amount"].sum()),
                "transaction_count": len(group),
            }
        )
    return pd.DataFrame(rows).sort_values("balance", ascending=False).reset_index(drop=True)


def balance_history(frame: pd.DataFrame, account_opening: dict[int, float]) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["booking_date", "account_id", "account_name", "balance"])
    parts: list[pd.DataFrame] = []
    for account_id, group in frame.sort_values(["booking_date", "id"], kind="stable").groupby("account_id"):
        group = group.copy()
        supplied = pd.to_numeric(group["running_balance"], errors="coerce")
        computed = float(account_opening.get(int(account_id), 0.0)) + group["amount"].cumsum()
        group["balance"] = supplied.where(supplied.notna(), computed)
        parts.append(group[["booking_date", "account_id", "account_name", "balance"]])
    return pd.concat(parts, ignore_index=True)
