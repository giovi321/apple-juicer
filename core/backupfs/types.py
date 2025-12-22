from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class BackupStatus(str, Enum):
    DISCOVERED = "discovered"
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    INDEXING = "indexing"
    INDEXED = "indexed"


@dataclass(slots=True)
class BackupSummary:
    backup_id: str
    path: Path
    display_name: str
    is_encrypted: bool
    status: BackupStatus
    device_name: Optional[str] = None
    product_version: Optional[str] = None
    last_indexed_at: Optional[datetime] = None
    size_bytes: Optional[int] = None
    last_modified_at: Optional[datetime] = None


@dataclass(slots=True)
class ManifestFileEntry:
    file_id: str
    domain: str
    relative_path: str
    flags: int
    size: Optional[int]
    mtime: Optional[int]


class UnlockState(str, Enum):
    UNKNOWN = "unknown"
    LOCKED = "locked"
    FAILED = "failed"
    READY = "ready"
