from __future__ import annotations

import pandas as pd


def test_manual_category_survives_automatic_refresh(container, tmp_path) -> None:
    path = tmp_path / "statement.csv"
    pd.DataFrame(
        [
            {"date": "2026-01-01", "description": "TESCO SUPERMARKET", "amount": -45.0},
            {"date": "2026-01-02", "description": "LOCAL CAFE", "amount": -8.0},
        ]
    ).to_csv(path, index=False)
    container.ingestion.import_csv(path, account_name="Current")
    frame = container.analysis.transaction_frame()
    cafe_id = int(frame.loc[frame["description_raw"] == "LOCAL CAFE", "id"].iloc[0])
    container.categorisation.create_custom_category(slug="treats", label="Treats")
    container.categorisation.assign_manual([cafe_id], "treats")
    container.categorisation.auto_categorise()
    refreshed = container.analysis.transaction_frame()
    cafe = refreshed.loc[refreshed["id"] == cafe_id].iloc[0]
    assert cafe["category_slug"] == "treats"
    assert cafe["category_source"] == "manual"


def test_reviewed_llm_import_respects_category_precedence(container, tmp_path) -> None:
    statement = tmp_path / "statement_for_llm.csv"
    pd.DataFrame(
        [
            {"date": "2026-02-01", "description": "MYSTERY PURCHASE", "amount": -12.0},
            {"date": "2026-02-02", "description": "TESCO SUPERMARKET", "amount": -30.0},
            {"date": "2026-02-03", "description": "LOCAL CLUB", "amount": -18.0},
        ]
    ).to_csv(statement, index=False)
    container.ingestion.import_csv(statement, account_name="Current")
    frame = container.analysis.transaction_frame()
    ids = {row.description_raw: int(row.id) for row in frame.itertuples()}

    container.categorisation.create_custom_category(slug="hobbies", label="Hobbies")
    container.categorisation.assign_manual([ids["LOCAL CLUB"]], "hobbies")

    suggestions = tmp_path / "suggestions.csv"
    pd.DataFrame(
        [
            {"transaction_id": ids["MYSTERY PURCHASE"], "category_slug": "hobbies", "confidence": 0.72},
            {"transaction_id": ids["TESCO SUPERMARKET"], "category_slug": "hobbies", "confidence": 0.80},
            {"transaction_id": ids["LOCAL CLUB"], "category_slug": "groceries", "confidence": 0.99},
        ]
    ).to_csv(suggestions, index=False)

    result = container.categorisation.import_llm_suggestions(suggestions)
    assert result == {"applied": 1, "skipped": 2, "invalid": 0}

    refreshed = container.analysis.transaction_frame().set_index("description_raw")
    assert refreshed.loc["MYSTERY PURCHASE", "category_slug"] == "hobbies"
    assert refreshed.loc["MYSTERY PURCHASE", "category_source"] == "llm"
    assert refreshed.loc["TESCO SUPERMARKET", "category_source"] == "builtin"
    assert refreshed.loc["LOCAL CLUB", "category_source"] == "manual"
