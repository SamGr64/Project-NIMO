from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from nimo.storage.models import DashboardLayout


class LayoutRepository:
    def get(self, session: Session, page_id: str) -> dict[str, Any] | None:
        row = session.scalar(select(DashboardLayout).where(DashboardLayout.page_id == page_id))
        return None if row is None else json.loads(row.layout_json)

    def save(self, session: Session, page_id: str, layout: dict[str, Any]) -> None:
        row = session.scalar(select(DashboardLayout).where(DashboardLayout.page_id == page_id))
        encoded = json.dumps(layout, sort_keys=True)
        if row is None:
            session.add(DashboardLayout(page_id=page_id, layout_json=encoded))
        else:
            row.layout_json = encoded
