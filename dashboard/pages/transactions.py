from __future__ import annotations


def render(ctx) -> None:
    import streamlit as st

    if ctx.container is None:
        st.info("Select a user profile first.")
        return
    st.title("Transactions")
    frame = ctx.container.analysis.transaction_frame().sort_values(["booking_date", "id"], ascending=False)
    search = st.text_input("Search descriptions")
    account_options = ["All", *sorted(frame["account_name"].dropna().unique())] if not frame.empty else ["All"]
    account = st.selectbox("Account", account_options)
    show_uncategorised = st.checkbox("Only uncategorised")
    if search:
        frame = frame.loc[frame["description_raw"].str.contains(search, case=False, na=False)]
    if account != "All":
        frame = frame.loc[frame["account_name"] == account]
    if show_uncategorised:
        frame = frame.loc[frame["category_id"].isna()]
    st.dataframe(
        frame[["id", "booking_date", "account_name", "description_raw", "amount", "category_label", "category_confidence", "transfer_group_id"]],
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Assign category manually"):
        transaction_id = st.number_input("Transaction id", min_value=1, step=1)
        categories = ctx.container.categorisation.list_categories()
        category_slug = st.selectbox("Category", [item["slug"] for item in categories])
        if st.button("Assign category"):
            count = ctx.container.categorisation.assign_manual([int(transaction_id)], category_slug)
            st.success(f"Updated {count} transaction.")
            st.rerun()
