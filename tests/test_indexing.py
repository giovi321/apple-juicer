"""Regression tests locking in the two critical 'stuck pipeline' fixes and
proving the indexer writes rows for every artifact type.

1. The RQ indexing job must be enqueued as a *synchronous* callable, otherwise
   RQ never awaits it and indexing silently no-ops.
2. A full index run must write rows for all six artifact types without crashing
   (calendar used to raise because the model lacked the ``name`` field).
"""

from __future__ import annotations

import inspect

from fixtures import build_all


def test_index_job_sync_async_contract():
    """The wrapper RQ enqueues is sync; the underlying coroutine stays async."""
    from worker.tasks import _index_backup_job, index_backup_job

    assert not inspect.iscoroutinefunction(index_backup_job)
    assert inspect.iscoroutinefunction(_index_backup_job)


def test_queue_enqueues_sync_callable(monkeypatch, tmp_path):
    """The decrypt route must enqueue the sync wrapper, never the coroutine."""
    import api.routes.backups as routes
    import worker.tasks as tasks

    captured: dict = {}

    class FakeQueue:
        def enqueue(self, func, *args, **kwargs):
            captured["func"] = func
            captured["args"] = args
            return None

    monkeypatch.setattr(routes, "get_queue", lambda *a, **k: FakeQueue())

    decrypted = tmp_path / "decrypted"
    decrypted.mkdir()
    (decrypted / "Calendar.sqlite").write_bytes(b"placeholder")

    routes._queue_artifact_indexing("B1", str(decrypted))

    assert captured.get("func") is tasks.index_backup_job
    assert not inspect.iscoroutinefunction(captured["func"])


async def _seed_backup(backup_id: str, src_path: str):
    from core.db.models import Backup
    from core.db.session import async_session_factory

    async with async_session_factory() as session:
        session.add(
            Backup(ios_identifier=backup_id, path=src_path, display_name="Test Backup", is_encrypted=True)
        )
        await session.commit()


async def test_full_pipeline_indexes_all_types(db, tmp_path):
    """index_backup_job writes rows for every artifact type end-to-end."""
    from sqlalchemy import func, select

    from core.backupfs.types import BackupStatus
    from core.db.artifacts import (
        ArtifactSearchIndex,
        Calendar,
        CalendarEvent,
        Contact,
        Message,
        MessageAttachment,
        MessageConversation,
        Note,
        PhotoAsset,
        WhatsAppAttachment,
        WhatsAppChat,
        WhatsAppMessage,
    )
    from core.db.models import Backup
    from core.db.session import async_session_factory
    from worker.tasks import _index_backup_job

    decrypted = tmp_path / "decrypted"
    artifact_files = build_all(decrypted)

    await _seed_backup("ALL-1", str(tmp_path / "src"))
    await _index_backup_job("ALL-1", str(decrypted), artifact_files)

    async def count(model) -> int:
        async with async_session_factory() as session:
            return await session.scalar(select(func.count()).select_from(model))

    assert await count(PhotoAsset) == 2
    assert await count(WhatsAppChat) == 1
    assert await count(WhatsAppMessage) == 2
    assert await count(WhatsAppAttachment) == 1
    assert await count(MessageConversation) == 1
    assert await count(Message) == 2
    assert await count(MessageAttachment) == 1
    assert await count(Note) == 2
    assert await count(Calendar) == 1
    assert await count(CalendarEvent) == 2
    assert await count(Contact) == 1
    assert await count(ArtifactSearchIndex) >= 2  # photos populate the search index

    async with async_session_factory() as session:
        backup = await session.scalar(select(Backup).where(Backup.ios_identifier == "ALL-1"))
        calendar = await session.scalar(select(Calendar))
        contact = await session.scalar(select(Contact))

    assert backup is not None and backup.status == BackupStatus.INDEXED
    assert calendar is not None and calendar.name == "Home"
    assert contact is not None and contact.emails == ["ada@example.com"]
