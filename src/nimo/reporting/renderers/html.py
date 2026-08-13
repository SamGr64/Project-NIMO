from __future__ import annotations

from pathlib import Path
from typing import Any

from nimo.reporting.renderers.common import escape, forecast_svg, money, percent
from nimo.reporting.schemas import ReportNarrative


def render_html(*, evidence: dict[str, Any], narrative: ReportNarrative, output_path: Path) -> Path:
    overview = evidence["historical_facts"]["overview"]
    categories = [
        row for row in evidence["historical_facts"].get("categories", []) if float(row.get("spend") or 0.0) > 0
    ][:10]
    forecast = evidence.get("forecast") or {}
    budget = evidence.get("budget") or {}
    goals = evidence.get("goals") or []
    investment = evidence.get("investment") or {}
    archetype = evidence.get("inferred_behaviour", {}).get("archetype", {})

    category_rows = "".join(
        "<tr>"
        f"<td>{escape(row.get('category_label', row.get('category', 'Uncategorised')))}</td>"
        f"<td class=\"number\">{money(row.get('spend'))}</td>"
        f"<td class=\"number\">{escape(row.get('transaction_count', row.get('transactions', '')))}</td>"
        "</tr>"
        for row in categories
    ) or '<tr><td colspan="3">No category rows available.</td></tr>'

    sections = [
        ("Executive summary", narrative.executive_summary),
        ("Financial position", narrative.financial_position),
        ("Cash flow", narrative.cash_flow),
        ("Spending behaviour", narrative.spending_behaviour),
        ("Forecast interpretation", narrative.forecast_interpretation),
        ("Budgets and goals", narrative.budgets_and_goals),
        ("Investing sandbox", narrative.investing),
    ]
    section_html = "".join(
        f"<section class=\"narrative\"><h2>{escape(title)}</h2><p>{escape(text)}</p></section>"
        for title, text in sections
    )
    list_html = "".join(
        _list_section(title, items, css_class)
        for title, items, css_class in [
            ("Risks", narrative.risks, "risk"),
            ("Opportunities", narrative.opportunities, "opportunity"),
            ("Possible actions", narrative.possible_actions, "action"),
            ("Caveats", narrative.caveats, "caveat"),
        ]
    )

    forecast_html = _forecast_summary(forecast)
    budget_html = _budget_table(budget)
    goals_html = _goals_table(goals)
    investment_html = _investment_summary(investment)
    period_start = evidence["period"].get("start") or "earliest available"
    period_end = evidence["period"].get("end") or "latest available"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Project NIMO report - {escape(evidence['user'])}</title>
<style>
:root {{ --ink:#16231b; --muted:#5f6b75; --accent:#31a247; --accent-dark:#237a36; --surface:#f5f8f6; --surface-2:#edf4ef; --border:#d7e0da; --danger:#a33b3b; --warning:#9a6a18; }}
* {{ box-sizing:border-box; }}
body {{ color:var(--ink); background:#eef2ef; font-family:"Segoe UI",Arial,sans-serif; line-height:1.55; margin:0; }}
main {{ max-width:1040px; margin:28px auto; background:#fff; box-shadow:0 12px 40px rgba(28,50,35,.10); }}
header {{ background:linear-gradient(120deg,#183e27,#2c8840); color:#fff; padding:38px 44px 32px; }}
header .eyebrow {{ letter-spacing:.12em; text-transform:uppercase; font-size:.78rem; opacity:.82; margin:0 0 8px; }}
h1 {{ margin:0; font-size:2.15rem; line-height:1.15; }}
header .subtitle {{ margin:.6rem 0 0; opacity:.90; }}
.content {{ padding:32px 44px 42px; }}
.grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin:0 0 28px; }}
.card {{ border:1px solid var(--border); border-radius:12px; padding:15px 16px; background:var(--surface); min-height:88px; }}
.card strong {{ display:block; font-size:.78rem; text-transform:uppercase; letter-spacing:.04em; color:var(--muted); margin-bottom:5px; }}
.card .value {{ font-size:1.45rem; font-weight:700; color:var(--accent-dark); }}
.card small {{ display:block; color:var(--muted); margin-top:2px; }}
section {{ margin:0 0 28px; break-inside:avoid; }}
h2 {{ margin:0 0 10px; font-size:1.28rem; color:#1b5d2c; }}
h3 {{ margin:0 0 8px; font-size:1rem; }}
p {{ margin:.25rem 0 .65rem; }}
.narrative {{ border-left:4px solid var(--accent); padding:2px 0 2px 18px; }}
.two-column {{ display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:22px; align-items:start; }}
.panel {{ border:1px solid var(--border); border-radius:12px; padding:18px; background:#fff; }}
.panel.tint {{ background:var(--surface); }}
table {{ border-collapse:collapse; width:100%; font-size:.93rem; }}
th,td {{ padding:9px 10px; border-bottom:1px solid var(--border); text-align:left; vertical-align:middle; }}
th {{ background:var(--surface-2); font-size:.78rem; text-transform:uppercase; letter-spacing:.035em; color:#41505c; }}
td.number, th.number {{ text-align:right; font-variant-numeric:tabular-nums; }}
svg {{ width:100%; height:auto; border:1px solid var(--border); border-radius:10px; }}
ul {{ margin:.35rem 0 0; padding-left:1.35rem; }}
li {{ margin:.35rem 0; }}
.callout {{ border-radius:10px; padding:14px 16px; background:var(--surface); border-left:4px solid var(--accent); }}
.callout.risk {{ border-left-color:var(--danger); }} .callout.caveat {{ border-left-color:var(--warning); }}
footer {{ border-top:1px solid var(--border); padding-top:18px; color:var(--muted); font-size:.82rem; }}
.badge {{ display:inline-block; border-radius:999px; padding:3px 9px; background:#dff1e4; color:#1d6530; font-size:.78rem; font-weight:600; }}
@media (max-width:760px) {{ main {{ margin:0; }} header,.content {{ padding-left:22px; padding-right:22px; }} .grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} .two-column {{ grid-template-columns:1fr; }} }}
@media print {{ body {{ background:#fff; }} main {{ max-width:none; margin:0; box-shadow:none; }} header {{ print-color-adjust:exact; -webkit-print-color-adjust:exact; }} .content {{ padding:24px 30px; }} section,.panel,.card,table {{ break-inside:avoid; }} }}
</style></head><body><main>
<header><p class="eyebrow">Project NIMO</p><h1>Personal financial report</h1><p class="subtitle">{escape(evidence['user'])} &middot; {escape(period_start)} to {escape(period_end)}</p></header>
<div class="content">
<div class="grid">
<div class="card"><strong>Total balance</strong><span class="value">{money(overview.get('total_balance'))}</span><small>{escape(overview.get('active_accounts', 0))} active accounts</small></div>
<div class="card"><strong>External income</strong><span class="value">{money(overview.get('total_income'))}</span><small>Selected period</small></div>
<div class="card"><strong>External spend</strong><span class="value">{money(overview.get('total_spend'))}</span><small>Transfers excluded</small></div>
<div class="card"><strong>Savings rate</strong><span class="value">{percent(overview.get('savings_rate'))}</span><small>Net external cash flow {money(overview.get('net_cash_flow'))}</small></div>
</div>
<section class="panel tint"><h2>Behaviour profile</h2><p><span class="badge">{escape(archetype.get('label', 'Insufficient history'))}</span> &nbsp; Confidence: {percent(archetype.get('confidence'), digits=0)}</p><p>This is a descriptive summary of detected behaviour, not a judgement or regulated risk classification.</p></section>
{section_html}
<section><h2>Forecast balance range</h2>{forecast_svg(forecast.get('months', [])) if forecast.get('months') else '<p>No forecast chart available.</p>'}{forecast_html}</section>
<div class="two-column"><section class="panel"><h2>Leading spending categories</h2><table><thead><tr><th>Category</th><th class="number">Spend</th><th class="number">Transactions</th></tr></thead><tbody>{category_rows}</tbody></table></section><section class="panel"><h2>Budget snapshot</h2>{budget_html}</section></div>
<section><h2>Goals</h2>{goals_html}</section>
<section><h2>Investing sandbox</h2>{investment_html}</section>
<div class="two-column">{list_html}</div>
<footer>Evidence version: {escape(evidence['source_data_version'])}. Generated by Project NIMO. Educational analysis only; not financial, tax or investment advice.</footer>
</div></main></body></html>""",
        encoding="utf-8",
    )
    return output_path


def _forecast_summary(forecast: dict[str, Any]) -> str:
    if not forecast:
        return "<p>No stored forecast was included.</p>"
    final = forecast.get("final_balance", {})
    return (
        '<div class="grid" style="margin-top:12px">'
        f'<div class="card"><strong>Median final balance</strong><span class="value">{money(final.get("median"))}</span></div>'
        f'<div class="card"><strong>10%-90% range</strong><span class="value" style="font-size:1.05rem">{money(final.get("p10"))}<br>to {money(final.get("p90"))}</span></div>'
        f'<div class="card"><strong>Expected income</strong><span class="value">{money(forecast.get("expected_total_income"))}</span></div>'
        f'<div class="card"><strong>Risk below zero</strong><span class="value">{percent(forecast.get("probability_negative_balance"))}</span></div>'
        "</div>"
    )


def _budget_table(budget: dict[str, Any]) -> str:
    lines = budget.get("lines", []) if budget else []
    if not lines:
        return "<p>No budget evaluation was included.</p>"
    rows = "".join(
        "<tr>"
        f"<td>{escape(line.get('label', line.get('category_slug', 'Budget line')))}</td>"
        f"<td class=\"number\">{money(line.get('amount'))}</td>"
        f"<td class=\"number\">{percent(line.get('probability_within_budget'))}</td>"
        "</tr>"
        for line in lines[:10]
    )
    return (
        f"<p><strong>Total monthly budget:</strong> {money(budget.get('total_budget'))}<br>"
        f"<strong>Forecast median:</strong> {money(budget.get('forecast_total_spend_median'))}</p>"
        "<table><thead><tr><th>Line</th><th class=\"number\">Budget</th><th class=\"number\">Chance within</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def _goals_table(goals: list[dict[str, Any]]) -> str:
    if not goals:
        return "<p>No active goals were included.</p>"
    rows = "".join(
        "<tr>"
        f"<td>{escape(goal.get('name', 'Goal'))}</td>"
        f"<td class=\"number\">{money(goal.get('current_amount'))}</td>"
        f"<td class=\"number\">{money(goal.get('target_amount'))}</td>"
        f"<td>{escape(goal.get('target_date', '-'))}</td>"
        f"<td class=\"number\">{percent(goal.get('probability_achieved'))}</td>"
        "</tr>"
        for goal in goals
    )
    return (
        "<table><thead><tr><th>Goal</th><th class=\"number\">Current</th><th class=\"number\">Target</th>"
        f"<th>Target date</th><th class=\"number\">Probability</th></tr></thead><tbody>{rows}</tbody></table>"
    )


def _investment_summary(investment: dict[str, Any]) -> str:
    if not investment:
        return "<p>No investment simulation was included.</p>"
    final = investment.get("final_value", {})
    contributed = investment.get("total_contributed", {})
    portfolio = investment.get("portfolio", {})
    allocations = portfolio.get("allocations", {})
    allocation_text = ", ".join(f"{escape(symbol)} {float(weight) * 100:.0f}%" for symbol, weight in allocations.items())
    return (
        '<div class="grid">'
        f'<div class="card"><strong>Portfolio</strong><span class="value" style="font-size:1.0rem">{escape(portfolio.get("name", "Educational portfolio"))}</span><small>{allocation_text}</small></div>'
        f'<div class="card"><strong>Median final value</strong><span class="value">{money(final.get("median"))}</span><small>{investment.get("horizon_years", "-")} year horizon</small></div>'
        f'<div class="card"><strong>Total contributed</strong><span class="value">{money(contributed.get("median"))}</span><small>Median simulated contributions</small></div>'
        f'<div class="card"><strong>Chance below contributions</strong><span class="value">{percent(investment.get("probability_loss_vs_contributions"))}</span><small>Educational simulation only</small></div>'
        "</div>"
        f'<p class="callout caveat">{escape(investment.get("educational_notice", "Simulated outcomes are not predictions or recommendations."))}</p>'
    )


def _list_section(title: str, items: list[str], css_class: str) -> str:
    body = "".join(f"<li>{escape(item)}</li>" for item in items) or "<li>None recorded.</li>"
    return f'<section class="callout {css_class}"><h2>{escape(title)}</h2><ul>{body}</ul></section>'
