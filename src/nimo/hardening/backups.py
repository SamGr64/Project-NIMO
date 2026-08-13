from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nimo.users.workspace import UserWorkspace, WorkspaceManager, slugify_user_name

ENCRYPTED_HEADER = b"NIMOENC1"


def create_backup(
    workspace: UserWorkspace,
    *,
    output_path: Path | None = None,
    include_cache: bool = False,
    passphrase: str | None = None,
) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = ".nimoenc" if passphrase else ".zip"
    output = output_path or workspace.exports_dir / f"{workspace.slug}_backup_{timestamp}{suffix}"
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nimo_backup_") as tmp_name:
        staging = Path(tmp_name) / workspace.slug
        _stage_workspace(workspace, staging, include_cache=include_cache)
        manifest = _manifest(staging)
        (staging / "backup_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        zip_path = Path(tmp_name) / f"{workspace.slug}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in sorted(staging.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(staging))
        if passphrase:
            output.write_bytes(_encrypt(zip_path.read_bytes(), passphrase))
        else:
            shutil.copy2(zip_path, output)
    return output


def verify_backup(path: Path, *, passphrase: str | None = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="nimo_verify_") as tmp_name:
        archive_path = _materialise_archive(path, Path(tmp_name), passphrase)
        with zipfile.ZipFile(archive_path) as archive:
            bad_member = archive.testzip()
            if bad_member:
                return {"valid": False, "error": f"CRC failure: {bad_member}"}
            archive.extractall(Path(tmp_name) / "content")
        root = Path(tmp_name) / "content"
        manifest_path = root / "backup_manifest.json"
        if not manifest_path.exists():
            return {"valid": False, "error": "backup_manifest.json is missing"}
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        mismatches: list[str] = []
        for item in manifest.get("files", []):
            file_path = root / item["path"]
            if not file_path.exists() or _sha256(file_path) != item["sha256"]:
                mismatches.append(item["path"])
        return {
            "valid": not mismatches,
            "user": manifest.get("user"),
            "created_at": manifest.get("created_at"),
            "file_count": len(manifest.get("files", [])),
            "mismatches": mismatches,
            "encrypted": path.read_bytes()[:8] == ENCRYPTED_HEADER,
        }


def restore_backup(
    path: Path,
    *,
    data_root: Path,
    user_name: str | None = None,
    passphrase: str | None = None,
    overwrite: bool = False,
) -> UserWorkspace:
    verification = verify_backup(path, passphrase=passphrase)
    if not verification.get("valid"):
        raise ValueError(f"Backup verification failed: {verification}")
    slug = slugify_user_name(user_name or str(verification.get("user") or "restored_user"))
    target = data_root / slug
    if target.exists() and not overwrite:
        raise FileExistsError(f"Restore target already exists: {target}")
    with tempfile.TemporaryDirectory(prefix="nimo_restore_") as tmp_name:
        temp = Path(tmp_name)
        archive_path = _materialise_archive(path, temp, passphrase)
        extracted = temp / "content"
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                resolved = (extracted / member.filename).resolve()
                if not resolved.is_relative_to(extracted.resolve()):
                    raise ValueError("Unsafe path found in backup archive")
            archive.extractall(extracted)
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(extracted, target, ignore=shutil.ignore_patterns("backup_manifest.json"))
    workspace = WorkspaceManager(data_root).workspace(slug)
    for directory in (
        workspace.raw_dir,
        workspace.database_dir,
        workspace.synthetic_dir,
        workspace.exports_dir,
        workspace.reports_dir,
        workspace.cache_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    return workspace


def _stage_workspace(workspace: UserWorkspace, staging: Path, *, include_cache: bool) -> None:
    staging.mkdir(parents=True, exist_ok=True)
    for source in workspace.root.iterdir():
        if source.name == "cache" and not include_cache:
            continue
        if source == workspace.exports_dir:
            destination = staging / "exports"
            destination.mkdir(exist_ok=True)
            for item in source.iterdir():
                if "_backup_" not in item.name:
                    _copy(item, destination / item.name)
            continue
        _copy(source, staging / source.name)
    if workspace.database_path.exists():
        snapshot = staging / "database" / workspace.database_path.name
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(workspace.database_path) as source, sqlite3.connect(snapshot) as target:
            source.backup(target)
        _normalise_snapshot_paths(snapshot, include_cache=include_cache)


def _copy(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)
    elif source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _normalise_snapshot_paths(database_path: Path, *, include_cache: bool) -> None:
    """Make path references in the backup database relocatable.

    Simulation summaries remain useful without their optional path arrays.  A
    default backup therefore clears those cache references.  When cache files
    are included, only the portable ``cache/<filename>`` value is persisted.
    Report and source-file references are similarly reduced to workspace
    relative paths.
    """

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "source_files" in tables:
            rows = connection.execute("SELECT id, stored_path FROM source_files").fetchall()
            for row_id, stored_path in rows:
                if stored_path:
                    connection.execute(
                        "UPDATE source_files SET stored_path=? WHERE id=?",
                        (f"raw/{Path(stored_path).name}", row_id),
                    )
        for table in ("forecast_runs", "investment_runs"):
            if table not in tables:
                continue
            rows = connection.execute(f"SELECT id, paths_file FROM {table}").fetchall()
            for row_id, paths_file in rows:
                portable = f"cache/{Path(paths_file).name}" if include_cache and paths_file else None
                connection.execute(
                    f"UPDATE {table} SET paths_file=? WHERE id=?",
                    (portable, row_id),
                )
        if "report_runs" in tables:
            rows = connection.execute("SELECT id, output_paths_json FROM report_runs").fetchall()
            for row_id, payload in rows:
                try:
                    outputs = json.loads(payload or "{}")
                except json.JSONDecodeError:
                    outputs = {}
                portable = {
                    key: f"reports/{Path(value).name}"
                    for key, value in outputs.items()
                    if value
                }
                connection.execute(
                    "UPDATE report_runs SET output_paths_json=? WHERE id=?",
                    (json.dumps(portable, sort_keys=True), row_id),
                )
        connection.commit()


def _manifest(root: Path) -> dict[str, Any]:
    profile = root / "profile.yaml"
    user = root.name
    if profile.exists():
        for line in profile.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("id:"):
                user = line.split(":", 1)[1].strip()
                break
    files = [
        {"path": str(path.relative_to(root)).replace(os.sep, "/"), "size": path.stat().st_size, "sha256": _sha256(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "backup_manifest.json"
    ]
    return {
        "schema_version": 1,
        "user": user,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }


def _materialise_archive(path: Path, temp: Path, passphrase: str | None) -> Path:
    payload = path.read_bytes()
    archive_path = temp / "backup.zip"
    if payload[:8] == ENCRYPTED_HEADER:
        if not passphrase:
            raise ValueError("This backup is encrypted; provide a passphrase")
        archive_path.write_bytes(_decrypt(payload, passphrase))
    else:
        archive_path.write_bytes(payload)
    return archive_path


def _encrypt(payload: bytes, passphrase: str) -> bytes:
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    except ImportError as exc:
        raise RuntimeError("Install Project NIMO with the security extra for encrypted backups") from exc
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600_000)
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))
    return ENCRYPTED_HEADER + salt + Fernet(key).encrypt(payload)


def _decrypt(payload: bytes, passphrase: str) -> bytes:
    try:
        from cryptography.fernet import Fernet, InvalidToken
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    except ImportError as exc:
        raise RuntimeError("Install Project NIMO with the security extra for encrypted backups") from exc
    salt, token = payload[8:24], payload[24:]
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600_000)
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))
    try:
        return Fernet(key).decrypt(token)
    except InvalidToken as exc:
        raise ValueError("Incorrect backup passphrase or damaged encrypted backup") from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
