from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass(frozen=True, slots=True)
class PeriodicSchedule:
    cadence: str
    day: int = 1
    probability: float = 1.0

    def dates(self, start: date, end: date) -> list[date]:
        if self.cadence == "monthly":
            return [
                date(period.year, period.month, min(self.day, monthrange(period.year, period.month)[1]))
                for period in pd.period_range(start=start, end=end, freq="M")
            ]
        if self.cadence == "weekly":
            return [value.date() for value in pd.date_range(start, end, freq=f"W-{_weekday(self.day)}")]
        if self.cadence == "yearly":
            return [date(year, 1, min(self.day, 31)) for year in range(start.year, end.year + 1)]
        raise ValueError(f"Unsupported periodic cadence: {self.cadence}")


def _weekday(index: int) -> str:
    names = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    return names[index % 7]
