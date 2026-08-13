from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from sqlalchemy import select, text

from nimo.storage.database import Database
from nimo.storage.migrations import CURRENT_SCHEMA_VERSION
from nimo.storage.models import ForecastRunRecord, InvestmentRunRecord, SchemaMigration, SourceFile
from nimo.storage.versioning import source_data_version
from nimo.users.workspace import UserWorkspace


def run_doctor(*, database: Database, workspace: UserWorkspace) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    with database.session() as session:
        integrity = session.execute(text("PRAGMA integrity_check")).scalar()
        checks.append(_check("sqlite_integrity", integrity == "ok", str(integrity)))
        foreign_keys = list(session.execute(text("PRAGMA foreign_key_check")))
        checks.append(_check("foreign_keys", not foreign_keys, f"{len(foreign_keys)} violation(s)"))
        latest_migration = session.scalar(select(SchemaMigration.version).order_by(SchemaMigration.version.desc())) or 0
        checks.append(_check("schema_version", latest_migration == CURRENT_SCHEMA_VERSION, f"database={latest_migration}, application={CURRENT_SCHEMA_VERSION}"))
        source_checks = []
        for source in session.scalars(select(SourceFile)):
            path = workspace.resolve_stored_path(source.stored_path)
            source_checks.append(path.exists() and _sha256(path) == source.sha256)
        checks.append(_check("raw_source_hashes", all(source_checks), f"checked={len(source_checks)}"))
        missing_forecast = [
            record.id
            for record in session.scalars(select(ForecastRunRecord))
            if record.paths_file and not workspace.resolve_stored_path(record.paths_file).exists()
        ]
        checks.append(_check("forecast_cache_references", not missing_forecast, f"missing={missing_forecast}"))
        missing_investment = [
            record.id
            for record in session.scalars(select(InvestmentRunRecord))
            if record.paths_file and not workspace.resolve_stored_path(record.paths_file).exists()
        ]
        checks.append(_check("investment_cache_references", not missing_investment, f"missing={missing_investment}"))
        data_version = source_data_version(session)
    required_dirs = [workspace.raw_dir, workspace.database_dir, workspace.synthetic_dir, workspace.exports_dir, workspace.reports_dir, workspace.cache_dir]
    checks.append(_check("workspace_directories", all(path.exists() for path in required_dirs), ", ".join(path.name for path in required_dirs)))
    return {
        "healthy": all(check["passed"] for check in checks),
        "user": workspace.slug,
        "database": str(database.path),
        "source_data_version": data_version,
        "checks": checks,
    }


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
