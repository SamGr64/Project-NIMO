from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ReportNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executive_summary: str
    financial_position: str
    cash_flow: str
    spending_behaviour: str
    forecast_interpretation: str
    budgets_and_goals: str
    investing: str
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    possible_actions: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
