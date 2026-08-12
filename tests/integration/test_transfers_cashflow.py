from __future__ import annotations

from datetime import date

from nimo.application.container import ApplicationContainer
from nimo.domain.models import GenerationRequest


def test_internal_transfers_are_paired_and_excluded_from_external_spend(project_root, data_root) -> None:
    container = ApplicationContainer.for_user(
        "transfer_user", project_root=project_root, data_root=data_root, create=True, source_type="generated"
    )
    container.generation.generate(
        GenerationRequest(
            "transfer_user",
            42,
            date(2024, 1, 1),
            date(2025, 12, 31),
            archetype="stable_saver",
        )
    )
    frame = container.analysis.transaction_frame()
    transfer_rows = frame.loc[frame["description_raw"].str.contains("TRANSFER", case=False)]
    assert not transfer_rows.empty
    assert transfer_rows["transfer_group_id"].notna().all()

    metrics = container.analysis.overview()
    external = frame.loc[frame["transfer_group_id"].isna()]
    assert round(metrics.total_spend, 2) == round(-external.loc[external["amount"] < 0, "amount"].sum(), 2)
    payload = container.analysis.cashflow()
    assert any(link["flow_type"] == "internal_transfer" for link in payload["links"])


def test_manual_transfer_rejection_and_confirmation_survive_refresh(container, tmp_path) -> None:
    import pandas as pd

    current_path = tmp_path / "current.csv"
    savings_path = tmp_path / "savings.csv"
    pd.DataFrame(
        [
            {
                "bank_name": "NIMO Bank",
                "account_number": "11111111",
                "account_name": "Current",
                "date": "2026-03-01",
                "description": "TRANSFER TO SAVINGS",
                "amount": -100.0,
            }
        ]
    ).to_csv(current_path, index=False)
    pd.DataFrame(
        [
            {
                "bank_name": "NIMO Bank",
                "account_number": "22222222",
                "account_name": "Savings",
                "date": "2026-03-01",
                "description": "TRANSFER FROM CURRENT",
                "amount": 100.0,
            }
        ]
    ).to_csv(savings_path, index=False)

    container.ingestion.import_csv(current_path)
    container.ingestion.import_csv(savings_path)
    frame = container.analysis.transaction_frame()
    debit = frame.loc[frame["amount"] < 0].iloc[0]
    credit = frame.loc[frame["amount"] > 0].iloc[0]
    automatic_group = str(debit["transfer_group_id"])
    assert automatic_group and automatic_group == credit["transfer_group_id"]

    assert container.transfer_detector.unmatch_group(automatic_group) is True
    rejected_refresh = container.transfer_detector.detect()
    rejected_frame = container.analysis.transaction_frame()
    assert rejected_frame["transfer_group_id"].isna().all()
    assert rejected_refresh["rejected_pairs"] == 1

    manual_group = container.transfer_detector.confirm_pair(int(debit["id"]), int(credit["id"]))
    manual_refresh = container.transfer_detector.detect()
    confirmed_frame = container.analysis.transaction_frame()
    assert set(confirmed_frame["transfer_group_id"]) == {manual_group}
    assert manual_refresh["preserved_manual_pairs"] == 1
