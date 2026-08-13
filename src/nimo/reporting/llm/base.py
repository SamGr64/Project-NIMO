from __future__ import annotations

from typing import Protocol

from nimo.reporting.schemas import ReportNarrative


class NarrativeProvider(Protocol):
    name: str

    def generate(self, evidence: dict, *, model: str | None = None) -> ReportNarrative: ...
