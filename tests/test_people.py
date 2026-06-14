"""Cross-artifact people correlation.

The same person appears as a WhatsApp JID, an iMessage handle, a dialled number
and a voicemail sender; the People endpoints collapse those into one entity and
resolve the name from Contacts.
"""

from __future__ import annotations

from sqlalchemy import select

from fixtures import build_all

from core.correlation import identity_key, normalize_identifier


def test_normalize_collapses_identifier_shapes():
    # A WhatsApp JID, an E.164 number, and a bare number all reduce to one key.
    assert normalize_identifier("15550001111@s.whatsapp.net") == ("phone", "5550001111")
    assert normalize_identifier("+15550001111") == ("phone", "5550001111")
    assert normalize_identifier("5550001111") == ("phone", "5550001111")
    assert normalize_identifier('Optional("+15550001111")') == ("phone", "5550001111")
    assert identity_key("+15550001111") == "phone:5550001111"


def test_normalize_emails_and_empties():
    assert normalize_identifier("ada@example.com") == ("email", "ada@example.com")
    assert normalize_identifier("ADA@Example.com") == ("email", "ada@example.com")
    assert normalize_identifier(None) is None
    assert normalize_identifier("") is None


class _Registry:
    def __init__(self, session):
        self.session = session

    async def get_backup(self, identifier: str):
        from core.db.models import Backup

        return await self.session.scalar(select(Backup).where(Backup.ios_identifier == identifier))


async def _indexed_backup(tmp_path):
    from core.db.models import Backup, DecryptionStatus
    from core.db.session import async_session_factory
    from worker.tasks import _index_backup_job

    decrypted = tmp_path / "decrypted"
    artifact_files = build_all(decrypted)
    backup_id = "PPL-1"

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


async def test_people_list_aggregates_across_artifacts(db, tmp_path):
    from core.db.session import async_session_factory

    from api.routes import people

    backup_id = await _indexed_backup(tmp_path)

    async with async_session_factory() as session:
        registry = _Registry(session)
        result = await people.list_people(backup_id, registry=registry, session=session)

    by_key = {p.key: p for p in result.items}

    # Ada (+15550001111) shows up via WhatsApp, a call, and a voicemail, and
    # resolves to the contact name.
    ada = by_key["phone:5550001111"]
    assert ada.is_contact is True
    assert ada.display_name == "Ada Lovelace"
    assert ada.whatsapp_count == 1
    assert ada.call_count == 1
    assert ada.voicemail_count == 1
    assert ada.total_events == 3

    # Grace (+15550002222) has no contact card but still correlates an iMessage,
    # a call, and a voicemail.
    grace = by_key["phone:5550002222"]
    assert grace.is_contact is False
    assert grace.message_count == 1
    assert grace.call_count == 1
    assert grace.voicemail_count == 1


async def test_person_detail_returns_contact_card_and_events(db, tmp_path):
    from core.db.session import async_session_factory

    from api.routes import people

    backup_id = await _indexed_backup(tmp_path)

    async with async_session_factory() as session:
        registry = _Registry(session)
        detail = await people.get_person(backup_id, "phone:5550001111", registry=registry, session=session)

    assert detail.contact is not None
    assert detail.contact.first_name == "Ada"
    assert "+15550001111" in detail.contact.phones

    types = {e.artifact_type for e in detail.events}
    assert {"whatsapp_message", "call", "voicemail"} <= types
    timestamps = [e.timestamp for e in detail.events]
    assert timestamps == sorted(timestamps, reverse=True)
