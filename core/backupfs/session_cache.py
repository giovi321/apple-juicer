from __future__ import annotations

import secrets
from collections.abc import MutableMapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import RLock
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from iphone_backup_decrypt.iphone_backup import EncryptedBackup


@dataclass(slots=True)
class UnlockSession:
    backup_id: str
    handle: "EncryptedBackup"
    created_at: datetime
    expires_at: datetime

    def refresh(self, ttl: timedelta) -> None:
        self.expires_at = datetime.utcnow() + ttl


class InMemoryUnlockCache:
    """Store unlock secrets per API token (not persisted)."""

    def __init__(self, ttl_seconds: int = 3600):
        self._ttl_seconds = ttl_seconds
        self._ttl = timedelta(seconds=ttl_seconds)
        self._lock = RLock()
        self._store: MutableMapping[str, UnlockSession] = {}

    @property
    def ttl_seconds(self) -> int:
        return self._ttl_seconds

    def put(self, backup_id: str, handle: "EncryptedBackup") -> str:
        token = secrets.token_hex(16)
        session = UnlockSession(
            backup_id=backup_id,
            handle=handle,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + self._ttl,
        )
        with self._lock:
            self._store[token] = session
        return token

    def get(self, token: str) -> Optional[UnlockSession]:
        with self._lock:
            session = self._store.get(token)
            if not session:
                return None
            if session.expires_at <= datetime.utcnow():
                self._dispose_session(token, session)
                return None
            # refresh TTL
            session.refresh(self._ttl)
            return session

    def revoke(self, token: str) -> None:
        with self._lock:
            session = self._store.pop(token, None)
        if session:
            self._cleanup(session)

    def purge_expired(self) -> None:
        with self._lock:
            expired = [(token, session) for token, session in self._store.items() if session.expires_at <= datetime.utcnow()]
            for token, session in expired:
                self._dispose_session(token, session)

    def _dispose_session(self, token: str, session: UnlockSession) -> None:
        self._store.pop(token, None)
        self._cleanup(session)

    @staticmethod
    def _cleanup(session: UnlockSession) -> None:
        handle = session.handle
        try:
            cleanup = getattr(handle, "_cleanup", None)
            if callable(cleanup):
                cleanup()
        except Exception:
            # Best effort cleanup; ignore errors since temp dirs are per-session.
            pass
