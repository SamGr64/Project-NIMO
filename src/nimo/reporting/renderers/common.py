from __future__ import annotations

import html
from typing import Any, Iterable


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def money(value: Any) -> str:
    if value is None:
        return "-"
    try:
        return f"£{float(value):,.2f}"
    except (TypeError, ValueError):
        return "-"


def percent(value: Any, *, digits: int = 1) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "-"


def escape(value: Any) -> str:
    return html.escape(str(value))


def safe_text(value: Any) -> str:
    """Return text that renders reliably with ReportLab's standard Type 1 fonts."""

    text = str(value)
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2022": "-",
        "\u2192": "->",
        "\u00a0": " ",
        "\u2026": "...",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text.encode("cp1252", errors="replace").decode("cp1252")


def forecast_svg(rows: list[dict[str, Any]], *, width: int = 760, height: int = 250) -> str:
    """Build an accessible, dependency-free SVG fan chart for HTML reports."""

    if not rows:
        return ""
    medians = [as_float(row.get("balance_median")) for row in rows]
    lows = [as_float(row.get("balance_p10", row.get("balance_p05"))) for row in rows]
    highs = [as_float(row.get("balance_p90", row.get("balance_p95"))) for row in rows]
    values = lows + highs + medians
    minimum, maximum = min(values), max(values)
    padding = max(1.0, (maximum - minimum) * 0.08)
    minimum -= padding
    maximum += padding
    span = max(1e-9, maximum - minimum)
    left, right, top, bottom = 66.0, width - 18.0, 20.0, height - 40.0

    def coordinate(index: int, value: float) -> tuple[float, float]:
        x = left + index * (right - left) / max(1, len(rows) - 1)
        y = bottom - (value - minimum) * (bottom - top) / span
        return x, y

    high_points = [coordinate(index, value) for index, value in enumerate(highs)]
    low_points = [coordinate(index, value) for index, value in enumerate(lows)]
    median_points = [coordinate(index, value) for index, value in enumerate(medians)]
    band = " ".join(f"{x:.1f},{y:.1f}" for x, y in high_points + list(reversed(low_points)))
    median = " ".join(f"{x:.1f},{y:.1f}" for x, y in median_points)
    grid = []
    for index in range(5):
        ratio = index / 4
        y = top + ratio * (bottom - top)
        value = maximum - ratio * span
        grid.append(
            f'<line x1="{left:.1f}" y1="{y:.1f}" x2="{right:.1f}" y2="{y:.1f}" '
            'stroke="#dce3e8" stroke-width="1" />'
            f'<text x="{left - 8:.1f}" y="{y + 4:.1f}" text-anchor="end" font-size="11" '
            f'fill="#5f6b75">£{value:,.0f}</text>'
        )
    labels = []
    label_indexes = sorted({0, len(rows) // 2, len(rows) - 1})
    for index in label_indexes:
        x, _ = coordinate(index, medians[index])
        label = escape(rows[index].get("month", str(index + 1)))
        labels.append(
            f'<text x="{x:.1f}" y="{height - 12:.1f}" text-anchor="middle" font-size="11" '
            f'fill="#5f6b75">{label}</text>'
        )
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" '
        'aria-label="Forecast median balance with 10th to 90th percentile interval">'
        '<rect width="100%" height="100%" rx="10" fill="#ffffff" />'
        + "".join(grid)
        + f'<polygon points="{band}" fill="#31a247" fill-opacity="0.16" stroke="none" />'
        + f'<polyline fill="none" stroke="#237a36" stroke-width="3" points="{median}" />'
        + "".join(labels)
        + '<line x1="570" y1="18" x2="600" y2="18" stroke="#237a36" stroke-width="3" />'
        + '<text x="607" y="22" font-size="11" fill="#41505c">Median</text>'
        + '<rect x="665" y="10" width="20" height="14" fill="#31a247" fill-opacity="0.16" />'
        + '<text x="691" y="22" font-size="11" fill="#41505c">10%-90%</text>'
        + "</svg>"
    )


def rows_as_markdown(headers: list[str], rows: Iterable[Iterable[Any]]) -> list[str]:
    materialised = [[str(cell) for cell in row] for row in rows]
    if not materialised:
        return ["_No data available._"]
    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    output.extend("| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |" for row in materialised)
    return output
