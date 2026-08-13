from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def asset_statistics(history: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for symbol, group in history.groupby("symbol"):
        group = group.sort_values("date")
        returns = pd.to_numeric(group["monthly_return"], errors="coerce").dropna().to_numpy(dtype=float)
        if len(returns) == 0:
            continue
        cumulative = np.cumprod(1.0 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = cumulative / running_max - 1.0
        annualised_return = float(np.prod(1.0 + returns) ** (12.0 / len(returns)) - 1.0)
        annualised_volatility = float(np.std(returns, ddof=1) * np.sqrt(12.0)) if len(returns) > 1 else 0.0
        one_year = float(np.prod(1.0 + returns[-12:]) - 1.0) if len(returns) >= 12 else None
        five_year = float(np.prod(1.0 + returns[-60:]) ** (12.0 / min(60, len(returns))) - 1.0) if len(returns) >= 24 else None
        rows.append(
            {
                "symbol": symbol,
                "name": str(group["name"].iloc[-1]) if "name" in group else symbol,
                "asset_type": str(group["asset_type"].iloc[-1]) if "asset_type" in group else "custom",
                "observations": int(len(returns)),
                "annualised_return": round(annualised_return, 6),
                "annualised_volatility": round(annualised_volatility, 6),
                "maximum_drawdown": round(float(np.min(drawdowns)), 6),
                "one_year_return": None if one_year is None else round(one_year, 6),
                "five_year_annualised_return": None if five_year is None else round(five_year, 6),
                "latest_price": round(float(group["price"].iloc[-1]), 6) if "price" in group else None,
                "latest_date": str(pd.Timestamp(group["date"].max()).date()),
                "is_synthetic": bool(group["is_synthetic"].iloc[-1]) if "is_synthetic" in group else False,
            }
        )
    return sorted(rows, key=lambda item: item["symbol"])


def correlation_matrix(history: pd.DataFrame, symbols: list[str] | None = None) -> pd.DataFrame:
    work = history
    if symbols:
        work = work.loc[work["symbol"].isin(symbols)]
    pivot = work.pivot_table(index="date", columns="symbol", values="monthly_return", aggfunc="last")
    return pivot.corr()
