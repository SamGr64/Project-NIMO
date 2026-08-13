from __future__ import annotations

from dashboard.lib.charts import investment_fan_chart
from dashboard.lib.layout import edit_layout
from dashboard.lib.themes import plotly_layout

METRICS = {
    "monthly_contribution": "Monthly contribution",
    "median_final_value": "Median final value",
    "total_contributed": "Median contributed",
    "negative_cash_probability": "Chance cash falls below zero",
}
WIDGETS = {
    "capacity": "Cash-flow capacity",
    "portfolio_editor": "Portfolio editor",
    "investment_fan": "Investment fan chart",
    "asset_statistics": "Asset statistics",
    "stress_tests": "Stress tests",
}


def render(ctx) -> None:
    import pandas as pd
    import streamlit as st

    if ctx.container is None:
        st.info("Create or select a profile from Data & Setup.")
        return
    st.title("Investing Sandbox")
    st.warning("The bundled market history is synthetic and educational. NIMO is not recommending investments or predicting market prices.")
    service = ctx.container.investing
    layout = edit_layout(st, page_id="investing", layout_service=ctx.container.layouts, available_metrics=METRICS, available_widgets=WIDGETS)
    portfolios = service.portfolios()
    selected_name = st.selectbox("Portfolio", [item["name"] for item in portfolios])
    portfolio = next(item for item in portfolios if item["name"] == selected_name)

    if "portfolio_editor" in layout.get("widgets", []):
        st.subheader("Portfolio and contribution rule")
        weights = pd.DataFrame([{"symbol": key, "weight": value} for key, value in portfolio["allocations"].items()])
        edited = st.data_editor(weights, hide_index=True, use_container_width=True, disabled=["symbol"], key=f"portfolio_{portfolio['id']}")
        rule_type = st.selectbox("Contribution rule", ["fixed", "percent_income", "percent_surplus", "threshold", "goal_aware"], index=["fixed", "percent_income", "percent_surplus", "threshold", "goal_aware"].index(portfolio["contribution_rule"].get("type", "fixed")))
        if rule_type in {"fixed", "goal_aware"}:
            amount = st.number_input("Monthly amount", min_value=0.0, value=float(portfolio["contribution_rule"].get("amount", 100.0)))
            rule = {"type": rule_type, "amount": amount}
            if rule_type == "goal_aware":
                rule["minimum_cash"] = st.number_input("Minimum cash before investing", min_value=0.0, value=float(portfolio["contribution_rule"].get("minimum_cash", 5000.0)))
        elif rule_type in {"percent_income", "percent_surplus"}:
            fraction = st.slider("Fraction", 0.0, 1.0, float(portfolio["contribution_rule"].get("fraction", 0.10)), 0.01)
            rule = {"type": rule_type, "fraction": fraction}
        else:
            threshold = st.number_input("Cash threshold", min_value=0.0, value=float(portfolio["contribution_rule"].get("cash_threshold", 5000.0)))
            fraction = st.slider("Share invested above threshold", 0.0, 1.0, float(portfolio["contribution_rule"].get("fraction", 1.0)), 0.05)
            rule = {"type": "threshold", "cash_threshold": threshold, "fraction": fraction}
        if st.button("Save portfolio settings"):
            service.update_portfolio(portfolio["id"], allocations={row["symbol"]: float(row["weight"]) for row in edited.to_dict(orient="records")}, contribution_rule=rule)
            st.success("Portfolio settings saved.")

    col1, col2, col3 = st.columns(3)
    years = col1.slider("Horizon (years)", 1, 50, 10)
    runs = col2.select_slider("Simulation runs", options=[250, 500, 1000, 3000, 5000, 10000], value=3000)
    stress = col3.selectbox("Stress test", ["None", "market_drop", "income_drop", "unexpected_expense"])
    if st.button("Run investment simulation", type="primary"):
        with st.spinner("Simulating cash flow and portfolio paths..."):
            service.simulate(portfolio["id"], horizon_years=years, runs=runs, stress_name=None if stress == "None" else stress)
        st.success("Simulation complete.")
    latest = service.latest_run()
    if latest:
        rule = latest["portfolio"]["contribution_rule"]
        contribution_label = f"£{rule.get('amount', 0):,.2f}" if rule.get("type") == "fixed" else rule.get("type", "custom")
        values = {
            "monthly_contribution": contribution_label,
            "median_final_value": f"£{latest['final_value']['median']:,.2f}",
            "total_contributed": f"£{latest['total_contributed']['median']:,.2f}",
            "negative_cash_probability": f"{latest['probability_negative_cash']:.1%}",
        }
        selected_metrics = layout.get("headline_metrics", [])
        cols = st.columns(min(4, max(1, len(selected_metrics))))
        for index, metric in enumerate(selected_metrics):
            cols[index % len(cols)].metric(METRICS[metric], values[metric])
    if "capacity" in layout.get("widgets", []):
        overview = ctx.container.analysis.overview()
        st.subheader("Current cash-flow context")
        st.write({"historical_net_cash_flow": overview.net_cash_flow, "savings_rate": overview.savings_rate, "current_balance": overview.total_balance})
    if "investment_fan" in layout.get("widgets", []) and latest:
        st.plotly_chart(investment_fan_chart(latest, plotly_layout(ctx.config.theme(ctx.theme_name))), use_container_width=True)
    if "asset_statistics" in layout.get("widgets", []):
        st.subheader("Educational asset statistics")
        st.dataframe(service.statistics(), use_container_width=True, hide_index=True)
    if "stress_tests" in layout.get("widgets", []):
        st.caption("Stress presets combine market, income or expense shocks with the selected behavioural cash-flow scenario.")
