from __future__ import annotations

import copy
from typing import Any


def resolve_profile(profile: dict[str, Any], overrides: dict[str, Any] | None) -> dict[str, Any]:
    resolved = copy.deepcopy(profile)
    for path, value in (overrides or {}).items():
        set_path(resolved, path, value)
    return resolved


def set_path(payload: dict[str, Any], path: str, value: Any) -> None:
    parts = [part for part in path.split(".") if part]
    if not parts:
        raise ValueError("Scenario override path cannot be empty")
    current: dict[str, Any] = payload
    for part in parts[:-1]:
        child = current.get(part)
        if child is None:
            child = {}
            current[part] = child
        if not isinstance(child, dict):
            raise ValueError(f"Cannot set {path}: {part} is not a mapping")
        current = child
    current[parts[-1]] = value


def get_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def validate_override(profile: dict[str, Any], path: str, value: Any) -> None:
    existing = get_path(profile, path)
    if isinstance(existing, (int, float)) and not isinstance(value, (int, float)):
        raise TypeError(f"Override {path} must be numeric")
    if path.endswith("zero_probability") and not 0 <= float(value) <= 1:
        raise ValueError("Probability overrides must be between 0 and 1")
    if path.endswith("monthly_std") and float(value) < 0:
        raise ValueError("Standard deviation cannot be negative")
