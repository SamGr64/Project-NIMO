from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from nimo.storage.models import AuditEvent


def record_audit(
    session: Session,
    event_type: str,
    *,
    actor: str = "local_user",
    object_type: str | None = None,
    object_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        event_type=event_type,
        actor=actor,
        object_type=object_type,
        object_id=object_id,
        details_json=json.dumps(details or {}, sort_keys=True, default=str),
    )
    session.add(event)
    return event
