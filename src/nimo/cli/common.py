from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from nimo.application.container import ApplicationContainer
from nimo.application.services.user_service import UserService
from nimo.config.loader import ConfigManager


def config_from_args(args: Any) -> ConfigManager:
    return ConfigManager.discover(
        project_root=getattr(args, "project_root", None),
        data_root=getattr(args, "data_root", None),
    )


def user_service_from_args(args: Any) -> UserService:
    return UserService(config_from_args(args))


def container_from_args(args: Any, user_name: str, *, create: bool = False) -> ApplicationContainer:
    return ApplicationContainer.for_user(
        user_name,
        project_root=getattr(args, "project_root", None),
        data_root=getattr(args, "data_root", None),
        create=create,
    )


def json_default(value: Any) -> Any:
    if isinstance(value, (date, datetime, Path)):
        return str(value)
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Cannot serialise {type(value).__name__}")


def print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=json_default))


def print_table(rows: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    if not rows:
        print("No rows.")
        return
    columns = columns or list(rows[0])
    widths = {
        column: max(len(column), *(len(_format(row.get(column))) for row in rows))
        for column in columns
    }
    print("  ".join(column.ljust(widths[column]) for column in columns))
    print("  ".join("-" * widths[column] for column in columns))
    for row in rows:
        print("  ".join(_format(row.get(column)).ljust(widths[column]) for column in columns))


def _format(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)
