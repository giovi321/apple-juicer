from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from iphone_backup_decrypt.iphone_backup import EncryptedBackup

from core.backupfs import BackupFS, InMemoryUnlockCache
from core.backupfs.types import BackupStatus
from core.config import get_settings
from core.db.models import Backup


class UnlockError(Exception):
    """Raised when a backup cannot be unlocked."""


class SessionNotFoundError(Exception):
    """Raised when a session token is missing or expired."""


@dataclass(slots=True)
class UnlockResult:
    token: str
    ttl_seconds: int


class UnlockManager:
    """Handle unlock lifecycle without persisting secrets."""

    def __init__(self, cache: InMemoryUnlockCache | None = None, sandbox_root: str | None = None):
        settings = get_settings()
        self.cache = cache or InMemoryUnlockCache()
        self.sandbox_root = Path(sandbox_root or settings.backup_paths.temp_path)
        self.sandbox_root.mkdir(parents=True, exist_ok=True)

    def unlock(self, backup: Backup, password: str) -> UnlockResult:
        backup_path = Path(backup.path)
        if not backup_path.exists():
            raise UnlockError(f"Backup path missing: {backup.path}")
        try:
            handle = EncryptedBackup(backup_directory=str(backup_path), passphrase=password)
            handle.test_decryption()
        except ValueError as exc:
            raise UnlockError("Invalid password") from exc
        except Exception as exc:  # pragma: no cover - safety net
            raise UnlockError(str(exc)) from exc
        token = self.cache.put(backup.ios_identifier, handle)
        backup.status = BackupStatus.UNLOCKED
        return UnlockResult(token=token, ttl_seconds=self.cache.ttl_seconds)

    def revoke(self, token: str) -> None:
        self.cache.revoke(token)

    def get_filesystem(self, token: str) -> tuple[str, BackupFS]:
        session = self.cache.get(token)
        if not session:
            raise SessionNotFoundError("Session expired or invalid.")
        fs = BackupFS(handle=session.handle, sandbox_root=self.sandbox_root)
        return session.backup_id, fs
