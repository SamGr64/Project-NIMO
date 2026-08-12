from __future__ import annotations

from dashboard.lib.charts import balance_chart
from dashboard.lib.themes import plotly_layout


def render(ctx) -> None:
    import streamlit as st

    if ctx.container is None:
        st.info("Select a user profile first.")
        return
    st.title("Accounts")
    accounts = ctx.container.analysis.accounts()
    if accounts.empty:
        st.info("No accounts have been imported.")
        return
    columns = st.columns(min(3, len(accounts)))
    for index, row in accounts.iterrows():
        columns[index % len(columns)].metric(str(row["account_name"]), f"£{row['balance']:,.2f}", f"£{row['net_movement']:,.2f} movement")
    st.plotly_chart(
        balance_chart(ctx.container.analysis.balances(), plotly_layout(ctx.config.theme(ctx.theme_name))),
        use_container_width=True,
    )
    st.dataframe(accounts, use_container_width=True, hide_index=True)
