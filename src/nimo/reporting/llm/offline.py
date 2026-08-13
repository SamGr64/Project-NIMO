from __future__ import annotations

from typing import Any

from nimo.reporting.schemas import ReportNarrative


class OfflineNarrativeProvider:
    name = "offline"

    def generate(self, evidence: dict[str, Any], *, model: str | None = None) -> ReportNarrative:
        overview = evidence.get("historical_facts", {}).get("overview", {})
        archetype = evidence.get("inferred_behaviour", {}).get("archetype", {})
        forecast = evidence.get("forecast") or {}
        budget = evidence.get("budget") or {}
        goals = evidence.get("goals") or []
        investment = evidence.get("investment") or {}
        savings_rate = overview.get("savings_rate")
        savings_text = "not available" if savings_rate is None else f"{float(savings_rate) * 100:.1f}%"
        final = forecast.get("final_balance", {}) if isinstance(forecast, dict) else {}
        forecast_text = (
            "No stored forecast was included."
            if not final
            else f"The baseline simulation's median final balance is {float(final.get('median', 0)):,.2f}, with a 10th–90th percentile range of {float(final.get('p10', 0)):,.2f} to {float(final.get('p90', 0)):,.2f}."
        )
        goal_text = "No active goals were included." if not goals else f"{len(goals)} active goal{'s are' if len(goals) != 1 else ' is'} tracked; each should be interpreted using its simulated completion probability."
        investing_text = (
            "No investment simulation was included."
            if not investment
            else "The investment section uses an educational sandbox and must not be treated as personalised investment advice or a market prediction."
        )
        risks: list[str] = []
        if overview.get("net_cash_flow", 0) < 0:
            risks.append("External spending exceeded income over the selected period.")
        if forecast.get("probability_negative_balance", 0) > 0.1:
            risks.append("The baseline simulation shows a material probability of the balance falling below zero.")
        if not risks:
            risks.append("Model uncertainty increases when the transaction history is short, categorisation is incomplete, or future plans are not entered.")
        opportunities = [
            "Review categories with high variability or frequent outliers before setting restrictive budgets.",
            "Add known future events and income changes to improve the relevance of scenarios.",
        ]
        actions = [
            "Confirm uncategorised transactions and internal-transfer matches.",
            "Compare the baseline with at least one user-defined scenario before relying on a goal date.",
        ]
        return ReportNarrative(
            executive_summary=(
                f"The selected history ends with an estimated balance of {float(overview.get('total_balance', 0)):,.2f}. "
                f"External income was {float(overview.get('total_income', 0)):,.2f}, external spending was {float(overview.get('total_spend', 0)):,.2f}, and the measured savings rate was {savings_text}."
            ),
            financial_position=(
                f"Net external cash flow was {float(overview.get('net_cash_flow', 0)):,.2f}. "
                f"The profile currently contains {int(overview.get('active_accounts', 0))} active account(s) and {int(overview.get('transaction_count', 0))} active transaction rows."
            ),
            cash_flow=(
                "Internal transfers are excluded from external income and expenditure when NIMO has matched the two legs. "
                "Transfer confidence and manual review remain important where descriptions or posting dates differ."
            ),
            spending_behaviour=(
                f"NIMO's descriptive archetype is “{archetype.get('label', 'insufficient history')}” with confidence {float(archetype.get('confidence', 0)):.0%}. "
                "This label summarises detected timing, variability and outlier patterns; it is not a judgement or a regulated risk classification."
            ),
            forecast_interpretation=forecast_text,
            budgets_and_goals=goal_text + (" A budget evaluation is included." if budget else " No budget evaluation was included."),
            investing=investing_text,
            risks=risks,
            opportunities=opportunities,
            possible_actions=actions,
            caveats=[
                "Forecast ranges depend on historical data, selected assumptions and Monte Carlo sampling.",
                "Unexpected life events, market changes and incorrect categories can materially change outcomes.",
                "NIMO provides educational analysis, not regulated financial, tax or investment advice.",
            ],
        )
