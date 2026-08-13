# Database migrations

Project NIMO 1.0 records schema versions 1–11 in each user database. The current releases are additive, so the migration runner can create missing tables with SQLAlchemy metadata and write the migration ledger idempotently.

A future migration that renames/removes columns or transforms stored data must add an explicit numbered migration to `runner.py`; it must not rely on `create_all` for a destructive change. Back up user workspaces before applying such a release.
