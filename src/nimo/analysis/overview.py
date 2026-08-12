from __future__ import annotations

from calendar import monthrange
from datetime import date

import numpy as np
import pandas as pd

from nimo.domain.models import OverviewMetrics


def _external(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "transfer_group_id" not in frame:
        return frame
    return frame.loc[frame["transfer_group_id"].isna()].copy()


def _latest_balances(frame: pd.DataFrame, account_opening: dict[int, float]) -> dict[int, float]:
    balances: dict[int, float] = {}
    if frame.empty:
        return account_opening.copy()
    for account_id, group in frame.sort_values(["booking_date", "id"]).groupby("account_id"):
        running = pd.to_numeric(group["running_balance"], errors="coerce")
        if running.notna().any():
            balances[int(account_id)] = float(running.dropna().iloc[-1])
        else:
            balances[int(account_id)] = float(account_opening.get(int(account_id), 0.0)) + float(
                group["amount"].sum()
            )
    for account_id, opening in account_opening.items():
        balances.setdefault(account_id, float(opening))
    return balances


def _weighted_average(values: pd.Series, decay: float) -> float | None:
    if values.empty:
        return None
    ordered = values.sort_index()
    weights = np.array([decay ** index for index in reversed(range(len(ordered)))], dtype=float)
    weights /= weights.sum()
    return float(np.average(ordered.to_numpy(dtype=float), weights=weights))


def _project_month_end(external: pd.DataFrame, as_of: pd.Timestamp, decay: float) -> float | None:
    debits = external.loc[external["amount"] < 0].copy()
    if debits.empty:
        return 0.0
    debits["spend"] = -debits["amount"]
    current_period = as_of.to_period("M")
    current = debits.loc[debits["booking_date"].dt.to_period("M") == current_period]
    current_spend = float(current["spend"].sum())

    previous = debits.loc[debits["booking_date"].dt.to_period("M") < current_period].copy()
    if previous.empty:
        days = monthrange(as_of.year, as_of.month)[1]
        return current_spend / max(1, as_of.day) * days

    previous["period"] = previous["booking_date"].dt.to_period("M")
    previous["day"] = previous["booking_date"].dt.day
    full = previous.groupby("period")["spend"].sum()
    through_day = previous.loc[previous["day"] <= as_of.day].groupby("period")["spend"].sum()
    remaining = (full - through_day.reindex(full.index, fill_value=0.0)).clip(lower=0.0)
    expected_remaining = _weighted_average(remaining, decay) or 0.0
    return current_spend + expected_remaining


def compute_overview_metrics(
    frame: pd.DataFrame,
    *,
    account_opening: dict[int, float] | None = None,
    recent_weight_decay: float = 0.85,
) -> OverviewMetrics:
    account_opening = account_opening or {}
    if frame.empty:
        return OverviewMetrics(
            total_balance=sum(account_opening.values()),
            total_income=0.0,
            total_spend=0.0,
            net_cash_flow=0.0,
            savings_rate=None,
            current_month_spend=0.0,
            projected_month_end_spend=None,
            weighted_monthly_spend=None,
            yearly_spend=0.0,
            active_accounts=len(account_opening),
            transaction_count=0,
            uncategorised_count=0,
            largest_debit=None,
            largest_credit=None,
            date_start=None,
            date_end=None,
        )

    work = frame.copy()
    work["booking_date"] = pd.to_datetime(work["booking_date"])
    external = _external(work)
    income = external.loc[external["amount"] > 0, "amount"]
    spend = -external.loc[external["amount"] < 0, "amount"]
    total_income = float(income.sum())
    total_spend = float(spend.sum())
    net = total_income - total_spend
    savings_rate = None if total_income <= 0 else net / total_income
    as_of = work["booking_date"].max()
    current_period = as_of.to_period("M")
    current_spend = float(
        -external.loc[
            (external["booking_date"].dt.to_period("M") == current_period)
            & (external["amount"] < 0),
            "amount",
        ].sum()
    )

    debit_frame = external.loc[external["amount"] < 0].copy()
    debit_frame["period"] = debit_frame["booking_date"].dt.to_period("M")
    monthly_spend = -debit_frame.groupby("period")["amount"].sum()
    weighted_monthly = _weighted_average(monthly_spend, recent_weight_decay)
    projected = _project_month_end(external, as_of, recent_weight_decay)
    yearly_spend = float(
        -external.loc[
            (external["booking_date"].dt.year == as_of.year) & (external["amount"] < 0),
            "amount",
        ].sum()
    )
    balances = _latest_balances(work, account_opening)

    return OverviewMetrics(
        total_balance=float(sum(balances.values())),
        total_income=total_income,
        total_spend=total_spend,
        net_cash_flow=net,
        savings_rate=savings_rate,
        current_month_spend=current_spend,
        projected_month_end_spend=projected,
        weighted_monthly_spend=weighted_monthly,
        yearly_spend=yearly_spend,
        active_accounts=int(work["account_id"].nunique()),
        transaction_count=len(work),
        uncategorised_count=int(work["category_id"].isna().sum()),
        largest_debit=(float(spend.max()) if not spend.empty else None),
        largest_credit=(float(income.max()) if not income.empty else None),
        date_start=work["booking_date"].min().date(),
        date_end=as_of.date(),
    )


def monthly_spending(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["month", "spend", "income", "net"])
    work = _external(frame.copy())
    work["booking_date"] = pd.to_datetime(work["booking_date"])
    work["month"] = work["booking_date"].dt.to_period("M").dt.to_timestamp()
    grouped = work.groupby("month")["amount"]
    result = pd.DataFrame(
        {
            "income": grouped.apply(lambda values: values[values > 0].sum()),
            "spend": grouped.apply(lambda values: -values[values < 0].sum()),
            "net": grouped.sum(),
        }
    ).reset_index()
    return result
