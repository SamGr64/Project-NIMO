from __future__ import annotations

from dataclasses import dataclass

from nimo.generation.processes.spontaneous import SpontaneousProcess


@dataclass(frozen=True, slots=True)
class ShockProcess(SpontaneousProcess):
    median_amount: float = 400.0
    log_sigma: float = 0.7
