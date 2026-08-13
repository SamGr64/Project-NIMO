from __future__ import annotations

from nimo.cli.main import main


def test_complete_cli_surface(project_root, data_root, capsys) -> None:
    common = ["--project-root", str(project_root), "--data-root", str(data_root)]
    assert main([*common, "user", "create", "cli_complete"]) == 0
    assert main([
        *common,
        "generate",
        "cli_complete",
        "--seed",
        "88",
        "--start",
        "2024-01-01",
        "--end",
        "2026-07-31",
        "--answer",
        "income_pattern=predictable",
        "--answer",
        "saving_style=balanced",
        "--answer",
        "social_spend=medium",
        "--answer",
        "unexpected_costs=sometimes",
    ]) == 0
    assert main([*common, "behaviours", "cli_complete", "--json"]) == 0
    assert main([*common, "forecast", "run", "cli_complete", "--months", "3", "--runs", "100", "--json"]) == 0
    assert main([*common, "budget", "show", "cli_complete", "--json"]) == 0
    assert main([*common, "invest", "assets", "cli_complete", "--json"]) == 0
    assert main([*common, "report", "build", "cli_complete", "--format", "html", "--json"]) == 0
    assert main([*common, "doctor", "cli_complete", "--json"]) == 0
    output = capsys.readouterr().out
    assert "archetype" in output
    assert "educational" in output.lower() or "GLOBAL_EQ" in output
    assert "healthy" in output
