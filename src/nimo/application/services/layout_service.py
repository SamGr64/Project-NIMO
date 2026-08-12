from __future__ import annotations

from copy import deepcopy
from typing import Any

from nimo.storage.database import Database
from nimo.storage.repositories import LayoutRepository


class LayoutService:
    def __init__(self, *, database: Database, default_layouts: dict[str, Any]) -> None:
        self.database = database
        self.default_layouts = default_layouts.get("pages", {})
        self.layouts = LayoutRepository()

    def get(self, page_id: str) -> dict[str, Any]:
        with self.database.session() as session:
            saved = self.layouts.get(session, page_id)
        if saved is not None:
            return saved
        return deepcopy(self.default_layouts.get(page_id, {"headline_metrics": [], "widgets": []}))

    def save(self, page_id: str, layout: dict[str, Any]) -> None:
        with self.database.session() as session:
            self.layouts.save(session, page_id, layout)

    def reset(self, page_id: str) -> dict[str, Any]:
        default = deepcopy(self.default_layouts.get(page_id, {"headline_metrics": [], "widgets": []}))
        self.save(page_id, default)
        return default
