from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def slugify_user_name(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    if not slug:
        raise ValueError("User name must contain at least one letter or number")
    return slug


@dataclass(frozen=True, slots=True)
class UserWorkspace:
    slug: str
    root: Path
    profile_path: Path
    raw_dir: Path
    database_dir: Path
    synthetic_dir: Path
    exports_dir: Path
    reports_dir: Path
    cache_dir: Path

    @property
    def database_path(self) -> Path:
        return self.database_dir / "nimo.sqlite3"

    def path_for_storage(self, path: Path) -> str:
        """Return a portable workspace-relative path whenever possible.

        Older NIMO builds sometimes persisted absolute cache/report paths in the
        SQLite database.  Relative paths make backups and copied workspaces
        relocatable across Windows, macOS and Linux machines.
        """

        candidate = Path(path)
        try:
            return candidate.resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return str(candidate)

    def resolve_stored_path(self, value: str | Path) -> Path:
        """Resolve a path stored by :meth:`path_for_storage`.

        Absolute legacy paths remain supported.  Relative values are always
        interpreted from the user workspace root, never from the process CWD.
        """

        candidate = Path(value)
        return candidate if candidate.is_absolute() else self.root / candidate

    def read_profile(self) -> dict[str, Any]:
        if not self.profile_path.exists():
            return {}
        payload = yaml.safe_load(self.profile_path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise TypeError(f"Invalid user profile mapping: {self.profile_path}")
        return payload

    def write_profile(self, payload: dict[str, Any]) -> None:
        self.profile_path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    def update_profile(self, updates: dict[str, Any]) -> dict[str, Any]:
        profile = self.read_profile()
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(profile.get(key), dict):
                profile[key] = _deep_merge(profile[key], value)
            else:
                profile[key] = value
        self.write_profile(profile)
        return profile


def _deep_merge(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


class WorkspaceManager:
    def __init__(self, data_root: Path) -> None:
        self.data_root = data_root
        self.data_root.mkdir(parents=True, exist_ok=True)

    def workspace(self, user_name: str, *, require_exists: bool = True) -> UserWorkspace:
        slug = slugify_user_name(user_name)
        root = self.data_root / slug
        if require_exists and not root.exists():
            raise FileNotFoundError(f"NIMO user does not exist: {slug}")
        return UserWorkspace(
            slug=slug,
            root=root,
            profile_path=root / "profile.yaml",
            raw_dir=root / "raw",
            database_dir=root / "database",
            synthetic_dir=root / "synthetic",
            exports_dir=root / "exports",
            reports_dir=root / "reports",
            cache_dir=root / "cache",
        )

    def create(
        self,
        user_name: str,
        *,
        display_name: str | None = None,
        source_type: str = "imported",
        currency: str = "GBP",
    ) -> UserWorkspace:
        workspace = self.workspace(user_name, require_exists=False)
        for directory in (
            workspace.root,
            workspace.raw_dir,
            workspace.database_dir,
            workspace.synthetic_dir,
            workspace.exports_dir,
            workspace.reports_dir,
            workspace.cache_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

        if not workspace.profile_path.exists():
            now = datetime.now(timezone.utc).isoformat()
            workspace.write_profile(
                {
                    "schema_version": 1,
                    "user": {
                        "id": workspace.slug,
                        "display_name": display_name or user_name,
                        "created_at": now,
                        "source_type": source_type,
                        "currency": currency,
                        "locale": "en-GB",
                    },
                    "preferences": {
                        "default_period": "trailing_12_months",
                        "theme": "system",
                        "dashboard_layouts": {},
                    },
                }
            )
        return workspace

    def list_users(self) -> list[str]:
        if not self.data_root.exists():
            return []
        return sorted(
            path.name
            for path in self.data_root.iterdir()
            if path.is_dir() and (path / "profile.yaml").exists()
        )
