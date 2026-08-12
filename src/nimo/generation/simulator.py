from __future__ import annotations

import json
import math
import uuid
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd

from nimo.generation.accounts import SyntheticAccount
from nimo.generation.latent_profile import LatentProfile
from nimo.generation.processes import inflation_factor
from nimo.generation.seeds import child_seed


@dataclass(slots=True)
class SimulationResult:
    transactions: pd.DataFrame
    process_truth: dict[str, Any]


def _clamped_date(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, monthrange(year, month)[1]))


def _weighted_weekday(
    rng: np.random.Generator,
    week_start: date,
    weights: np.ndarray,
    start_date: date,
    end_date: date,
) -> date:
    weights = weights / weights.sum()
    for _ in range(20):
        offset = int(rng.choice(np.arange(7), p=weights))
        candidate = week_start + timedelta(days=offset)
        if start_date <= candidate <= end_date:
            return candidate
    return min(max(week_start, start_date), end_date)


def simulate_financial_life(
    *,
    profile: LatentProfile,
    accounts: list[SyntheticAccount],
    start_date: date,
    end_date: date,
) -> SimulationResult:
    if end_date < start_date:
        raise ValueError("Generation end date must be on or after the start date")
    account_by_key = {account.key: account for account in accounts}
    current = account_by_key["current"]
    savings = account_by_key.get("savings")
    rows: list[dict[str, Any]] = []
    event_counter = 0

    def add(
        account_key: str,
        event_date: date,
        description: str,
        amount: float,
        category: str,
        process: str,
        behaviours: list[str],
        *,
        event_id: str | None = None,
    ) -> None:
        nonlocal event_counter
        if not (start_date <= event_date <= end_date):
            return
        event_counter += 1
        deterministic_event_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"nimo:{profile.seed}:{account_key}:{process}:{event_date.isoformat()}:{event_counter}",
            )
        )
        rows.append(
            {
                "account_key": account_key,
                "booking_date": event_date,
                "description": description,
                "amount": round(float(amount), 2),
                "currency": account_by_key[account_key].currency,
                "category_truth": category,
                "process_truth": process,
                "behaviours_truth": json.dumps(behaviours),
                "event_id": event_id or deterministic_event_id,
            }
        )

    process_truth: dict[str, Any] = {}

    income_rng = np.random.default_rng(child_seed(profile.seed, "income"))
    if profile.income_stability >= 0.48:
        process_truth["income"] = {
            "occurrence": "monthly_periodic",
            "day": profile.payday,
            "amount_mean": profile.monthly_income,
            "amount_variability": 1.0 - profile.income_stability,
        }
        for month in pd.period_range(start=start_date, end=end_date, freq="M"):
            event_date = _clamped_date(month.year, month.month, profile.payday)
            variability = max(0.006, (1.0 - profile.income_stability) * 0.11)
            amount = profile.monthly_income * float(income_rng.normal(1.0, variability))
            add(
                "current",
                event_date,
                "ACME PAYROLL SALARY",
                max(300.0, amount),
                "salary",
                "income",
                ["periodic", "distributional"],
            )
    else:
        process_truth["income"] = {
            "occurrence": "weekly_distributional",
            "monthly_mean": profile.monthly_income,
            "volatility": 1.0 - profile.income_stability,
        }
        week_starts = pd.date_range(start_date, end_date, freq="W-MON")
        weekly_mean = profile.monthly_income / 4.345
        for week in week_starts:
            count = max(0, int(income_rng.poisson(1.35)))
            for _ in range(count):
                event_date = (week + pd.Timedelta(days=int(income_rng.integers(0, 5)))).date()
                amount = float(
                    income_rng.lognormal(
                        mean=math.log(max(90.0, weekly_mean / 1.35)),
                        sigma=0.25 + 0.55 * (1.0 - profile.income_stability),
                    )
                )
                add(
                    "current",
                    event_date,
                    str(income_rng.choice(["CLIENT INVOICE PAYMENT", "FREELANCE CREDIT", "CONTRACT PAY"])),
                    amount,
                    "other_income",
                    "income",
                    ["distributional", "spontaneous"],
                )

    housing_rng = np.random.default_rng(child_seed(profile.seed, "housing"))
    rent_day = int(housing_rng.choice([1, 2, 3, 5]))
    rent_base = profile.monthly_income * profile.housing_ratio
    process_truth["housing"] = {
        "occurrence": "monthly_periodic",
        "day": rent_day,
        "amount_base": round(rent_base, 2),
        "inflation": profile.annual_inflation,
    }
    for month in pd.period_range(start=start_date, end=end_date, freq="M"):
        event_date = _clamped_date(month.year, month.month, rent_day)
        amount = rent_base * inflation_factor(event_date, start_date, profile.annual_inflation * 0.85)
        add("current", event_date, "HOME RENT PAYMENT", -amount, "housing", "housing", ["periodic"])

    bills_rng = np.random.default_rng(child_seed(profile.seed, "bills"))
    bill_specs = [
        ("NIMO ENERGY", 0.034, 7),
        ("CITY WATER", 0.014, 15),
        ("BROADBAND SERVICE", 0.011, 20),
        ("MOBILE NETWORK", 0.009, 22),
    ]
    process_truth["bills"] = {"occurrence": "monthly_periodic", "count": len(bill_specs)}
    for month in pd.period_range(start=start_date, end=end_date, freq="M"):
        for description, income_fraction, day in bill_specs:
            event_date = _clamped_date(month.year, month.month, day)
            noise = float(bills_rng.normal(1.0, 0.025 + 0.05 * profile.spending_volatility))
            amount = (
                profile.monthly_income
                * income_fraction
                * noise
                * inflation_factor(event_date, start_date, profile.annual_inflation)
            )
            add("current", event_date, description, -amount, "bills", "bills", ["periodic", "distributional"])

    subscription_rng = np.random.default_rng(child_seed(profile.seed, "subscriptions"))
    subscription_catalogue = [
        ("NETFLIX SUBSCRIPTION", 10.99),
        ("SPOTIFY MEMBERSHIP", 11.99),
        ("GYM MEMBERSHIP", 29.99),
        ("CLOUD STORAGE", 2.99),
        ("NEWS MEMBERSHIP", 8.50),
        ("VIDEO STREAMING", 7.99),
    ]
    subscription_count = min(
        len(subscription_catalogue),
        max(1, 1 + int(round(profile.subscription_tendency * 5))),
    )
    selected_subscriptions = subscription_rng.choice(
        len(subscription_catalogue), size=subscription_count, replace=False
    )
    process_truth["subscriptions"] = {
        "occurrence": "monthly_periodic",
        "count": subscription_count,
    }
    for index in selected_subscriptions:
        description, base_amount = subscription_catalogue[int(index)]
        billing_day = int(subscription_rng.integers(2, 26))
        for month in pd.period_range(start=start_date, end=end_date, freq="M"):
            event_date = _clamped_date(month.year, month.month, billing_day)
            add(
                "current",
                event_date,
                description,
                -base_amount * inflation_factor(event_date, start_date, profile.annual_inflation * 0.45),
                "subscriptions",
                "subscriptions",
                ["periodic"],
            )

    groceries_rng = np.random.default_rng(child_seed(profile.seed, "groceries"))
    grocery_weekday_weights = np.array([0.09, 0.08, 0.10, 0.11, 0.14, 0.30, 0.18])
    grocery_weekday_weights[5:] *= 1.0 + 0.8 * profile.weekend_bias
    grocery_merchants = ["TESCO SUPERMARKET", "SAINSBURY STORE", "ALDI GROCERIES", "LIDL MARKET"]
    process_truth["groceries"] = {
        "occurrence": "weekly_distributional",
        "weekly_lambda": round(1.05 + 0.85 * (1.0 - profile.price_sensitivity), 3),
        "weekday_weights": grocery_weekday_weights.tolist(),
        "amount_family": "lognormal",
        "spontaneous_large_shop_probability": 0.04 + 0.08 * profile.spending_volatility,
    }
    week_starts = pd.date_range(start_date - timedelta(days=start_date.weekday()), end_date, freq="W-MON")
    for week in week_starts:
        count = max(1, int(groceries_rng.poisson(1.05 + 0.85 * (1.0 - profile.price_sensitivity))))
        for _ in range(count):
            event_date = _weighted_weekday(
                groceries_rng,
                week.date(),
                grocery_weekday_weights,
                start_date,
                end_date,
            )
            median = profile.monthly_income * 0.0125
            amount = float(
                groceries_rng.lognormal(
                    mean=math.log(max(12.0, median)),
                    sigma=0.32 + 0.35 * profile.spending_volatility,
                )
            )
            behaviours = ["distributional", "periodic"]
            if groceries_rng.random() < 0.04 + 0.08 * profile.spending_volatility:
                amount *= float(groceries_rng.uniform(2.0, 4.1))
                behaviours.append("spontaneous")
            amount *= inflation_factor(event_date, start_date, profile.annual_inflation)
            add(
                "current",
                event_date,
                str(groceries_rng.choice(grocery_merchants)),
                -amount,
                "groceries",
                "groceries",
                behaviours,
            )

    dining_rng = np.random.default_rng(child_seed(profile.seed, "dining"))
    dining_weights = np.array([0.04, 0.05, 0.07, 0.10, 0.22, 0.36, 0.16])
    dining_weights[4:] *= 1.0 + 1.5 * profile.weekend_bias
    dining_merchants = ["LOCAL CAFE", "CITY RESTAURANT", "NEIGHBOURHOOD PUB", "DELIVEROO TAKEAWAY"]
    dining_lambda = 0.12 + 1.55 * profile.discretionary_intensity
    process_truth["dining"] = {
        "occurrence": "weekly_distributional",
        "weekly_lambda": round(dining_lambda, 3),
        "weekday_weights": dining_weights.tolist(),
        "amount_family": "bimodal_lognormal",
    }
    for week in week_starts:
        count = int(dining_rng.poisson(dining_lambda))
        for _ in range(count):
            event_date = _weighted_weekday(
                dining_rng, week.date(), dining_weights, start_date, end_date
            )
            expensive = dining_rng.random() < 0.28 + 0.22 * profile.discretionary_intensity
            median = 42.0 if expensive else 13.5
            amount = float(
                dining_rng.lognormal(
                    mean=math.log(median),
                    sigma=0.22 + 0.35 * profile.spending_volatility,
                )
            )
            add(
                "current",
                event_date,
                str(dining_rng.choice(dining_merchants)),
                -amount * inflation_factor(event_date, start_date, profile.annual_inflation),
                "dining",
                "dining",
                ["distributional", "periodic" if event_date.weekday() >= 4 else "distributional"],
            )

    transport_rng = np.random.default_rng(child_seed(profile.seed, "transport"))
    process_truth["transport"] = {
        "occurrence": "weekday_distributional",
        "paired_identical_bus_rows": True,
        "amount_family": "mixture",
    }
    for event_date in pd.date_range(start_date, end_date, freq="D"):
        day = event_date.date()
        if day.weekday() < 5 and transport_rng.random() < 0.52 + 0.25 * profile.income_stability:
            if transport_rng.random() < 0.58:
                fare = round(1.75 * inflation_factor(day, start_date, profile.annual_inflation * 0.5), 2)
                # Two visually identical rows can represent two genuine journeys.
                add("current", day, "TFL BUS JOURNEY", -fare, "transport", "transport", ["distributional", "periodic"])
                add("current", day, "TFL BUS JOURNEY", -fare, "transport", "transport", ["distributional", "periodic"])
            else:
                fare = float(transport_rng.choice([3.20, 4.60, 6.40, 9.20]))
                add(
                    "current",
                    day,
                    "TFL RAIL TRAVEL",
                    -fare * inflation_factor(day, start_date, profile.annual_inflation * 0.5),
                    "transport",
                    "transport",
                    ["distributional", "periodic"],
                )
        elif day.weekday() >= 5 and transport_rng.random() < 0.08 + 0.28 * profile.discretionary_intensity:
            amount = float(transport_rng.lognormal(math.log(14.0), 0.45))
            add("current", day, "CITY TAXI", -amount, "transport", "transport", ["spontaneous", "distributional"])

    shopping_rng = np.random.default_rng(child_seed(profile.seed, "shopping"))
    shopping_lambda = 0.05 + 0.58 * profile.discretionary_intensity
    process_truth["shopping"] = {
        "occurrence": "weekly_spontaneous",
        "weekly_lambda": round(shopping_lambda, 3),
        "amount_family": "heavy_tailed_lognormal",
    }
    for week in week_starts:
        count = int(shopping_rng.poisson(shopping_lambda))
        for _ in range(count):
            event_date = _weighted_weekday(
                shopping_rng,
                week.date(),
                np.array([0.06, 0.07, 0.09, 0.11, 0.20, 0.31, 0.16]),
                start_date,
                end_date,
            )
            amount = float(
                shopping_rng.lognormal(
                    mean=math.log(28 + 65 * profile.discretionary_intensity),
                    sigma=0.48 + 0.35 * profile.spending_volatility,
                )
            )
            add(
                "current",
                event_date,
                str(shopping_rng.choice(["AMAZON MARKETPLACE", "CITY DEPARTMENT STORE", "ONLINE SHOP", "ELECTRONICS STORE"])),
                -amount * inflation_factor(event_date, start_date, profile.annual_inflation),
                "shopping",
                "shopping",
                ["spontaneous", "distributional"],
            )

    health_rng = np.random.default_rng(child_seed(profile.seed, "health"))
    for month in pd.period_range(start=start_date, end=end_date, freq="M"):
        if health_rng.random() < 0.18:
            event_date = _clamped_date(month.year, month.month, int(health_rng.integers(1, 26)))
            amount = float(health_rng.lognormal(math.log(24.0), 0.55))
            add("current", event_date, "LOCAL PHARMACY", -amount, "health", "health", ["spontaneous", "distributional"])

    shock_rng = np.random.default_rng(child_seed(profile.seed, "shocks"))
    expected_shocks = ((end_date - start_date).days / 365.2425) * (0.12 + 1.35 * profile.shock_exposure)
    shock_count = int(shock_rng.poisson(max(0.0, expected_shocks)))
    shock_descriptions = ["EMERGENCY HOME REPAIR", "VEHICLE REPAIR", "REPLACEMENT APPLIANCE", "URGENT DENTAL COST"]
    process_truth["shocks"] = {
        "occurrence": "rare_spontaneous",
        "expected_annual_rate": round(0.12 + 1.35 * profile.shock_exposure, 3),
        "amount_family": "heavy_tailed_lognormal",
    }
    total_days = (end_date - start_date).days
    for _ in range(shock_count):
        event_date = start_date + timedelta(days=int(shock_rng.integers(0, max(1, total_days + 1))))
        amount = float(shock_rng.lognormal(math.log(420.0), 0.72))
        add(
            "current",
            event_date,
            str(shock_rng.choice(shock_descriptions)),
            -amount,
            "other",
            "shocks",
            ["spontaneous"],
        )

    if savings is not None:
        transfer_rng = np.random.default_rng(child_seed(profile.seed, "transfers"))
        process_truth["savings_transfer"] = {
            "occurrence": "monthly_periodic_probability",
            "probability": round(0.45 + 0.50 * profile.savings_propensity, 3),
            "income_linked": True,
        }
        for month in pd.period_range(start=start_date, end=end_date, freq="M"):
            if transfer_rng.random() > 0.45 + 0.50 * profile.savings_propensity:
                continue
            event_date = _clamped_date(month.year, month.month, min(28, profile.payday + 1))
            amount = profile.monthly_income * profile.savings_propensity * float(transfer_rng.uniform(0.58, 1.08))
            amount = max(20.0, amount)
            transfer_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"nimo:{profile.seed}:savings-transfer:{event_date.isoformat()}",
                )
            )
            add(
                "current",
                event_date,
                "TRANSFER TO SAVINGS",
                -amount,
                "savings",
                "savings_transfer",
                ["periodic", "distributional"],
                event_id=transfer_id,
            )
            add(
                "savings",
                event_date,
                "TRANSFER FROM CURRENT",
                amount,
                "savings",
                "savings_transfer",
                ["periodic", "distributional"],
                event_id=transfer_id,
            )
        for month in pd.period_range(start=start_date, end=end_date, freq="M"):
            event_date = _clamped_date(month.year, month.month, monthrange(month.year, month.month)[1])
            add(
                "savings",
                event_date,
                "SAVINGS INTEREST",
                savings.opening_balance * 0.002 / 12,
                "other_income",
                "interest",
                ["periodic"],
            )

    frame = pd.DataFrame(rows)
    if frame.empty:
        raise RuntimeError("Synthetic simulation produced no transactions")
    frame["booking_date"] = pd.to_datetime(frame["booking_date"])
    frame = frame.sort_values(["account_key", "booking_date"], kind="stable").reset_index(drop=True)

    balances: list[float] = [0.0] * len(frame)
    for account_key, group in frame.groupby("account_key", sort=False):
        running = float(account_by_key[account_key].opening_balance)
        for index in group.index:
            running += float(frame.at[index, "amount"])
            balances[index] = round(running, 2)
    frame["running_balance"] = balances
    frame["booking_date"] = frame["booking_date"].dt.date
    return SimulationResult(transactions=frame, process_truth=process_truth)
