from __future__ import annotations

from nimo.config.loader import ConfigManager


def test_configuration_bundle_loads(project_root, data_root) -> None:
    config = ConfigManager.discover(project_root=project_root, data_root=data_root)
    assert config.app.application.default_currency == "GBP"
    assert "formats" in config.mapping("statement_formats")
    assert config.theme("dark").surface.background.startswith("#")
