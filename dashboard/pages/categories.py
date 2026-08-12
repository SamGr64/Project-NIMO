from __future__ import annotations

from dashboard.lib.charts import category_bar
from dashboard.lib.themes import plotly_layout


def render(ctx) -> None:
    import streamlit as st

    if ctx.container is None:
        st.info("Select a user profile first.")
        return
    st.title("Categories")
    if st.button("Re-run automatic categorisation"):
        result = ctx.container.categorisation.auto_categorise()
        st.success(f"Applied {result['user_rule']} user-rule and {result['builtin']} built-in classifications.")
    summary = ctx.container.analysis.categories()
    st.plotly_chart(
        category_bar(summary, plotly_layout(ctx.config.theme(ctx.theme_name))),
        use_container_width=True,
    )
    st.dataframe(summary, use_container_width=True, hide_index=True)

    col_custom, col_export = st.columns(2)
    with col_custom:
        st.subheader("Custom category")
        slug = st.text_input("Slug", key="custom_category_slug")
        label = st.text_input("Label", key="custom_category_label")
        if st.button("Create category", disabled=not slug or not label):
            ctx.container.categorisation.create_custom_category(slug=slug, label=label)
            st.success("Custom category created.")
    with col_export:
        st.subheader("ChatGPT categorisation package")
        st.caption("Exports normalised rows plus the master prompt; it does not send data automatically.")
        if st.button("Build export package"):
            csv_path, prompt_path = ctx.container.categorisation.export_for_llm()
            st.success(f"Created {csv_path.name} and {prompt_path.name} in the user's exports folder.")
        suggestions = st.file_uploader("Import reviewed suggestion CSV", type=["csv"], key="category_suggestion_upload")
        override_builtin = st.checkbox("Allow suggestions to replace built-in categories", key="category_override_builtin")
        if st.button("Import suggestions", disabled=suggestions is None):
            temporary = ctx.container.workspace.cache_dir / suggestions.name
            temporary.write_bytes(suggestions.getbuffer())
            result = ctx.container.categorisation.import_llm_suggestions(temporary, override_builtin=override_builtin)
            st.success(f"Applied {result['applied']} suggestions; skipped {result['skipped']}; invalid {result['invalid']}.")
            st.rerun()
