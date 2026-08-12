from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go

from dashboard.lib.charts.common import apply_layout


def balance_chart(frame, layout):
    fig = px.area(frame, x="booking_date", y="balance", color="account_name", title="Balance over time")
    return apply_layout(fig, layout)


def monthly_chart(frame, layout):
    fig = go.Figure()
    fig.add_bar(x=frame["month"], y=frame["spend"], name="Spend")
    fig.add_scatter(x=frame["month"], y=frame["income"], name="Income", mode="lines+markers")
    fig.update_layout(title="Monthly income and spending")
    return apply_layout(fig, layout)


def category_bar(frame, layout):
    work = frame.loc[frame["spend"] > 0].sort_values("spend")
    fig = px.bar(work, x="spend", y="category", orientation="h", title="Spending by category")
    return apply_layout(fig, layout)


def account_pie(frame, layout):
    fig = px.pie(frame, names="account_name", values="balance", title="Account composition")
    return apply_layout(fig, layout)


def cashflow_sankey(payload, layout):
    links = payload["links"]
    fig = go.Figure(
        go.Sankey(
            node={"label": payload["nodes"]},
            link={
                "source": [row["source"] for row in links],
                "target": [row["target"] for row in links],
                "value": [row["value"] for row in links],
                "label": [row["flow_type"] for row in links],
            },
        )
    )
    fig.update_layout(title="Cash-flow schematic")
    return apply_layout(fig, layout)
