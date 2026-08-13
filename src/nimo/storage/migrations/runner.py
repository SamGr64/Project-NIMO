from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from nimo.storage.models import Base, SchemaMigration

CURRENT_SCHEMA_VERSION = 11

MIGRATIONS: tuple[tuple[int, str], ...] = (
    (1, "canonical_users_accounts_transactions"),
    (2, "seeded_generator_provenance"),
    (3, "descriptive_analysis"),
    (4, "dashboard_layouts"),
    (5, "categories_and_transfers"),
    (6, "behaviour_inference"),
    (7, "forecast_profiles_and_scenarios"),
    (8, "budgets_and_goals"),
    (9, "report_runs"),
    (10, "investment_sandbox"),
    (11, "audit_backup_and_hardening"),
)


def run_migrations(engine: Engine, session: Session) -> list[int]:
    """Apply idempotent schema migrations.

    NIMO currently adds tables without destructive column rewrites. ``create_all`` is
    therefore the migration operation for each release and the migration ledger is
    the durable record used by backup/restore and support tooling. Future migrations
    can replace an entry with explicit SQL while retaining the same runner.
    """
    Base.metadata.create_all(engine)
    applied = set(session.scalars(select(SchemaMigration.version)))
    newly_applied: list[int] = []
    for version, name in MIGRATIONS:
        if version in applied:
            continue
        session.add(SchemaMigration(version=version, name=name))
        newly_applied.append(version)
    session.flush()
    return newly_applied


def migration_names() -> Iterable[tuple[int, str]]:
    return MIGRATIONS
