from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from dashboard.lib.charts.common import apply_layout


def forecast_fan_chart(summary, layout):
    rows = summary.get("months", [])
    frame = pd.DataFrame(rows)
    fig = go.Figure()
    if not frame.empty:
        fig.add_trace(go.Scatter(x=frame["month"], y=frame["balance_p90"], line={"width": 0}, showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=frame["month"], y=frame["balance_p10"], fill="tonexty", line={"width": 0}, name="80% range"))
        fig.add_trace(go.Scatter(x=frame["month"], y=frame["balance_p75"], line={"width": 0}, showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=frame["month"], y=frame["balance_p25"], fill="tonexty", line={"width": 0}, name="50% range"))
        fig.add_trace(go.Scatter(x=frame["month"], y=frame["balance_median"], mode="lines+markers", name="Median"))
    fig.update_layout(title="Balance forecast", yaxis_title="Balance", xaxis_title="Month")
    return apply_layout(fig, layout)


def investment_fan_chart(summary, layout):
    frame = pd.DataFrame(summary.get("months", []))
    fig = go.Figure()
    if not frame.empty:
        fig.add_trace(go.Scatter(x=frame["month"], y=frame["portfolio_p90"], line={"width": 0}, showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=frame["month"], y=frame["portfolio_p10"], fill="tonexty", line={"width": 0}, name="80% range"))
        fig.add_trace(go.Scatter(x=frame["month"], y=frame["portfolio_median"], mode="lines", name="Portfolio median"))
        fig.add_trace(go.Scatter(x=frame["month"], y=frame["cash_median"], mode="lines", name="Cash median"))
    fig.update_layout(title="Investment and cash simulation", yaxis_title="Value", xaxis_title="Month")
    return apply_layout(fig, layout)


def budget_probability_chart(rows, layout):
    frame = pd.DataFrame(rows)
    fig = go.Figure()
    if not frame.empty:
        fig.add_bar(x=frame["label"], y=frame["probability_within_budget"], name="Probability")
    fig.update_layout(title="Probability of remaining within budget", yaxis={"tickformat": ".0%", "range": [0, 1]}, xaxis_title="Category")
    return apply_layout(fig, layout)
