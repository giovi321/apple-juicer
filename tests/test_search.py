"""Global search returns cross-artifact matches from the search index."""

from __future__ import annotations

from sqlalchemy import select

from fixtures import build_all


class _Registry:
    def __init__(self, session):
        self.session = session

    async def get_backup(self, identifier: str):
        from core.db.models import Backup

        return await self.session.scalar(select(Backup).where(Backup.ios_identifier == identifier))


async def _index_decrypted(tmp_path):
    from core.db.models import Backup, DecryptionStatus
    from core.db.session import async_session_factory
    from worker.tasks import _index_backup_job

    decrypted = tmp_path / "decrypted"
    artifact_files = build_all(decrypted)
    backup_id = "SEARCH-1"
    async with async_session_factory() as session:
        session.add(
            Backup(ios_identifier=backup_id, path=str(tmp_path / "src"), display_name="t", is_encrypted=True)
        )
        await session.commit()
    await _index_backup_job(backup_id, str(decrypted), artifact_files)
    async with async_session_factory() as session:
        backup = await session.scalar(select(Backup).where(Backup.ios_identifier == backup_id))
        backup.decryption_status = DecryptionStatus.DECRYPTED
        backup.decrypted_path = str(decrypted)
        await session.commit()
    return backup_id


async def _search(backup_id, q):
    from core.db.session import async_session_factory

    from api.routes import search

    async with async_session_factory() as session:
        registry = _Registry(session)
        return await search.search_artifacts(backup_id, q=q, registry=registry, session=session)


async def test_search_covers_all_artifact_types(db, tmp_path):
    backup_id = await _index_decrypted(tmp_path)

    async def types(q):
        result = await _search(backup_id, q)
        return {item.artifact_type for item in result.items}

    assert "contact" in await types("Ada")
    assert "note" in await types("Milk")
    assert "calendar_event" in await types("Meeting")
    assert "message" in await types("Hello from Grace")
    assert "whatsapp_message" in await types("See attached")
    assert "photo" in await types("IMG_0001")


async def test_search_empty_and_no_match(db, tmp_path):
    backup_id = await _index_decrypted(tmp_path)

    blank = await _search(backup_id, "   ")
    assert blank.items == []

    nomatch = await _search(backup_id, "zzz-no-such-term-zzz")
    assert nomatch.items == []
