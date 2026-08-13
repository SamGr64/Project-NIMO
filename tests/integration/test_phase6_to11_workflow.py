from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from nimo.application.container import ApplicationContainer
from nimo.domain.models import GenerationRequest
from nimo.hardening import restore_backup


def test_behaviour_forecast_planning_investing_reporting_and_backup(project_root, data_root, tmp_path) -> None:
    app = ApplicationContainer.for_user(
        "complete_user",
        project_root=project_root,
        data_root=data_root,
        create=True,
        source_type="generated",
    )
    app.generation.generate(
        GenerationRequest(
            "complete_user",
            4242,
            date(2024, 1, 1),
            date(2026, 7, 31),
        )
    )

    behaviour = app.behaviours.refresh(force=True)
    assert behaviour["archetype"]["label"]
    assert app.behaviours.patterns_frame().shape[0] > 0
    assert "ground_truth" not in str(behaviour).lower()

    profile = app.forecasting.ensure_default_profile(force=True)
    assert profile["profile"]["history_months"] >= 24
    app.forecasting.create_scenario("User Plan")
    app.forecasting.set_override("User Plan", "global_assumptions.annual_inflation_rate", 0.04)
    app.forecasting.add_event(
        "User Plan",
        name="Planned course",
        event_date=date(2026, 11, 1),
        amount=-750.0,
        uncertainty=75.0,
    )
    forecast = app.forecasting.run(scenario="User Plan", horizon_months=6, runs=250, seed=991)
    repeated = app.forecasting.run(scenario="User Plan", horizon_months=6, runs=250, seed=991, store=False)
    assert forecast["final_balance"] == repeated["summary"]["final_balance"]
    assert forecast["simulation_runs"] == 250
    assert app.workspace.resolve_stored_path(forecast["paths_file"]).exists()

    budget = app.planning.ensure_default_budget(force=True)
    assert budget["lines"]
    evaluation = app.planning.evaluate(runs=200)
    assert evaluation["total_budget"] >= 0
    assert all(
        line["probability_within_budget"] is None
        or 0.0 <= line["probability_within_budget"] <= 1.0
        for line in evaluation["lines"]
    )

    goal = app.planning.add_goal(
        name="Emergency Fund",
        target_amount=5000.0,
        target_date=date.today() + timedelta(days=550),
        current_amount=750.0,
        monthly_contribution=150.0,
        surplus_allocation_fraction=0.2,
    )
    goal_result = app.planning.simulate_goal(goal["id"], runs=200, seed=123)
    assert 0.0 <= goal_result["probability_achieved"] <= 1.0

    assets = app.investing.assets()
    assert {"GLOBAL_EQ", "BOND", "CASH"}.issubset({row["symbol"] for row in assets})
    investment = app.investing.simulate(horizon_years=2, runs=200, seed=777)
    assert investment["educational_notice"]
    assert 0.0 <= investment["probability_negative_cash"] <= 1.0
    assert app.workspace.resolve_stored_path(investment["paths_file"]).exists()

    report = app.reporting.build(formats=["html", "md", "pdf", "docx"], use_llm=False)
    assert report["provider"] == "offline"
    for stored_path in report["outputs"].values():
        output = app.workspace.resolve_stored_path(stored_path)
        assert output.exists() and output.stat().st_size > 0

    backup_path = app.backups.create(output_path=tmp_path / "complete_user.zip")
    verification = app.backups.verify(backup_path)
    assert verification["valid"] is True
    restored_root = tmp_path / "restored"
    restored = restore_backup(backup_path, data_root=restored_root, user_name="restored_user")
    restored_app = ApplicationContainer.for_user(
        restored.slug,
        project_root=project_root,
        data_root=restored_root,
    )
    assert restored_app.analysis.overview().transaction_count == app.analysis.overview().transaction_count
    assert restored_app.backups.doctor()["healthy"] is True


def test_encrypted_backup_round_trip(project_root, data_root, tmp_path) -> None:
    app = ApplicationContainer.for_user(
        "secure_user",
        project_root=project_root,
        data_root=data_root,
        create=True,
    )
    path = app.backups.create(output_path=tmp_path / "secure_user.nimoenc", passphrase="correct horse battery staple")
    assert app.backups.verify(path, passphrase="correct horse battery staple")["valid"] is True
