from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import pandas as pd


class LocalMarketDataProvider:
    name = "local_educational"

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(str(files("nimo.investing").joinpath("data/educational_market.csv")))

    def history(self, symbols: list[str] | None = None) -> pd.DataFrame:
        frame = pd.read_csv(self.path, parse_dates=["date"])
        if symbols:
            requested = {symbol.upper() for symbol in symbols}
            frame = frame.loc[frame["symbol"].str.upper().isin(requested)]
        return frame.sort_values(["date", "symbol"]).reset_index(drop=True)

    def list_assets(self) -> pd.DataFrame:
        frame = self.history()
        return (
            frame.sort_values("date")
            .groupby("symbol", as_index=False)
            .agg(
                name=("name", "last"),
                asset_type=("asset_type", "last"),
                latest_date=("date", "max"),
                latest_price=("price", "last"),
                is_synthetic=("is_synthetic", "last"),
            )
            .sort_values("symbol")
        )
