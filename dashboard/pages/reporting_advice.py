from __future__ import annotations

from pathlib import Path

from dashboard.lib.layout import edit_layout

METRICS = {"report_count": "Reports generated", "last_provider": "Latest narrative provider"}
WIDGETS = {"report_builder": "Report builder", "report_history": "Report history", "narrative_preview": "Narrative preview"}


def render(ctx) -> None:
    import streamlit as st

    if ctx.container is None:
        st.info("Create or select a profile from Data & Setup.")
        return
    st.title("Reporting & Advice")
    layout = edit_layout(st, page_id="reporting", layout_service=ctx.container.layouts, available_metrics=METRICS, available_widgets=WIDGETS)
    service = ctx.container.reporting
    history = service.list()
    values = {"report_count": str(len(history)), "last_provider": history[0]["provider"] if history else "—"}
    selected = layout.get("headline_metrics", [])
    cols = st.columns(min(4, max(1, len(selected))))
    for index, metric in enumerate(selected):
        cols[index % len(cols)].metric(METRICS[metric], values[metric])

    if "report_builder" in layout.get("widgets", []):
        st.subheader("Build report")
        formats = st.multiselect("Formats", ["html", "md", "pdf", "docx"], default=["html"])
        use_llm = st.checkbox("Use OpenAI for structured narrative synthesis", value=False, help="NIMO sends only the structured evidence package; raw descriptions are excluded by default.")
        include_forecast = st.checkbox("Include forecast", value=True)
        include_budget = st.checkbox("Include budget and goals", value=True)
        include_investing = st.checkbox("Include latest investing simulation", value=True)
        if st.button("Generate report", type="primary", disabled=not formats):
            try:
                with st.spinner("Building evidence, narrative and report files..."):
                    result = service.build(formats=formats, use_llm=use_llm, include_forecast=include_forecast, include_budget=include_budget, include_investing=include_investing)
                st.session_state["latest_report_result"] = result
                st.success("Report generated.")
            except Exception as exc:
                st.error(str(exc))
    if "narrative_preview" in layout.get("widgets", []) and "latest_report_result" in st.session_state:
        result = st.session_state["latest_report_result"]
        st.subheader("Narrative preview")
        st.json(result["narrative"])
        for format_name, path in result["outputs"].items():
            file_path = ctx.container.workspace.resolve_stored_path(path)
            if file_path.exists():
                st.download_button(f"Download {format_name.upper()}", file_path.read_bytes(), file_name=file_path.name)
    if "report_history" in layout.get("widgets", []):
        st.subheader("Report history")
        st.dataframe(history, use_container_width=True, hide_index=True)
