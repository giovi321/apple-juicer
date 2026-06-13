from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from core.artifacts import REGISTRY, truncate_artifacts
from core.backupfs.types import BackupStatus
from core.db.models import Backup
from core.db.session import async_session_factory

# Backwards-compatible alias for api.routes.backups (delete-decrypted flow).
_truncate_artifacts = truncate_artifacts


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
