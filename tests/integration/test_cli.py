from __future__ import annotations

from nimo.cli.main import main


def test_cli_can_create_generate_and_analyse(project_root, data_root, capsys) -> None:
    common = ["--project-root", str(project_root), "--data-root", str(data_root)]
    assert main([*common, "user", "create", "cli_user"]) == 0
    assert main([
        *common,
        "generate",
        "cli_user",
        "--seed",
        "7",
        "--start",
        "2025-01-01",
        "--end",
        "2025-03-31",
    ]) == 0
    assert main([*common, "analyse", "cli_user", "--json"]) == 0
    output = capsys.readouterr().out
    assert "transaction_count" in output
