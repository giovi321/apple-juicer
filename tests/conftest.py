from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Point the app at an isolated SQLite database BEFORE any app module imports
# core.config / core.db.session, both of which read settings at import time.
_TMP_DIR = Path(tempfile.mkdtemp(prefix="apple_juicer_tests_"))
os.environ.setdefault("APPLE_JUICER_ENVIRONMENT", "test")
os.environ["APPLE_JUICER_POSTGRES__DSN"] = f"sqlite+aiosqlite:///{(_TMP_DIR / 'test.db').as_posix()}"
os.environ.setdefault("APPLE_JUICER_REDIS__URL", "redis://localhost:6379/0")
os.environ.setdefault("APPLE_JUICER_SECURITY__API_TOKEN", "test-token")
# Service singletons in api.dependencies create these dirs at import time, so
# they must point somewhere writable (the default /data is root-owned on CI).
os.environ.setdefault("APPLE_JUICER_BACKUP_PATHS__BASE_PATH", str(_TMP_DIR / "ios_backups"))
os.environ.setdefault("APPLE_JUICER_BACKUP_PATHS__TEMP_PATH", str(_TMP_DIR / "tmp"))
os.environ.setdefault("APPLE_JUICER_BACKUP_PATHS__DECRYPTED_PATH", str(_TMP_DIR / "decrypted"))

import pytest_asyncio  # noqa: E402


@pytest_asyncio.fixture
async def db():
    """Create a fresh schema for each test and drop it afterwards."""
    from core.db.base import Base
    from core.db.session import engine
    import core.db.models  # noqa: F401  (register tables on the metadata)
    import core.db.artifacts  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
