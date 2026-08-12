from __future__ import annotations

from dashboard.lib.charts import account_pie, balance_chart, monthly_chart
from dashboard.lib.layout import edit_layout
from dashboard.lib.themes import plotly_layout


METRICS = {
    "total_balance": "Total balance",
    "current_month_spend": "Current month spend",
    "net_cash_flow": "Net cash flow",
    "savings_rate": "Savings rate",
    "weighted_monthly_spend": "Typical monthly spend",
    "projected_month_end_spend": "Projected month end",
    "yearly_spend": "Spend this year",
    "uncategorised_count": "Uncategorised transactions",
}
WIDGETS = {
    "balance_history": "Balance history",
    "monthly_spend": "Monthly income and spend",
    "account_composition": "Account composition",
    "recent_transactions": "Recent transactions",
}


def render(ctx) -> None:
    import streamlit as st

    if ctx.container is None:
        st.info("Create or select a profile from Data & Setup.")
        return
    st.title("Overview")
    layout = edit_layout(
        st,
        page_id="overview",
        layout_service=ctx.container.layouts,
        available_metrics=METRICS,
        available_widgets=WIDGETS,
    )
    metrics = ctx.container.analysis.overview()
    metric_values = {
        "total_balance": f"£{metrics.total_balance:,.2f}",
        "current_month_spend": f"£{metrics.current_month_spend:,.2f}",
        "net_cash_flow": f"£{metrics.net_cash_flow:,.2f}",
        "savings_rate": "—" if metrics.savings_rate is None else f"{metrics.savings_rate:.1%}",
        "weighted_monthly_spend": "—" if metrics.weighted_monthly_spend is None else f"£{metrics.weighted_monthly_spend:,.2f}",
        "projected_month_end_spend": "—" if metrics.projected_month_end_spend is None else f"£{metrics.projected_month_end_spend:,.2f}",
        "yearly_spend": f"£{metrics.yearly_spend:,.2f}",
        "uncategorised_count": f"{metrics.uncategorised_count:,}",
    }
    selected_metrics = layout.get("headline_metrics", [])
    if selected_metrics:
        columns = st.columns(min(4, len(selected_metrics)))
        for index, metric_id in enumerate(selected_metrics):
            columns[index % len(columns)].metric(METRICS[metric_id], metric_values[metric_id])

    theme = ctx.config.theme(ctx.theme_name)
    chart_layout = plotly_layout(theme)
    for widget in layout.get("widgets", []):
        if widget == "balance_history":
            st.plotly_chart(
                balance_chart(ctx.container.analysis.balances(), chart_layout),
                use_container_width=True,
            )
        elif widget == "monthly_spend":
            st.plotly_chart(
                monthly_chart(ctx.container.analysis.monthly(), chart_layout),
                use_container_width=True,
            )
        elif widget == "account_composition":
            accounts = ctx.container.analysis.accounts()
            if not accounts.empty:
                st.plotly_chart(account_pie(accounts, chart_layout), use_container_width=True)
        elif widget == "recent_transactions":
            frame = ctx.container.analysis.transaction_frame().sort_values(["booking_date", "id"], ascending=False).head(12)
            st.dataframe(
                frame[["booking_date", "account_name", "description_raw", "category_label", "amount"]],
                use_container_width=True,
                hide_index=True,
            )
