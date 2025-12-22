from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends

from core.db.session import get_async_session
from core.services import BackupRegistry, DecryptOrchestrator
from core.services.unlock_manager import UnlockManager

_unlock_manager = UnlockManager()
_decrypt_orchestrator = DecryptOrchestrator()


async def get_db_session() -> AsyncGenerator:
    async for session in get_async_session():
        yield session


async def get_backup_registry(session=Depends(get_db_session)) -> BackupRegistry:
    return BackupRegistry(session)  # type: ignore[arg-type]


def get_unlock_manager() -> UnlockManager:
    return _unlock_manager


def get_decrypt_orchestrator() -> DecryptOrchestrator:
    return _decrypt_orchestrator
