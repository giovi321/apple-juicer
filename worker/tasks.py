from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from core.artifacts import REGISTRY, filename_to_key, truncate_artifacts
from core.backupfs.types import BackupStatus
from core.db.models import Backup, DecryptionStatus
from core.db.session import async_session_factory
from core.services import DecryptionError, DecryptOrchestrator

# Backwards-compatible alias for api.routes.backups (delete-decrypted flow).
_truncate_artifacts = truncate_artifacts


def _extract_artifact_databases(decrypted_path: str) -> dict[str, str]:
    """Map present artifact DB files to their artifact keys (registry-driven)."""
    decrypted_dir = Path(decrypted_path)
    artifact_files: dict[str, str] = {}
    for db_name, artifact_type in filename_to_key().items():
        db_path = decrypted_dir / db_name
        if db_path.exists():
            artifact_files[artifact_type] = str(db_path)
    return artifact_files


async def _index_backup_job(
    backup_identifier: str,
    artifact_bundle_dir: str,
    artifact_files: dict[str, str],
) -> None:
    job_dir = Path(artifact_bundle_dir)
    if not job_dir.exists():
        raise FileNotFoundError(f"Artifact bundle missing: {artifact_bundle_dir}")

    async with async_session_factory() as session:
        backup = await session.scalar(select(Backup).where(Backup.ios_identifier == backup_identifier))
        if not backup:
            raise RuntimeError(f"Unknown backup {backup_identifier}")

        backup.status = BackupStatus.INDEXING
        backup.indexing_progress = 0
        backup.indexing_total = 1
        backup.indexing_artifact = None
        await session.flush()
        await session.commit()

        await truncate_artifacts(session, backup)
        await session.commit()

        for spec in REGISTRY:
            source = artifact_files.get(spec.key)
            await spec.ingest(session, backup, Path(source) if source else None)
            await session.commit()

        backup.status = BackupStatus.INDEXED
        backup.last_indexed_at = datetime.now(timezone.utc)
        backup.indexing_progress = backup.indexing_total
        backup.indexing_artifact = None
        await session.commit()


def index_backup_job(backup_identifier: str, artifact_bundle_dir: str, artifact_files: dict[str, str]) -> None:
    asyncio.run(_index_backup_job(backup_identifier, artifact_bundle_dir, artifact_files))


async def _decrypt_backup_job(backup_identifier: str, password: str) -> None:
    """Decrypt a backup off the request path, then index it.

    Runs in the RQ worker so the HTTP request returns immediately and the UI
    polls /decrypt-status instead of blocking for minutes on a large backup.
    """
    orchestrator = DecryptOrchestrator()

    async with async_session_factory() as session:
        backup = await session.scalar(select(Backup).where(Backup.ios_identifier == backup_identifier))
        if not backup:
            raise RuntimeError(f"Unknown backup {backup_identifier}")
        try:
            decrypted_path = orchestrator.decrypt_backup(backup, password)
        except DecryptionError as exc:
            backup.decryption_status = DecryptionStatus.FAILED
            backup.decryption_error = str(exc)
            await session.commit()
            return

        backup.decrypted_path = decrypted_path
        backup.decryption_status = DecryptionStatus.DECRYPTED
        backup.decryption_error = None
        backup.decrypted_at = datetime.now(timezone.utc)
        await session.commit()

    artifact_files = _extract_artifact_databases(decrypted_path)
    if artifact_files:
        await _index_backup_job(backup_identifier, decrypted_path, artifact_files)


def decrypt_backup_job(backup_identifier: str, password: str) -> None:
    asyncio.run(_decrypt_backup_job(backup_identifier, password))
