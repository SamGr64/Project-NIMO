from __future__ import annotations

from pathlib import Path

from nimo.hardening import create_backup, run_doctor, verify_backup
from nimo.storage.audit import record_audit
from nimo.storage.database import Database
from nimo.users.workspace import UserWorkspace


class BackupService:
    def __init__(self, *, database: Database, workspace: UserWorkspace) -> None:
        self.database = database
        self.workspace = workspace

    def create(self, *, output_path: Path | None = None, include_cache: bool = False, passphrase: str | None = None) -> Path:
        path = create_backup(self.workspace, output_path=output_path, include_cache=include_cache, passphrase=passphrase)
        with self.database.session() as session:
            record_audit(session, "backup_created", object_type="backup", object_id=str(path), details={"encrypted": bool(passphrase), "include_cache": include_cache})
        return path

    def verify(self, path: Path, *, passphrase: str | None = None):
        return verify_backup(path, passphrase=passphrase)

    def doctor(self):
        return run_doctor(database=self.database, workspace=self.workspace)
