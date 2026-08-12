from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class TransferEvent:
    event_id: str
    event_date: date
    source_account: str
    destination_account: str
    amount: float
