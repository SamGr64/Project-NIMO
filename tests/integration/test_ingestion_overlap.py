from __future__ import annotations

import pandas as pd


def _write(path, rows):
    pd.DataFrame(rows).to_csv(path, index=False)


def test_newest_date_coverage_supersedes_old_rows_without_row_deduplication(container, tmp_path) -> None:
    old_path = tmp_path / "old.csv"
    new_path = tmp_path / "new.csv"
    shared = {"bank_name": "Test Bank", "account_number": "12345678", "account_name": "Current"}
    _write(
        old_path,
        [
            {**shared, "date": "2026-01-01", "description": "BUS", "amount": -2.0},
            {**shared, "date": "2026-01-01", "description": "BUS", "amount": -2.0},
            {**shared, "date": "2026-01-02", "description": "SALARY OLD", "amount": 1000.0},
            {**shared, "date": "2026-01-03", "description": "OLD GROCERIES", "amount": -40.0},
        ],
    )
    _write(
        new_path,
        [
            {**shared, "date": "2026-01-02", "description": "SALARY UPDATED", "amount": 1020.0},
            {**shared, "date": "2026-01-04", "description": "BUS", "amount": -2.0},
            {**shared, "date": "2026-01-04", "description": "BUS", "amount": -2.0},
        ],
    )

    first = container.ingestion.import_csv(old_path)
    second = container.ingestion.import_csv(new_path)
    frame = container.analysis.transaction_frame()

    assert first.imported_rows == 4
    assert second.superseded_rows == 2
    assert len(frame) == 5
    assert len(frame.loc[(frame["booking_date"].dt.date.astype(str) == "2026-01-01") & (frame["description_raw"] == "BUS")]) == 2
    assert len(frame.loc[(frame["booking_date"].dt.date.astype(str) == "2026-01-04") & (frame["description_raw"] == "BUS")]) == 2
    assert "OLD GROCERIES" not in set(frame["description_raw"])
    assert "SALARY UPDATED" in set(frame["description_raw"])


def test_exact_source_file_is_not_imported_twice(container, tmp_path) -> None:
    path = tmp_path / "one.csv"
    _write(path, [{"date": "2026-01-01", "description": "BUS", "amount": -2.0}])
    first = container.ingestion.import_csv(path, account_name="Current")
    second = container.ingestion.import_csv(path, account_name="Current")
    assert first.imported_rows == 1
    assert second.duplicate_file is True
    assert container.analysis.overview().transaction_count == 1
