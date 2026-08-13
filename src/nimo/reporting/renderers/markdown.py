from __future__ import annotations

from pathlib import Path
from typing import Any

from nimo.reporting.renderers.common import money, percent, rows_as_markdown
from nimo.reporting.schemas import ReportNarrative


def render_markdown(*, evidence: dict[str, Any], narrative: ReportNarrative, output_path: Path) -> Path:
    overview = evidence["historical_facts"]["overview"]
    categories = [
        row for row in evidence["historical_facts"].get("categories", []) if float(row.get("spend") or 0.0) > 0
    ][:10]
    forecast = evidence.get("forecast") or {}
    budget = evidence.get("budget") or {}
    goals = evidence.get("goals") or []
    investment = evidence.get("investment") or {}
    archetype = evidence.get("inferred_behaviour", {}).get("archetype", {})

    period_start = evidence["period"].get("start") or "earliest available"
    period_end = evidence["period"].get("end") or "latest available"
    text = [
        f"# Project NIMO report - {evidence['user']}",
        "",
        f"**Period:** {period_start} to {period_end}",
        f"**Behaviour profile:** {archetype.get('label', 'Insufficient history')} ({percent(archetype.get('confidence'), digits=0)} confidence)",
        "",
        "## Key metrics",
        "",
    ]
    text.extend(
        rows_as_markdown(
            ["Metric", "Value"],
            [
                ["Total balance", money(overview.get("total_balance"))],
                ["External income", money(overview.get("total_income"))],
                ["External spend", money(overview.get("total_spend"))],
                ["Net cash flow", money(overview.get("net_cash_flow"))],
                ["Savings rate", percent(overview.get("savings_rate"))],
                ["Active accounts", overview.get("active_accounts", 0)],
                ["Transactions", overview.get("transaction_count", 0)],
            ],
        )
    )
    text.append("")

    sections = [
        ("Executive summary", narrative.executive_summary),
        ("Financial position", narrative.financial_position),
        ("Cash flow", narrative.cash_flow),
        ("Spending behaviour", narrative.spending_behaviour),
        ("Forecast interpretation", narrative.forecast_interpretation),
        ("Budgets and goals", narrative.budgets_and_goals),
        ("Investing sandbox", narrative.investing),
    ]
    for title, body in sections:
        text.extend([f"## {title}", "", body, ""])

    text.extend(["## Leading spending categories", ""])
    text.extend(
        rows_as_markdown(
            ["Category", "Spend", "Transactions"],
            [
                [
                    row.get("category_label", row.get("category", "Uncategorised")),
                    money(row.get("spend")),
                    row.get("transaction_count", row.get("transactions", "")),
                ]
                for row in categories
            ],
        )
    )
    text.append("")

    text.extend(["## Forecast summary", ""])
    if forecast:
        final = forecast.get("final_balance", {})
        text.extend(
            rows_as_markdown(
                ["Measure", "Value"],
                [
                    ["Scenario", forecast.get("scenario", "Baseline")],
                    ["Horizon", f"{forecast.get('horizon_months', '-')} months"],
                    ["Median final balance", money(final.get("median"))],
                    ["10%-90% final range", f"{money(final.get('p10'))} to {money(final.get('p90'))}"],
                    ["Probability below zero", percent(forecast.get("probability_negative_balance"))],
                ],
            )
        )
    else:
        text.append("_No stored forecast was included._")
    text.append("")

    text.extend(["## Budget snapshot", ""])
    lines = budget.get("lines", []) if budget else []
    if lines:
        text.extend(
            rows_as_markdown(
                ["Budget line", "Budget", "Forecast median", "Chance within"],
                [
                    [
                        line.get("label", line.get("category_slug", "Budget line")),
                        money(line.get("amount")),
                        money(line.get("forecast_median")),
                        percent(line.get("probability_within_budget")),
                    ]
                    for line in lines
                ],
            )
        )
    else:
        text.append("_No budget evaluation was included._")
    text.append("")

    text.extend(["## Goals", ""])
    if goals:
        text.extend(
            rows_as_markdown(
                ["Goal", "Current", "Target", "Target date", "Probability"],
                [
                    [
                        goal.get("name", "Goal"),
                        money(goal.get("current_amount")),
                        money(goal.get("target_amount")),
                        goal.get("target_date", "-"),
                        percent(goal.get("probability_achieved")),
                    ]
                    for goal in goals
                ],
            )
        )
    else:
        text.append("_No active goals were included._")
    text.append("")

    text.extend(["## Investment simulation", ""])
    if investment:
        final = investment.get("final_value", {})
        contributed = investment.get("total_contributed", {})
        text.extend(
            rows_as_markdown(
                ["Measure", "Value"],
                [
                    ["Portfolio", investment.get("portfolio", {}).get("name", "Educational portfolio")],
                    ["Horizon", f"{investment.get('horizon_years', '-')} years"],
                    ["Median final value", money(final.get("median"))],
                    ["10%-90% final range", f"{money(final.get('p10'))} to {money(final.get('p90'))}"],
                    ["Median contributions", money(contributed.get("median"))],
                    ["Probability below contributions", percent(investment.get("probability_loss_vs_contributions"))],
                    ["Probability of negative cash", percent(investment.get("probability_negative_cash"))],
                ],
            )
        )
        text.extend(["", f"> {investment.get('educational_notice', 'Simulations are not predictions or recommendations.')}"])
    else:
        text.append("_No investment simulation was included._")
    text.append("")

    for title, items in [
        ("Risks", narrative.risks),
        ("Opportunities", narrative.opportunities),
        ("Possible actions", narrative.possible_actions),
        ("Caveats", narrative.caveats),
    ]:
        text.extend([f"## {title}", ""] + ([f"- {item}" for item in items] or ["- None recorded."]) + [""])

    text.extend(
        [
            "---",
            "",
            f"Evidence version: `{evidence['source_data_version']}`",
            "",
            "Generated by Project NIMO. Educational analysis only; not financial, tax or investment advice.",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(text), encoding="utf-8")
    return output_path
