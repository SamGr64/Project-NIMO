from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np


@dataclass(frozen=True, slots=True)
class SpontaneousProcess:
    annual_rate: float

    def sample_dates(self, rng: np.random.Generator, start: date, end: date) -> list[date]:
        years = max(0.0, (end - start).days / 365.2425)
        count = int(rng.poisson(self.annual_rate * years))
        span = max(1, (end - start).days + 1)
        return sorted(start + timedelta(days=int(rng.integers(0, span))) for _ in range(count))
