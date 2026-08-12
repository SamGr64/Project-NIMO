from __future__ import annotations

from datetime import date


def date_filter(st, frame, *, key: str) -> tuple[date | None, date | None]:
    if frame.empty:
        return None, None
    minimum = frame["booking_date"].min().date()
    maximum = frame["booking_date"].max().date()
    selected = st.date_input("Date range", value=(minimum, maximum), min_value=minimum, max_value=maximum, key=key)
    if isinstance(selected, tuple) and len(selected) == 2:
        return selected[0], selected[1]
    return minimum, maximum
