from __future__ import annotations

from copy import deepcopy
from typing import Any


def edit_layout(st, *, page_id: str, layout_service, available_metrics: dict[str, str], available_widgets: dict[str, str]) -> dict[str, Any]:
    layout = deepcopy(layout_service.get(page_id))
    with st.expander("Customise page", expanded=False):
        metrics = st.multiselect(
            "Headline metrics",
            options=list(available_metrics),
            default=[value for value in layout.get("headline_metrics", []) if value in available_metrics],
            format_func=lambda value: available_metrics[value],
            key=f"{page_id}_metric_editor",
        )
        widgets = st.multiselect(
            "Widgets",
            options=list(available_widgets),
            default=[value for value in layout.get("widgets", []) if value in available_widgets],
            format_func=lambda value: available_widgets[value],
            key=f"{page_id}_widget_editor",
        )
        order = st.multiselect(
            "Widget order",
            options=widgets,
            default=[value for value in layout.get("widgets", []) if value in widgets] + [value for value in widgets if value not in layout.get("widgets", [])],
            format_func=lambda value: available_widgets[value],
            key=f"{page_id}_widget_order",
        )
        col_save, col_reset = st.columns(2)
        if col_save.button("Save layout", key=f"{page_id}_save_layout"):
            layout = {"headline_metrics": metrics, "widgets": order}
            layout_service.save(page_id, layout)
            st.success("Layout saved.")
        if col_reset.button("Restore default", key=f"{page_id}_reset_layout"):
            layout = layout_service.reset(page_id)
            st.success("Default restored.")
    return layout_service.get(page_id)
