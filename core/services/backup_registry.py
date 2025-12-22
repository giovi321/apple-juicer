from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.backupfs import BackupDiscovery
from core.backupfs.types import BackupStatus, BackupSummary
from core.config import get_settings
from core.db.models import Backup

settings = get_settings()


class BackupRegistry:
    """Bridge between filesystem discovery and persisted backups."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.discovery = BackupDiscovery(Path(settings.backup_paths.base_path))
        self._lock = asyncio.Lock()

    async def refresh(self) -> List[BackupSummary]:
        summaries = self.discovery.discover()
        summary_map = {summary.backup_id: summary for summary in summaries}
        async with self._lock:
            existing = {backup.ios_identifier: backup for backup in await self._fetch_all()}
            upserts: List[Backup] = []
            for summary in summaries:
                backup = existing.get(summary.backup_id)
                if backup:
                    backup.path = str(summary.path)
                    backup.display_name = summary.display_name
                    backup.device_name = summary.device_name
                    backup.product_version = summary.product_version
                    backup.is_encrypted = summary.is_encrypted
                    backup.size_bytes = summary.size_bytes
                    if summary.is_encrypted and backup.status == BackupStatus.UNLOCKED:
                        backup.status = BackupStatus.LOCKED
                    backup.mark_seen()
                else:
                    backup = Backup(
                        ios_identifier=summary.backup_id,
                        path=str(summary.path),
                        display_name=summary.display_name,
                        device_name=summary.device_name,
                        product_version=summary.product_version,
                        is_encrypted=summary.is_encrypted,
                        status=summary.status,
                        size_bytes=summary.size_bytes,
                    )
                    self.session.add(backup)
                upserts.append(backup)
            await self.session.flush()
            await self.session.commit()
        return [
            BackupSummary(
                backup_id=backup.ios_identifier,
                path=Path(backup.path),
                display_name=backup.display_name,
                device_name=backup.device_name,
                product_version=backup.product_version,
                is_encrypted=backup.is_encrypted,
                status=backup.status,
                last_indexed_at=backup.last_indexed_at,
                size_bytes=backup.size_bytes,
                last_modified_at=summary_map.get(backup.ios_identifier, None).last_modified_at
                if summary_map.get(backup.ios_identifier, None)
                else None,
            )
            for backup in upserts
        ]

    async def list_backups(self) -> List[Backup]:
        result = await self.session.scalars(select(Backup).order_by(Backup.created_at.desc()))
        return list(result)

    async def get_backup(self, identifier: str) -> Backup | None:
        result = await self.session.scalars(select(Backup).where(Backup.ios_identifier == identifier))
        return result.first()

    async def _fetch_all(self) -> List[Backup]:
        result = await self.session.scalars(select(Backup))
        return list(result)
