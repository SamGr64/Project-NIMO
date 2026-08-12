from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_statement_csv(path: Path) -> pd.DataFrame:
    """Read a CSV while allowing common comma, semicolon and tab delimiters."""
    try:
        frame = pd.read_csv(path, sep=None, engine="python", dtype=object)
    except (UnicodeDecodeError, pd.errors.ParserError):
        frame = pd.read_csv(path, dtype=object, encoding="latin-1")
    if frame.empty:
        raise ValueError(f"Statement contains no rows: {path}")
    frame.columns = [str(column).strip() for column in frame.columns]
    return frame
