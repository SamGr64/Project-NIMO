from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

from nimo.reporting.renderers.common import as_float, money, percent, safe_text
from nimo.reporting.schemas import ReportNarrative


def render_pdf(*, evidence: dict[str, Any], narrative: ReportNarrative, output_path: Path) -> Path:
    try:
        from reportlab.graphics.shapes import Drawing, Line, Polygon, PolyLine, Rect, String
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            HRFlowable,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        raise RuntimeError("Install Project NIMO with the reports extra to render PDF reports") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page_width, _ = A4
    margin = 17 * mm
    content_width = page_width - 2 * margin
    palette = {
        "ink": colors.HexColor("#16231B"),
        "muted": colors.HexColor("#5F6B75"),
        "accent": colors.HexColor("#31A247"),
        "accent_dark": colors.HexColor("#1F6D31"),
        "banner": colors.HexColor("#183E27"),
        "surface": colors.HexColor("#F3F7F4"),
        "surface_2": colors.HexColor("#E7F0E9"),
        "border": colors.HexColor("#D4DED7"),
        "danger": colors.HexColor("#9D3C3C"),
        "warning": colors.HexColor("#976719"),
        "white": colors.white,
    }

    sample = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "NimoTitle",
            parent=sample["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=palette["white"],
            spaceAfter=3 * mm,
        ),
        "subtitle": ParagraphStyle(
            "NimoSubtitle",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#E8F4EB"),
        ),
        "h1": ParagraphStyle(
            "NimoH1",
            parent=sample["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=palette["accent_dark"],
            spaceBefore=5 * mm,
            spaceAfter=2.5 * mm,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "NimoH2",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=15,
            textColor=palette["ink"],
            spaceBefore=3 * mm,
            spaceAfter=1.5 * mm,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "NimoBody",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=9.6,
            leading=14.2,
            textColor=palette["ink"],
            spaceAfter=2.4 * mm,
        ),
        "small": ParagraphStyle(
            "NimoSmall",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=10.5,
            textColor=palette["muted"],
        ),
        "metric_label": ParagraphStyle(
            "NimoMetricLabel",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.2,
            leading=9,
            textTransform="uppercase",
            textColor=palette["muted"],
            spaceAfter=1.2 * mm,
        ),
        "metric_value": ParagraphStyle(
            "NimoMetricValue",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=18,
            textColor=palette["accent_dark"],
        ),
        "table_header": ParagraphStyle(
            "NimoTableHeader",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=palette["ink"],
            alignment=TA_LEFT,
        ),
        "table_cell": ParagraphStyle(
            "NimoTableCell",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=10.2,
            textColor=palette["ink"],
        ),
        "table_number": ParagraphStyle(
            "NimoTableNumber",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=10.2,
            textColor=palette["ink"],
            alignment=TA_RIGHT,
        ),
        "callout": ParagraphStyle(
            "NimoCallout",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=9.0,
            leading=13.3,
            textColor=palette["ink"],
        ),
        "center_small": ParagraphStyle(
            "NimoCenterSmall",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=10,
            textColor=palette["muted"],
            alignment=TA_CENTER,
        ),
    }

    def paragraph(text: Any, style: str = "body") -> Paragraph:
        return Paragraph(xml_escape(safe_text(text)), styles[style])

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

    title_block = Table(
        [[
            [
                paragraph("PROJECT NIMO", "subtitle"),
                Paragraph("Personal financial report", styles["title"]),
                paragraph(f"{evidence['user']}  |  {period_start} to {period_end}", "subtitle"),
            ]
        ]],
        colWidths=[content_width],
        hAlign="LEFT",
    )
    title_block.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), palette["banner"]),
                ("BOX", (0, 0), (-1, -1), 0, palette["banner"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 10 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 9 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9 * mm),
            ]
        )
    )

    metric_cells = [
        _metric_cell(paragraph, "Total balance", money(overview.get("total_balance"))),
        _metric_cell(paragraph, "External income", money(overview.get("total_income"))),
        _metric_cell(paragraph, "External spend", money(overview.get("total_spend"))),
        _metric_cell(paragraph, "Savings rate", percent(overview.get("savings_rate"))),
    ]
    metric_table = Table(
        [metric_cells[:2], metric_cells[2:]],
        colWidths=[content_width / 2 - 2 * mm, content_width / 2 - 2 * mm],
        hAlign="LEFT",
    )
    metric_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), palette["surface"]),
                ("BOX", (0, 0), (-1, -1), 0.6, palette["border"]),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, palette["border"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    behaviour_callout = Table(
        [[
            paragraph("Behaviour profile", "h2"),
            paragraph(
                f"{archetype.get('label', 'Insufficient history')} ({percent(archetype.get('confidence'), digits=0)} confidence). "
                "This is a descriptive summary of detected behaviour, not a judgement or regulated risk classification.",
                "callout",
            ),
        ]],
        colWidths=[39 * mm, content_width - 39 * mm],
        hAlign="LEFT",
    )
    behaviour_callout.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), palette["surface_2"]),
                ("BOX", (0, 0), (-1, -1), 0.7, palette["border"]),
                ("LINEBEFORE", (0, 0), (0, -1), 3, palette["accent"]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
            ]
        )
    )

    story: list[Any] = [
        title_block,
        Spacer(1, 5 * mm),
        metric_table,
        Spacer(1, 4 * mm),
        behaviour_callout,
        paragraph("Executive summary", "h1"),
        paragraph(narrative.executive_summary),
        paragraph("Financial position", "h1"),
        paragraph(narrative.financial_position),
        paragraph("Cash flow", "h2"),
        paragraph(narrative.cash_flow),
    ]

    if categories:
        story.extend(
            [
                paragraph("Spending and categories", "h1"),
                paragraph(narrative.spending_behaviour),
                _categories_table(categories, paragraph, content_width, palette, Table, TableStyle),
            ]
        )
    else:
        story.extend([paragraph("Spending and categories", "h1"), paragraph(narrative.spending_behaviour)])

    if forecast:
        story.extend(
            [
                paragraph("Forecast and scenarios", "h1"),
                paragraph(narrative.forecast_interpretation),
                _forecast_drawing(
                    forecast.get("months", []),
                    width=content_width,
                    height=55 * mm,
                    palette=palette,
                    Drawing=Drawing,
                    Line=Line,
                    Polygon=Polygon,
                    PolyLine=PolyLine,
                    Rect=Rect,
                    String=String,
                ),
                Spacer(1, 2 * mm),
                _forecast_metric_table(forecast, paragraph, content_width, palette, Table, TableStyle),
            ]
        )
    else:
        story.extend([paragraph("Forecast and scenarios", "h1"), paragraph(narrative.forecast_interpretation)])

    story.extend([paragraph("Budgeting and goals", "h1"), paragraph(narrative.budgets_and_goals)])
    if budget.get("lines"):
        story.append(_budget_table(budget, paragraph, content_width, palette, Table, TableStyle))
    else:
        story.append(paragraph("No budget evaluation was included."))
    if goals:
        story.extend([Spacer(1, 2 * mm), paragraph("Active goals", "h2")])
        story.append(_goals_table(goals, paragraph, content_width, palette, Table, TableStyle))

    story.extend([paragraph("Investing sandbox", "h1"), paragraph(narrative.investing)])
    if investment:
        story.append(_investment_table(investment, paragraph, content_width, palette, Table, TableStyle))
        story.append(
            _callout_table(
                investment.get(
                    "educational_notice",
                    "Simulated outcomes are not predictions or recommendations.",
                ),
                paragraph,
                content_width,
                palette["warning"],
                palette["surface"],
                Table,
                TableStyle,
            )
        )
    else:
        story.append(paragraph("No investment simulation was included."))

    story.extend(
        [
            paragraph("Risks, opportunities and actions", "h1"),
            _two_column_lists(
                narrative.risks,
                narrative.opportunities,
                paragraph,
                content_width,
                palette,
                Table,
                TableStyle,
            ),
            Spacer(1, 3 * mm),
            paragraph("Possible actions", "h2"),
        ]
    )
    story.extend(_bullet_paragraphs(narrative.possible_actions, paragraph))
    story.extend([paragraph("Caveats", "h2")])
    story.extend(_bullet_paragraphs(narrative.caveats, paragraph))
    story.extend(
        [
            Spacer(1, 3 * mm),
            HRFlowable(width="100%", thickness=0.6, color=palette["border"]),
            Spacer(1, 2 * mm),
            paragraph(
                f"Evidence version: {evidence['source_data_version']}. Generated by Project NIMO. "
                "Educational analysis only; not financial, tax or investment advice.",
                "small",
            ),
        ]
    )

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=margin,
        leftMargin=margin,
        topMargin=17 * mm,
        bottomMargin=17 * mm,
        title=f"Project NIMO financial report - {safe_text(evidence['user'])}",
        author="Project NIMO",
        subject="Educational personal finance analysis",
    )

    def footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(palette["border"])
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, 11 * mm, page_width - doc.rightMargin, 11 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(palette["muted"])
        canvas.drawString(doc.leftMargin, 7 * mm, "Project NIMO | educational analysis")
        canvas.drawRightString(page_width - doc.rightMargin, 7 * mm, f"Page {doc.page}")
        canvas.restoreState()

    def later_page(canvas, doc) -> None:
        footer(canvas, doc)
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.setFillColor(palette["accent_dark"])
        canvas.drawString(doc.leftMargin, A4[1] - 10 * mm, "PROJECT NIMO FINANCIAL REPORT")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=later_page)
    return output_path


def _metric_cell(paragraph, label: str, value: str) -> list[Any]:
    return [paragraph(label, "metric_label"), paragraph(value, "metric_value")]


def _table_style(palette, *, header_rows: int = 1):
    from reportlab.platypus import TableStyle

    commands = [
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), palette["surface_2"]),
        ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), palette["ink"]),
        ("ROWBACKGROUNDS", (0, header_rows), (-1, -1), [colors_white(), palette["surface"]]),
        ("BOX", (0, 0), (-1, -1), 0.6, palette["border"]),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, palette["border"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    return TableStyle(commands)


def _forecast_drawing(
    rows: list[dict[str, Any]],
    *,
    width: float,
    height: float,
    palette,
    Drawing,
    Line,
    Polygon,
    PolyLine,
    Rect,
    String,
):
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, fillColor=colors_white(), strokeColor=palette["border"], strokeWidth=0.6, rx=6, ry=6))
    if not rows:
        drawing.add(String(width / 2, height / 2, "No forecast chart available", textAnchor="middle", fontName="Helvetica", fontSize=9, fillColor=palette["muted"]))
        return drawing

    left, right, top, bottom = 45.0, width - 12.0, height - 22.0, 28.0
    medians = [as_float(row.get("balance_median")) for row in rows]
    lows = [as_float(row.get("balance_p10", row.get("balance_p05"))) for row in rows]
    highs = [as_float(row.get("balance_p90", row.get("balance_p95"))) for row in rows]
    values = medians + lows + highs
    minimum, maximum = min(values), max(values)
    padding = max(1.0, (maximum - minimum) * 0.08)
    minimum -= padding
    maximum += padding
    span = max(1e-9, maximum - minimum)

    def coordinate(index: int, value: float) -> tuple[float, float]:
        x = left + index * (right - left) / max(1, len(rows) - 1)
        y = bottom + (value - minimum) * (top - bottom) / span
        return x, y

    for index in range(5):
        ratio = index / 4
        y = bottom + ratio * (top - bottom)
        value = minimum + ratio * span
        drawing.add(Line(left, y, right, y, strokeColor=palette["border"], strokeWidth=0.35))
        drawing.add(
            String(
                left - 5,
                y - 2.5,
                f"£{value:,.0f}",
                textAnchor="end",
                fontName="Helvetica",
                fontSize=6.8,
                fillColor=palette["muted"],
            )
        )

    high_points = [coordinate(index, value) for index, value in enumerate(highs)]
    low_points = [coordinate(index, value) for index, value in enumerate(lows)]
    median_points = [coordinate(index, value) for index, value in enumerate(medians)]
    band = [value for point in high_points + list(reversed(low_points)) for value in point]
    median = [value for point in median_points for value in point]
    drawing.add(Polygon(band, fillColor=colors_with_alpha(palette["accent"], 0.18), strokeColor=None))
    drawing.add(PolyLine(median, strokeColor=palette["accent_dark"], strokeWidth=2.2))

    for index in sorted({0, len(rows) // 2, len(rows) - 1}):
        x, _ = coordinate(index, medians[index])
        drawing.add(
            String(
                x,
                12,
                safe_text(rows[index].get("month", str(index + 1))),
                textAnchor="middle",
                fontName="Helvetica",
                fontSize=7,
                fillColor=palette["muted"],
            )
        )
    drawing.add(Line(width - 127, height - 12, width - 107, height - 12, strokeColor=palette["accent_dark"], strokeWidth=2.2))
    drawing.add(String(width - 102, height - 15, "Median", fontName="Helvetica", fontSize=6.8, fillColor=palette["muted"]))
    drawing.add(Rect(width - 57, height - 18, 12, 9, fillColor=colors_with_alpha(palette["accent"], 0.18), strokeColor=None))
    drawing.add(String(width - 41, height - 15, "10-90%", fontName="Helvetica", fontSize=6.8, fillColor=palette["muted"]))
    return drawing


def colors_white():
    from reportlab.lib import colors

    return colors.white


def colors_with_alpha(color, alpha: float):
    from reportlab.lib.colors import Color

    return Color(color.red, color.green, color.blue, alpha=alpha)


def _forecast_metric_table(forecast, paragraph, width, palette, Table, TableStyle):
    final = forecast.get("final_balance", {})
    cells = [
        _metric_cell(paragraph, "Median final balance", money(final.get("median"))),
        _metric_cell(paragraph, "10%-90% range", f"{money(final.get('p10'))} to {money(final.get('p90'))}"),
        _metric_cell(paragraph, "Expected income", money(forecast.get("expected_total_income"))),
        _metric_cell(paragraph, "Risk below zero", percent(forecast.get("probability_negative_balance"))),
    ]
    table = Table([cells], colWidths=[width / 4] * 4, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), palette["surface"]),
                ("BOX", (0, 0), (-1, -1), 0.6, palette["border"]),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, palette["border"]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _categories_table(rows, paragraph, width, palette, Table, TableStyle):
    data = [[paragraph("Category", "table_header"), paragraph("Spend", "table_header"), paragraph("Transactions", "table_header")]]
    for row in rows:
        data.append(
            [
                paragraph(row.get("category_label", row.get("category", "Uncategorised")), "table_cell"),
                paragraph(money(row.get("spend")), "table_number"),
                paragraph(row.get("transaction_count", row.get("transactions", "")), "table_number"),
            ]
        )
    table = Table(data, colWidths=[width * 0.58, width * 0.23, width * 0.19], repeatRows=1, hAlign="LEFT")
    table.setStyle(_table_style(palette))
    return table


def _budget_table(budget, paragraph, width, palette, Table, TableStyle):
    data = [[
        paragraph("Budget line", "table_header"),
        paragraph("Budget", "table_header"),
        paragraph("Current", "table_header"),
        paragraph("Forecast", "table_header"),
        paragraph("Chance within", "table_header"),
    ]]
    for line in budget.get("lines", []):
        data.append(
            [
                paragraph(line.get("label", line.get("category_slug", "Budget line")), "table_cell"),
                paragraph(money(line.get("amount")), "table_number"),
                paragraph(money(line.get("current_period_actual")), "table_number"),
                paragraph(money(line.get("forecast_median")), "table_number"),
                paragraph(percent(line.get("probability_within_budget")), "table_number"),
            ]
        )
    table = Table(
        data,
        colWidths=[width * 0.34, width * 0.16, width * 0.16, width * 0.16, width * 0.18],
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(_table_style(palette))
    return table


def _goals_table(goals, paragraph, width, palette, Table, TableStyle):
    data = [[
        paragraph("Goal", "table_header"),
        paragraph("Current", "table_header"),
        paragraph("Target", "table_header"),
        paragraph("Target date", "table_header"),
        paragraph("Probability", "table_header"),
    ]]
    for goal in goals:
        data.append(
            [
                paragraph(goal.get("name", "Goal"), "table_cell"),
                paragraph(money(goal.get("current_amount")), "table_number"),
                paragraph(money(goal.get("target_amount")), "table_number"),
                paragraph(goal.get("target_date", "-"), "table_cell"),
                paragraph(percent(goal.get("probability_achieved")), "table_number"),
            ]
        )
    table = Table(data, colWidths=[width * 0.30, width * 0.16, width * 0.16, width * 0.20, width * 0.18], repeatRows=1, hAlign="LEFT")
    table.setStyle(_table_style(palette))
    return table


def _investment_table(investment, paragraph, width, palette, Table, TableStyle):
    final = investment.get("final_value", {})
    contributed = investment.get("total_contributed", {})
    portfolio = investment.get("portfolio", {})
    allocations = portfolio.get("allocations", {})
    allocation_text = ", ".join(f"{symbol} {float(weight) * 100:.0f}%" for symbol, weight in allocations.items()) or "-"
    data = [
        [paragraph("Measure", "table_header"), paragraph("Value", "table_header")],
        [paragraph("Portfolio", "table_cell"), paragraph(portfolio.get("name", "Educational portfolio"), "table_cell")],
        [paragraph("Allocation", "table_cell"), paragraph(allocation_text, "table_cell")],
        [paragraph("Horizon", "table_cell"), paragraph(f"{investment.get('horizon_years', '-')} years", "table_cell")],
        [paragraph("Median final value", "table_cell"), paragraph(money(final.get("median")), "table_number")],
        [paragraph("10%-90% final range", "table_cell"), paragraph(f"{money(final.get('p10'))} to {money(final.get('p90'))}", "table_number")],
        [paragraph("Median contributions", "table_cell"), paragraph(money(contributed.get("median")), "table_number")],
        [paragraph("Probability below contributions", "table_cell"), paragraph(percent(investment.get("probability_loss_vs_contributions")), "table_number")],
        [paragraph("Probability of negative cash", "table_cell"), paragraph(percent(investment.get("probability_negative_cash")), "table_number")],
    ]
    table = Table(data, colWidths=[width * 0.45, width * 0.55], repeatRows=1, hAlign="LEFT")
    table.setStyle(_table_style(palette))
    return table


def _callout_table(text, paragraph, width, accent, background, Table, TableStyle):
    table = Table([[paragraph(text, "callout")]], colWidths=[width], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.5, accent),
                ("LINEBEFORE", (0, 0), (0, -1), 3, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def _two_column_lists(risks, opportunities, paragraph, width, palette, Table, TableStyle):
    risk_flow = [paragraph("Risks", "h2")] + _bullet_paragraphs(risks, paragraph)
    opportunity_flow = [paragraph("Opportunities", "h2")] + _bullet_paragraphs(opportunities, paragraph)
    table = Table([[risk_flow, opportunity_flow]], colWidths=[width / 2 - 2, width / 2 - 2], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), colors_tint(palette["danger"])),
                ("BACKGROUND", (1, 0), (1, 0), palette["surface_2"]),
                ("BOX", (0, 0), (-1, -1), 0.5, palette["border"]),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, palette["border"]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def colors_tint(color):
    from reportlab.lib.colors import Color

    return Color(1 - (1 - color.red) * 0.10, 1 - (1 - color.green) * 0.10, 1 - (1 - color.blue) * 0.10)


def _bullet_paragraphs(items, paragraph) -> list[Any]:
    if not items:
        return [paragraph("- None recorded.", "callout")]
    return [paragraph(f"- {item}", "callout") for item in items]
