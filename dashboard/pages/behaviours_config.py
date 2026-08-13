from __future__ import annotations

from dashboard.lib.layout import edit_layout

METRICS = {
    "archetype_confidence": "Archetype confidence",
    "history_months": "History months",
    "spontaneous_rate": "Spontaneous transaction rate",
    "weekend_share": "Weekend spending share",
}
WIDGETS = {
    "behaviour_table": "Behaviour table",
    "distribution_view": "Distribution explorer",
    "outlier_table": "Outlier table",
    "model_configuration": "Model configuration",
}


def render(ctx) -> None:
    import plotly.express as px
    import streamlit as st

    if ctx.container is None:
        st.info("Create or select a profile from Data & Setup.")
        return
    st.title("User Behaviours & Configuration")
    service = ctx.container.behaviours
    if st.button("Rebuild behavioural map"):
        service.refresh(force=True)
        st.success("Behavioural map rebuilt from canonical transactions only.")
    payload = service.current()
    layout = edit_layout(st, page_id="behaviours", layout_service=ctx.container.layouts, available_metrics=METRICS, available_widgets=WIDGETS)
    archetype = payload.get("archetype", {})
    st.subheader(archetype.get("label", "Insufficient history"))
    st.caption(archetype.get("explanation", ""))
    metric_values = {
        "archetype_confidence": f"{float(archetype.get('confidence', 0)):.1%}",
        "history_months": str(payload.get("metadata", {}).get("history_months", 0)),
        "spontaneous_rate": f"{float(payload.get('global', {}).get('spontaneous_transaction_rate', 0)):.1%}",
        "weekend_share": f"{float(payload.get('global', {}).get('weekend_spend_share', 0)):.1%}",
    }
    selected = layout.get("headline_metrics", [])
    cols = st.columns(min(4, max(1, len(selected))))
    for index, metric in enumerate(selected):
        cols[index % len(cols)].metric(METRICS[metric], metric_values[metric])

    for widget in layout.get("widgets", []):
        if widget == "behaviour_table":
            rows = []
            for category, value in payload.get("categories", {}).items():
                best = value.get("distributional", {}).get("best_fit") or {}
                rows.append({"category": category, "observations": value.get("sample_count"), "cadence": value.get("periodic", {}).get("cadence"), "periodic_score": value.get("periodic", {}).get("score"), "distribution": best.get("family"), "spontaneous_rate": value.get("spontaneous", {}).get("rate")})
            st.subheader("Behaviour map")
            st.dataframe(rows, use_container_width=True, hide_index=True)
        elif widget == "distribution_view":
            categories = list(payload.get("categories", {}))
            if categories:
                category = st.selectbox("Distribution category", categories)
                frame = ctx.container.analysis.transaction_frame()
                selected_frame = frame.loc[(frame["category_slug"].fillna("uncategorised") == category) & (frame["amount"] < 0)].copy()
                selected_frame["spend"] = -selected_frame["amount"]
                col1, col2 = st.columns(2)
                col1.plotly_chart(px.box(selected_frame, y="spend", points="outliers", title=f"{category}: box plot"), use_container_width=True)
                col2.plotly_chart(px.histogram(selected_frame, x="spend", nbins=30, title=f"{category}: amount distribution"), use_container_width=True)
                st.json(payload["categories"][category].get("distributional", {}))
        elif widget == "outlier_table":
            outliers = service.outliers_frame()
            if not outliers.empty:
                transactions = ctx.container.analysis.transaction_frame()[["id", "booking_date", "description_raw", "amount", "category_slug"]]
                st.subheader("Potential spontaneous/outlier transactions")
                st.dataframe(outliers.merge(transactions, left_on="transaction_id", right_on="id", how="left"), use_container_width=True, hide_index=True)
        elif widget == "model_configuration":
            _configuration(ctx, st)


def _configuration(ctx, st) -> None:
    st.subheader("User model configuration")
    st.caption("These optional user-level overrides sit above project defaults. Resetting them restores config/*.yaml behaviour.")
    analysis = ctx.container.behaviours.analysis_config
    forecasting = ctx.container.forecasting.config
    budgeting = ctx.container.planning.config
    investing = ctx.container.investing.config
    with st.form("model_configuration"):
        minimum_observations = st.number_input("Minimum behaviour observations", min_value=3, max_value=100, value=int(analysis.get("behaviour", {}).get("minimum_observations", 6)))
        forecast_runs = st.number_input("Default forecast runs", min_value=100, max_value=50000, value=int(forecasting.get("monte_carlo", {}).get("default_runs", 3000)), step=100)
        inflation = st.number_input("Default annual inflation", min_value=-0.05, max_value=0.30, value=float(forecasting.get("defaults", {}).get("annual_inflation_rate", 0.025)), step=0.005, format="%.3f")
        budget_lookback = st.number_input("Budget lookback months", min_value=1, max_value=60, value=int(budgeting.get("defaults", {}).get("lookback_months", 6)))
        fee = st.number_input("Sandbox annual fee assumption", min_value=0.0, max_value=0.10, value=float(investing.get("defaults", {}).get("annual_fee_rate", 0.0025)), step=0.0005, format="%.4f")
        if st.form_submit_button("Save user overrides"):
            ctx.container.workspace.update_profile({"model_overrides": {"analysis": {"behaviour": {"minimum_observations": int(minimum_observations)}}, "forecasting": {"monte_carlo": {"default_runs": int(forecast_runs)}, "defaults": {"annual_inflation_rate": float(inflation)}}, "budgeting": {"defaults": {"lookback_months": int(budget_lookback)}}, "investing": {"defaults": {"annual_fee_rate": float(fee)}}}})
            st.success("Overrides saved. Reload the dashboard to rebuild services with the new settings.")
