from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from nimo.config.models import AppConfig, ThemeConfig


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML mapping and fail with a useful path-aware error."""
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"NIMO configuration file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise TypeError(f"Expected a YAML mapping in {path}, got {type(payload).__name__}")
    return payload


def _find_project_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists() and (candidate / "config").exists():
            return candidate
    raise FileNotFoundError(
        "Could not discover the Project NIMO root. Run from the repository or pass --project-root."
    )


@dataclass(frozen=True, slots=True)
class ProjectPaths:
    project_root: Path
    config_root: Path
    data_root: Path
    prompts_root: Path

    @classmethod
    def discover(
        cls,
        project_root: Path | None = None,
        data_root: Path | None = None,
    ) -> "ProjectPaths":
        root_hint = Path(project_root) if project_root is not None else Path(os.getenv("NIMO_PROJECT_ROOT", Path.cwd()))
        root = _find_project_root(root_hint)
        app_payload = load_yaml(root / "config" / "app.yaml")
        app_config = AppConfig.model_validate(app_payload)

        configured_data = Path(os.getenv("NIMO_DATA_ROOT", app_config.paths.data_root))
        resolved_data = Path(data_root) if data_root is not None else (
            configured_data if configured_data.is_absolute() else root / configured_data
        )
        prompts = Path(os.getenv("NIMO_PROMPTS_ROOT", app_config.paths.prompts_root))
        resolved_prompts = prompts if prompts.is_absolute() else root / prompts
        return cls(
            project_root=root,
            config_root=root / "config",
            data_root=resolved_data.resolve(),
            prompts_root=resolved_prompts.resolve(),
        )


class ConfigManager:
    """Central access point for versioned project configuration."""

    def __init__(self, paths: ProjectPaths) -> None:
        self.paths = paths
        self._cache: dict[str, dict[str, Any]] = {}
        self._app: AppConfig | None = None

    @classmethod
    def discover(
        cls,
        project_root: Path | None = None,
        data_root: Path | None = None,
    ) -> "ConfigManager":
        return cls(ProjectPaths.discover(project_root=project_root, data_root=data_root))

    @property
    def app(self) -> AppConfig:
        if self._app is None:
            self._app = AppConfig.model_validate(load_yaml(self.paths.config_root / "app.yaml"))
        return self._app

    def mapping(self, name: str) -> dict[str, Any]:
        if name not in self._cache:
            self._cache[name] = load_yaml(self.paths.config_root / f"{name}.yaml")
        return self._cache[name]

    def theme(self, name: str) -> ThemeConfig:
        normalised = name.lower()
        if normalised not in {"light", "dark"}:
            raise ValueError(f"Unknown NIMO theme: {name}")
        return ThemeConfig.model_validate(
            load_yaml(self.paths.config_root / "themes" / f"{normalised}.yaml")
        )
