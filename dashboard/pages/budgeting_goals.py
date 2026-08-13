from __future__ import annotations

from datetime import date, timedelta

from dashboard.lib.charts import budget_probability_chart
from dashboard.lib.layout import edit_layout
from dashboard.lib.themes import plotly_layout

METRICS = {
    "total_budget": "Total monthly budget",
    "forecast_spend": "Forecast monthly spend",
    "active_goals": "Active goals",
    "selected_goal_probability": "Selected goal probability",
}
WIDGETS = {
    "budget_table": "Budget table",
    "budget_probability": "Budget probability chart",
    "goal_cards": "Goal cards",
    "intervention": "Intervention simulator",
}


def render(ctx) -> None:
    import pandas as pd
    import streamlit as st

    if ctx.container is None:
        st.info("Create or select a profile from Data & Setup.")
        return
    st.title("Budgeting & Goals")
    planning = ctx.container.planning
    layout = edit_layout(st, page_id="budgeting_goals", layout_service=ctx.container.layouts, available_metrics=METRICS, available_widgets=WIDGETS)
    budget_tab, goal_tab = st.tabs(["Budget", "Goals"])

    with budget_tab:
        budgets = planning.budgets()
        selected_name = st.selectbox("Budget", [item["name"] for item in budgets])
        selected = next(item for item in budgets if item["name"] == selected_name)
        col1, col2 = st.columns(2)
        if col1.button("Refresh inferred baseline"):
            planning.ensure_default_budget(force=True)
            st.success("Baseline refreshed.")
        with col2.expander("Create a custom budget"):
            new_name = st.text_input("Budget name")
            if st.button("Create budget") and new_name:
                planning.create_budget(new_name)
                st.success("Budget created.")
        editor_rows = pd.DataFrame(selected["lines"])[["category_slug", "label", "amount", "is_essential", "source"]]
        edited = st.data_editor(editor_rows, use_container_width=True, hide_index=True, disabled=["category_slug", "source"], key=f"budget_editor_{selected['id']}")
        if st.button("Save budget lines"):
            for row in edited.to_dict(orient="records"):
                planning.set_line(selected["id"], row["category_slug"], float(row["amount"]), label=row["label"], essential=bool(row["is_essential"]))
            st.success("Budget saved.")
        evaluation = planning.evaluate(selected["id"], runs=1000)
        metric_values = {
            "total_budget": f"£{evaluation['total_budget']:,.2f}",
            "forecast_spend": f"£{evaluation['forecast_total_spend_median']:,.2f}",
            "active_goals": f"{len(planning.goals())}",
            "selected_goal_probability": "—",
        }
        _metrics(st, layout, metric_values)
        if "budget_table" in layout.get("widgets", []):
            st.dataframe(evaluation["lines"], use_container_width=True, hide_index=True)
        if "budget_probability" in layout.get("widgets", []):
            st.plotly_chart(budget_probability_chart(evaluation["lines"], plotly_layout(ctx.config.theme(ctx.theme_name))), use_container_width=True)

    with goal_tab:
        with st.expander("Add a goal", expanded=False):
            with st.form("add_goal"):
                name = st.text_input("Goal name")
                target = st.number_input("Target amount", min_value=1.0, value=5000.0)
                current = st.number_input("Current amount", min_value=0.0, value=0.0)
                target_date = st.date_input("Target date", value=date.today() + timedelta(days=730))
                monthly = st.number_input("Fixed monthly contribution", min_value=0.0, value=200.0)
                surplus = st.slider("Additional share of positive monthly surplus", 0.0, 1.0, 0.0, 0.05)
                priority = st.slider("Priority", 1, 5, 3)
                if st.form_submit_button("Add goal") and name:
                    planning.add_goal(name=name, target_amount=target, current_amount=current, target_date=target_date, monthly_contribution=monthly, surplus_allocation_fraction=surplus, priority=priority)
                    st.success("Goal added.")
        goals = planning.goals()
        if not goals:
            st.info("Add a goal to simulate likely completion.")
            return
        goal_name = st.selectbox("Goal to inspect", [item["name"] for item in goals])
        selected_goal = next(item for item in goals if item["name"] == goal_name)
        result = planning.simulate_goal(selected_goal["id"], runs=1000)
        st.metric("Probability achieved", f"{result['probability_achieved']:.1%}")
        st.metric("Median value at target date", f"£{result['median_final_amount']:,.2f}")
        st.write(f"Median completion month: **{result['completion_month_median'] or 'not reached in most paths'}**")
        if "goal_cards" in layout.get("widgets", []):
            st.dataframe(goals, use_container_width=True, hide_index=True)
        if "intervention" in layout.get("widgets", []):
            st.subheader("Test a spending intervention")
            categories = list(ctx.container.forecasting.profile()["profile"].get("categories", {}))
            category = st.selectbox("Category", categories)
            reduction = st.slider("Reduction", 0, 100, 10, 5)
            if st.button("Simulate intervention"):
                comparison = planning.intervention(selected_goal["id"], category_slug=category, reduction_fraction=reduction / 100, runs=1000)
                st.json(comparison)


def _metrics(st, layout, values):
    selected = layout.get("headline_metrics", [])
    if not selected:
        return
    cols = st.columns(min(4, len(selected)))
    for index, key in enumerate(selected):
        cols[index % len(cols)].metric(METRICS[key], values.get(key, "—"))
