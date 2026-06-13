"""The in-memory unlock cache expires, purges, and cleans up sessions."""

from __future__ import annotations

from datetime import datetime, timedelta

from core.backupfs.session_cache import InMemoryUnlockCache


class _Handle:
    def __init__(self):
        self.cleaned = False

    def _cleanup(self):
        self.cleaned = True


def test_get_returns_live_session():
    cache = InMemoryUnlockCache(ttl_seconds=3600)
    token = cache.put("backup-1", _Handle())
    session = cache.get(token)
    assert session is not None
    assert session.backup_id == "backup-1"


def test_expired_session_is_not_returned_and_cleaned():
    cache = InMemoryUnlockCache(ttl_seconds=3600)
    handle = _Handle()
    token = cache.put("backup-1", handle)
    cache._store[token].expires_at = datetime.utcnow() - timedelta(seconds=1)

    assert cache.get(token) is None  # get() disposes expired sessions
    assert handle.cleaned is True


def test_purge_expired_removes_stale_sessions():
    cache = InMemoryUnlockCache(ttl_seconds=3600)
    handle = _Handle()
    token = cache.put("backup-1", handle)
    cache._store[token].expires_at = datetime.utcnow() - timedelta(seconds=1)

    cache.purge_expired()

    assert token not in cache._store
    assert handle.cleaned is True


def test_revoke_cleans_up():
    cache = InMemoryUnlockCache(ttl_seconds=3600)
    handle = _Handle()
    token = cache.put("backup-1", handle)
    cache.revoke(token)
    assert cache.get(token) is None
    assert handle.cleaned is True
