"""The Photos/Notes/Calendar/Contacts endpoints return indexed rows.

Calls the route coroutines directly (single event loop, no TestClient) with a
minimal registry, after indexing the synthetic fixture into the test DB.
"""

from __future__ import annotations

from sqlalchemy import select

from fixtures import build_all


class _Registry:
    def __init__(self, session):
        self.session = session

    async def get_backup(self, identifier: str):
        from core.db.models import Backup

        return await self.session.scalar(select(Backup).where(Backup.ios_identifier == identifier))


async def test_artifact_endpoints_return_indexed_rows(db, tmp_path):
    from core.db.models import Backup, DecryptionStatus
    from core.db.session import async_session_factory
    from worker.tasks import _index_backup_job

    from api.routes import (
        artifacts_calendar,
        artifacts_calls,
        artifacts_contacts,
        artifacts_locations,
        artifacts_notes,
        artifacts_photos,
        artifacts_safari,
        artifacts_voicemail,
    )

    decrypted = tmp_path / "decrypted"
    artifact_files = build_all(decrypted)
    backup_id = "ART-1"

    async with async_session_factory() as session:
        session.add(
            Backup(ios_identifier=backup_id, path=str(tmp_path / "src"), display_name="t", is_encrypted=True)
        )
        await session.commit()

    await _index_backup_job(backup_id, str(decrypted), artifact_files)

    # Endpoints require the backup to be decrypted.
    async with async_session_factory() as session:
        backup = await session.scalar(select(Backup).where(Backup.ios_identifier == backup_id))
        backup.decryption_status = DecryptionStatus.DECRYPTED
        backup.decrypted_path = str(decrypted)
        await session.commit()

    async with async_session_factory() as session:
        registry = _Registry(session)
        photos = await artifacts_photos.list_photos(backup_id, registry=registry, session=session)
        notes = await artifacts_notes.list_notes(backup_id, registry=registry, session=session)
        events = await artifacts_calendar.list_calendar_events(backup_id, registry=registry, session=session)
        contacts = await artifacts_contacts.list_contacts(backup_id, registry=registry, session=session)
        calls = await artifacts_calls.list_calls(backup_id, registry=registry, session=session)
        safari = await artifacts_safari.list_safari_history(backup_id, registry=registry, session=session)
        locations = await artifacts_locations.list_locations(backup_id, registry=registry, session=session)
        voicemail = await artifacts_voicemail.list_voicemail(backup_id, registry=registry, session=session)

    assert {p.media_type for p in photos.items} == {"photo", "video"}
    assert len(notes.items) == 2
    assert len(events.items) == 2
    assert all(e.calendar_name == "Home" for e in events.items)
    assert len(contacts.items) == 1
    assert contacts.items[0].first_name == "Ada"
    assert contacts.items[0].emails == ["ada@example.com"]
    assert contacts.items[0].phones == ["+15550001111"]
    assert len(calls.items) == 2
    assert {c.is_outgoing for c in calls.items} == {True, False}
    assert any(c.display_name == "Ada" for c in calls.items)
    assert len(safari.items) == 3
    assert any(v.url == "https://apple.com" for v in safari.items)
    assert len(locations.items) == 2
    assert any(abs((loc.latitude or 0) - 47.3769) < 0.001 for loc in locations.items)
    assert len(voicemail.items) == 2
    assert any(vm.trashed for vm in voicemail.items)


async def test_endpoints_reject_undecrypted_backup(db, tmp_path):
    from fastapi import HTTPException

    from core.db.models import Backup
    from core.db.session import async_session_factory

    from api.routes import artifacts_photos

    backup_id = "ART-2"
    async with async_session_factory() as session:
        session.add(
            Backup(ios_identifier=backup_id, path=str(tmp_path / "src"), display_name="t", is_encrypted=True)
        )
        await session.commit()

    async with async_session_factory() as session:
        registry = _Registry(session)
        raised = False
        try:
            await artifacts_photos.list_photos(backup_id, registry=registry, session=session)
        except HTTPException as exc:
            raised = True
            assert exc.status_code == 400
        assert raised
