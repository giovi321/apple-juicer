from __future__ import annotations

import os
import plistlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .types import BackupStatus, BackupSummary


class BackupDiscoveryError(Exception):
    """Raised when a backup cannot be parsed."""


@dataclass(slots=True)
class BackupMetadata:
    identifier: str
    path: Path
    display_name: str
    device_name: Optional[str]
    product_version: Optional[str]
    is_encrypted: bool
    size_bytes: Optional[int]
    status: BackupStatus
    last_modified_at: Optional[datetime]


class BackupDiscovery:
    """Scan a base directory for iOS backups and surface metadata."""

    def __init__(self, base_path: Path):
        self.base_path = base_path.expanduser().resolve()

    def discover(self) -> List[BackupSummary]:
        backups: List[BackupSummary] = []
        if not self.base_path.exists():
            return backups
        for entry in sorted(self.base_path.iterdir()):
            if not entry.is_dir():
                continue
            manifest_plist = entry / "Manifest.plist"
            manifest_db = entry / "Manifest.db"
            if not manifest_plist.exists() or not manifest_db.exists():
                continue
            try:
                metadata = self._read_backup_metadata(entry, manifest_plist)
            except BackupDiscoveryError:
                continue
            info = self._read_info_plist(entry)
            status = BackupStatus.LOCKED if metadata.is_encrypted else BackupStatus.UNLOCKED
            backups.append(
                BackupSummary(
                    backup_id=metadata.identifier or entry.name,
                    path=entry,
                    display_name=info.get("Device Name") or info.get("Display Name") or entry.name,
                    device_name=info.get("Device Name"),
                    product_version=info.get("Product Version"),
                    is_encrypted=metadata.is_encrypted,
                    status=status,
                    size_bytes=metadata.size_bytes,
                    last_modified_at=metadata.last_modified_at,
                )
            )
        return backups

    def _read_backup_metadata(self, root: Path, manifest_plist: Path) -> BackupMetadata:
        try:
            with manifest_plist.open("rb") as fp:
                plist = plistlib.load(fp)
        except (OSError, plistlib.InvalidFileException) as exc:
            raise BackupDiscoveryError(str(exc)) from exc
        identifier = plist.get("Lockdown", {}).get("UniqueDeviceID") or root.name
        is_encrypted = bool(plist.get("IsEncrypted", True))
        size_bytes = self._compute_directory_size(root)
        return BackupMetadata(
            identifier=identifier,
            path=root,
            display_name=root.name,
            device_name=None,
            product_version=None,
            is_encrypted=is_encrypted,
            size_bytes=size_bytes,
            status=BackupStatus.LOCKED if is_encrypted else BackupStatus.UNLOCKED,
            last_modified_at=self._read_last_modified(root),
        )

    def _read_info_plist(self, root: Path) -> dict:
        info_plist = root / "Info.plist"
        if not info_plist.exists():
            return {}
        try:
            with info_plist.open("rb") as fp:
                return plistlib.load(fp)
        except (OSError, plistlib.InvalidFileException):
            return {}

    def _read_last_modified(self, root: Path) -> Optional[datetime]:
        try:
            stat = root.stat()
        except OSError:
            return None
        return datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

    def _compute_directory_size(self, root: Path) -> Optional[int]:
        total = 0
        for current_root, dirnames, filenames in os.walk(root, followlinks=False):
            for name in list(dirnames):
                dir_path = Path(current_root) / name
                if dir_path.is_symlink():
                    dirnames.remove(name)
            for filename in filenames:
                path = Path(current_root) / filename
                try:
                    if path.is_symlink():
                        continue
                    total += path.stat(follow_symlinks=False).st_size
                except OSError:
                    continue
        return total
