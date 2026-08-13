from __future__ import annotations

from pathlib import Path

import pandas as pd


class CsvMarketDataProvider:
    name = "user_csv"

    def __init__(self, path: Path) -> None:
        self.path = path

    def history(self, symbols: list[str] | None = None) -> pd.DataFrame:
        frame = pd.read_csv(self.path, parse_dates=["date"])
        required = {"date", "symbol", "monthly_return"}
        missing = required - set(frame.columns)
        if missing:
            raise KeyError(f"Market CSV missing columns: {sorted(missing)}")
        if symbols:
            frame = frame.loc[frame["symbol"].isin(symbols)]
        return frame.sort_values(["date", "symbol"]).reset_index(drop=True)

    def list_assets(self) -> pd.DataFrame:
        frame = self.history()
        rows = []
        for symbol, group in frame.groupby("symbol"):
            rows.append(
                {
                    "symbol": symbol,
                    "name": group.get("name", pd.Series([symbol])).iloc[-1],
                    "asset_type": group.get("asset_type", pd.Series(["custom"])).iloc[-1],
                    "latest_date": group["date"].max(),
                    "latest_price": group.get("price", pd.Series([float("nan")])).iloc[-1],
                    "is_synthetic": bool(group.get("is_synthetic", pd.Series([False])).iloc[-1]),
                }
            )
        return pd.DataFrame(rows)
