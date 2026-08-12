from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pandas as pd

from nimo.generation.accounts import SyntheticAccount


class StatementRenderer(Protocol):
    def render(
        self,
        transactions: pd.DataFrame,
        account: SyntheticAccount,
        output_dir: Path,
        *,
        format_name: str,
    ) -> Path: ...
