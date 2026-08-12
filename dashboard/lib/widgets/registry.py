from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True, slots=True)
class WidgetDefinition:
    id: str
    title: str
    pages: tuple[str, ...]
    render: Callable


class WidgetRegistry:
    def __init__(self) -> None:
        self._widgets: dict[str, WidgetDefinition] = {}

    def register(self, definition: WidgetDefinition) -> None:
        if definition.id in self._widgets:
            raise KeyError(f"Widget already registered: {definition.id}")
        self._widgets[definition.id] = definition

    def get(self, widget_id: str) -> WidgetDefinition:
        return self._widgets[widget_id]

    def for_page(self, page_id: str) -> list[WidgetDefinition]:
        return [widget for widget in self._widgets.values() if page_id in widget.pages]
