from __future__ import annotations

from datetime import date

from dashboard.lib.charts import forecast_fan_chart
from dashboard.lib.layout import edit_layout
from dashboard.lib.themes import plotly_layout

METRICS = {
    "median_final_balance": "Median final balance",
    "p10_final_balance": "10th percentile",
    "p90_final_balance": "90th percentile",
    "negative_balance_probability": "Chance balance falls below zero",
    "expected_net_cashflow": "Expected net cash flow",
}
WIDGETS = {
    "forecast_fan": "Forecast fan chart",
    "assumption_table": "Assumption table",
    "scenario_controls": "Scenario controls",
    "event_table": "Planned events",
    "backtest": "Backtest diagnostics",
}


def render(ctx) -> None:
    import streamlit as st

    if ctx.container is None:
        st.info("Create or select a profile from Data & Setup.")
        return
    st.title("Forecasting & Scenarios")
    service = ctx.container.forecasting
    profile_payload = service.profile()
    profile = profile_payload["profile"]
    scenarios = service.scenarios()
    scenario_names = [item["name"] for item in scenarios]
    selected = st.selectbox("Scenario", scenario_names, key="forecast_scenario")
    selected_payload = next(item for item in scenarios if item["name"] == selected)

    with st.expander("Create or edit a scenario", expanded=False):
        with st.form("new_scenario_form"):
            name = st.text_input("New scenario name")
            description = st.text_input("Description")
            if st.form_submit_button("Create scenario") and name:
                service.create_scenario(name, description=description, copy_from=selected)
                st.success("Scenario created. Refresh or rerun the page to select it.")
        assumption_paths = ["income.monthly_mean", "income.monthly_std", "global_assumptions.annual_inflation_rate"]
        assumption_paths.extend(f"categories.{slug}.monthly_mean" for slug in profile.get("categories", {}))
        path = st.selectbox("Editable assumption", assumption_paths)
        current = _get(profile, path)
        value = st.number_input("Override value", value=float(current), key="forecast_override_value")
        if st.button("Save override"):
            service.set_override(selected, path, value)
            st.success("Override saved. Historical inference is unchanged.")
        if selected_payload.get("overrides"):
            st.json(selected_payload["overrides"])

        st.markdown("#### Planned event")
        with st.form("forecast_event_form"):
            event_name = st.text_input("Event name", value="Planned expense")
            event_date = st.date_input("Date", value=date.today())
            event_amount = st.number_input("Amount (negative for a cost)", value=-500.0)
            event_uncertainty = st.number_input("Uncertainty (+/-)", min_value=0.0, value=0.0)
            event_probability = st.slider("Probability", 0.0, 1.0, 1.0, 0.05)
            repeat = st.number_input("Repeat every N months (0 = once)", min_value=0, value=0, step=1)
            if st.form_submit_button("Add event"):
                service.add_event(selected, name=event_name, event_date=event_date, amount=event_amount, uncertainty=event_uncertainty, probability=event_probability, repeat_months=int(repeat))
                st.success("Event added.")

    col_a, col_b, col_c = st.columns(3)
    horizon = col_a.slider("Forecast months", 1, 120, 12)
    runs = col_b.select_slider("Monte Carlo runs", options=[250, 500, 1000, 3000, 5000, 10000], value=3000)
    threshold = col_c.number_input("Final balance threshold", value=0.0)
    if st.button("Run forecast", type="primary"):
        with st.spinner("Running the selected scenario..."):
            service.run(scenario=selected, horizon_months=horizon, runs=runs, threshold=threshold)
        st.success("Forecast complete.")
    latest = service.latest_run(scenario=selected)

    layout = edit_layout(st, page_id="forecasting", layout_service=ctx.container.layouts, available_metrics=METRICS, available_widgets=WIDGETS)
    if latest:
        final = latest["final_balance"]
        metric_values = {
            "median_final_balance": f"£{final['median']:,.2f}",
            "p10_final_balance": f"£{final['p10']:,.2f}",
            "p90_final_balance": f"£{final['p90']:,.2f}",
            "negative_balance_probability": f"{latest['probability_negative_balance']:.1%}",
            "expected_net_cashflow": f"£{latest['expected_net_cashflow']:,.2f}",
        }
        cols = st.columns(min(4, max(1, len(layout.get("headline_metrics", [])))))
        for index, metric_id in enumerate(layout.get("headline_metrics", [])):
            cols[index % len(cols)].metric(METRICS[metric_id], metric_values[metric_id])
    else:
        st.info("Run a forecast to populate scenario results.")

    theme = plotly_layout(ctx.config.theme(ctx.theme_name))
    for widget in layout.get("widgets", []):
        if widget == "forecast_fan" and latest:
            st.plotly_chart(forecast_fan_chart(latest, theme), use_container_width=True)
        elif widget == "assumption_table":
            rows = [{"assumption": "Income", **{key: profile["income"].get(key) for key in ["monthly_mean", "monthly_std", "monthly_trend", "confidence", "source"]}}]
            rows.extend({"assumption": process["label"], **{key: process.get(key) for key in ["monthly_mean", "monthly_std", "monthly_trend", "confidence", "source"]}} for process in profile.get("categories", {}).values())
            st.subheader("Default assumptions")
            st.dataframe(rows, use_container_width=True, hide_index=True)
        elif widget == "scenario_controls":
            st.subheader("Scenario provenance")
            st.json({"scenario": selected, "overrides": selected_payload.get("overrides", {}), "source_data_version": profile_payload["source_data_version"]})
        elif widget == "event_table":
            st.subheader("Planned events")
            st.dataframe(selected_payload.get("events", []), use_container_width=True, hide_index=True)
        elif widget == "backtest":
            st.subheader("Historical calibration")
            if st.button("Run backtest"):
                st.session_state["nimo_backtest"] = service.backtest()
            if "nimo_backtest" in st.session_state:
                result = st.session_state["nimo_backtest"]
                st.write(f"50% interval coverage: {result.get('coverage_50', 0):.1%}; 90% interval coverage: {result.get('coverage_90', 0):.1%}")
                st.dataframe(result.get("periods", []), use_container_width=True, hide_index=True)


def _get(payload, path):
    value = payload
    for part in path.split("."):
        value = value[part]
    return value
