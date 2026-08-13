from __future__ import annotations

from typing import Protocol

import pandas as pd


class MarketDataProvider(Protocol):
    name: str

    def list_assets(self) -> pd.DataFrame: ...

    def history(self, symbols: list[str] | None = None) -> pd.DataFrame: ...
