from __future__ import annotations

from dashboard.lib.charts import cashflow_sankey
from dashboard.lib.themes import plotly_layout


def render(ctx) -> None:
    import streamlit as st

    if ctx.container is None:
        st.info("Select a user profile first.")
        return
    st.title("Cash Flow")
    if st.button("Re-detect internal transfers"):
        result = ctx.container.transfer_detector.detect()
        st.success(f"Matched {result['matched_pairs']} transfer pairs.")
    with st.expander("Confirm or remove a transfer manually"):
        debit_id = st.number_input("Debit transaction id", min_value=1, step=1, key="manual_transfer_debit")
        credit_id = st.number_input("Credit transaction id", min_value=1, step=1, key="manual_transfer_credit")
        if st.button("Confirm pair as internal transfer"):
            group_id = ctx.container.transfer_detector.confirm_pair(int(debit_id), int(credit_id))
            st.success(f"Confirmed transfer group {group_id}.")
            st.rerun()
        group_to_remove = st.text_input("Transfer group id to remove")
        if st.button("Remove transfer match", disabled=not group_to_remove):
            removed = ctx.container.transfer_detector.unmatch_group(group_to_remove)
            st.success("Transfer removed." if removed else "Transfer group not found.")
            st.rerun()

    payload = ctx.container.analysis.cashflow()
    if not payload["links"]:
        st.info("No cash-flow links are available.")
        return
    st.plotly_chart(
        cashflow_sankey(payload, plotly_layout(ctx.config.theme(ctx.theme_name))),
        use_container_width=True,
    )
    st.dataframe(
        [
            {
                "Source": row["source_label"],
                "Target": row["target_label"],
                "Value": row["value"],
                "Type": row["flow_type"],
                "Confidence": row["confidence"],
            }
            for row in payload["links"]
        ],
        use_container_width=True,
        hide_index=True,
    )
