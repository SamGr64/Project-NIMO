from __future__ import annotations

import hashlib
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from nimo.storage.models import Transaction


def source_data_version(session: Session) -> str:
    """Return a cheap, deterministic fingerprint for active canonical data."""
    row = session.execute(
        select(
            func.count(Transaction.id),
            func.max(Transaction.id),
            func.max(Transaction.imported_at),
            func.sum(Transaction.amount),
            func.sum(func.coalesce(Transaction.category_id, 0)),
        ).where(Transaction.is_active.is_(True))
    ).one()
    count, max_id, imported_at, amount_sum, category_sum = row
    timestamp = imported_at.isoformat() if isinstance(imported_at, datetime) else str(imported_at or "")
    payload = f"{count or 0}|{max_id or 0}|{timestamp}|{float(amount_sum or 0):.6f}|{int(category_sum or 0)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
