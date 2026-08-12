from __future__ import annotations

from datetime import date

from nimo.application.container import ApplicationContainer
from nimo.domain.models import GenerationRequest


def test_same_seed_produces_identical_statement_files(project_root, data_root) -> None:
    first = ApplicationContainer.for_user(
        "seed_a", project_root=project_root, data_root=data_root, create=True, source_type="generated"
    )
    second = ApplicationContainer.for_user(
        "seed_b", project_root=project_root, data_root=data_root, create=True, source_type="generated"
    )
    request_a = GenerationRequest("seed_a", 901, date(2025, 1, 1), date(2025, 6, 30))
    request_b = GenerationRequest("seed_b", 901, date(2025, 1, 1), date(2025, 6, 30))
    result_a = first.generation.generate(request_a)
    result_b = second.generation.generate(request_b)

    contents_a = sorted(path.read_text(encoding="utf-8") for path in result_a.statement_paths)
    contents_b = sorted(path.read_text(encoding="utf-8") for path in result_b.statement_paths)
    assert contents_a == contents_b
    assert first.analysis.overview().transaction_count > 0


def test_generated_bus_rows_can_be_visually_identical(project_root, data_root) -> None:
    container = ApplicationContainer.for_user(
        "bus_user", project_root=project_root, data_root=data_root, create=True, source_type="generated"
    )
    container.generation.generate(
        GenerationRequest("bus_user", 42, date(2025, 1, 1), date(2025, 3, 31))
    )
    frame = container.analysis.transaction_frame()
    buses = frame.loc[frame["description_raw"] == "TFL BUS JOURNEY"]
    duplicates = buses.duplicated(subset=["booking_date", "account_id", "description_raw", "amount"], keep=False)
    assert duplicates.any()


def test_every_configured_statement_format_round_trips(project_root, data_root) -> None:
    from nimo.config.loader import ConfigManager

    config = ConfigManager.discover(project_root=project_root, data_root=data_root)
    format_names = sorted(config.mapping("statement_formats").get("formats", {}))
    for index, format_name in enumerate(format_names):
        user_name = f"format_{index}"
        container = ApplicationContainer.for_user(
            user_name,
            project_root=project_root,
            data_root=data_root,
            create=True,
            source_type="generated",
        )
        result = container.generation.generate(
            GenerationRequest(
                user_name,
                1200 + index,
                date(2025, 1, 1),
                date(2025, 3, 31),
                statement_format=format_name,
            )
        )
        assert result.imported_rows > 0
        assert container.analysis.overview().transaction_count == result.imported_rows
