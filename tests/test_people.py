"""Cross-artifact people correlation.

The same person appears as a WhatsApp JID, an iMessage handle, a dialled number
and a voicemail sender; the People endpoints collapse those into one entity and
resolve the name from Contacts.
"""

from __future__ import annotations

import sqlite3

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

    # Ada (+15550001111) shows up via her WhatsApp thread, a call, and a
    # voicemail, and resolves to the contact name. The WhatsApp count is the
    # whole 1:1 thread (incoming "Hi there" + outgoing "See attached") = 2.
    ada = by_key["phone:5550001111"]
    assert ada.is_contact is True
    assert ada.display_name == "Ada Lovelace"
    assert ada.whatsapp_count == 2
    assert ada.call_count == 1
    assert ada.voicemail_count == 1
    assert ada.total_events == 4

    # Grace (+15550002222) has no contact card but still correlates her iMessage
    # thread (both directions = 2), a call, and a voicemail.
    grace = by_key["phone:5550002222"]
    assert grace.is_contact is False
    assert grace.display_name == "Grace"
    assert grace.message_count == 2
    assert grace.call_count == 1
    assert grace.voicemail_count == 1


async def test_person_detail_returns_contact_card_and_bidirectional_thread(db, tmp_path):
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

    # The WhatsApp thread now shows BOTH directions: the incoming "Hi there" and
    # the outgoing "See attached" reply (which has a null sender).
    wa = [e for e in detail.events if e.artifact_type == "whatsapp_message"]
    bodies = {e.title for e in wa}
    assert "Hi there" in bodies
    assert "See attached" in bodies
    assert {e.is_from_me for e in wa} == {True, False}

    # The detail exposes the WhatsApp thread guid for deep-linking.
    assert detail.whatsapp_chat_guid is not None
    assert detail.conversation_guid is None  # Ada has no iMessage thread

    timestamps = [e.timestamp for e in detail.events]
    assert timestamps == sorted(timestamps, reverse=True)


async def test_person_detail_includes_bidirectional_imessage_thread(db, tmp_path):
    from core.db.session import async_session_factory

    from api.routes import people

    backup_id = await _indexed_backup(tmp_path)

    async with async_session_factory() as session:
        registry = _Registry(session)
        detail = await people.get_person(backup_id, "phone:5550002222", registry=registry, session=session)

    assert detail.contact is None  # Grace is not in the address book

    msgs = [e for e in detail.events if e.artifact_type == "message"]
    bodies = {e.title for e in msgs}
    assert "Hello from Grace" in bodies  # incoming
    assert "Photo attached" in bodies  # outgoing reply (null sender)
    assert {e.is_from_me for e in msgs} == {True, False}

    # The iMessage conversation guid is the raw chat guid, ready for deep-linking.
    assert detail.conversation_guid == "iMessage;-;+15550002222"
    assert detail.whatsapp_chat_guid is None


async def test_message_person_key_round_trips_to_people_key(db, tmp_path):
    """The clickable sender's person_key must match the key the People view uses,
    or the reverse deep-link would 404."""
    from core.db.artifacts import Message, WhatsAppChat
    from core.db.session import async_session_factory

    from api.routes import people

    backup_id = await _indexed_backup(tmp_path)

    async with async_session_factory() as session:
        registry = _Registry(session)
        result = await people.list_people(backup_id, registry=registry, session=session)
        keys = {p.key for p in result.items}

        # WhatsApp serializer keys a message off identity_key(chat_guid).
        chat = await session.scalar(select(WhatsAppChat))
        assert identity_key(chat.chat_guid) in keys

        # iMessage serializer keys an incoming message off identity_key(sender).
        msg = await session.scalar(
            select(Message).where(Message.is_from_me.is_(False), Message.sender.is_not(None))
        )
        assert identity_key(msg.sender) in keys


# --- Self-contained fixtures for group exclusion + multi-channel merge. These
# build their own DBs (not build_all) so the shared fixtures stay untouched. ---


def _whatsapp_mixed_db(path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE ZWACHATSESSION (
            Z_PK INTEGER PRIMARY KEY, ZCONTACTJID TEXT, ZPARTNERNAME TEXT,
            ZPARTICIPANTSCOUNT INTEGER, ZLASTMESSAGEDATE REAL, ZISARCHIVED INTEGER
        );
        CREATE TABLE ZWAMESSAGE (
            Z_PK INTEGER PRIMARY KEY, ZCHATSESSION INTEGER, ZMESSAGEID TEXT, ZMESSAGEDATE REAL,
            ZMESSAGETYPE INTEGER, ZTEXT TEXT, ZISFROMME INTEGER, ZFROMJID TEXT, ZISREAD INTEGER
        );
        CREATE TABLE ZWAMEDIAITEM (
            Z_PK INTEGER PRIMARY KEY, ZMESSAGE INTEGER, ZFILEHASH TEXT, ZMEDIALOCALPATH TEXT,
            ZMEDIAMIMETYPE TEXT, ZMEDIAFILESIZE INTEGER
        );
        -- 1:1 chat with Carol (both directions)
        INSERT INTO ZWACHATSESSION VALUES (1, '15551112222@s.whatsapp.net', 'Carol', 2, 700000100.0, 0);
        INSERT INTO ZWAMESSAGE VALUES (1, 1, 'w1', 700000000.0, 0, 'hi carol', 0, '15551112222@s.whatsapp.net', 1);
        INSERT INTO ZWAMESSAGE VALUES (2, 1, 'w2', 700000100.0, 0, 'reply', 1, NULL, 1);
        -- group chat — a member's message must NOT surface as a person
        INSERT INTO ZWACHATSESSION VALUES (2, '120363001@g.us', 'Group', 3, 700000200.0, 0);
        INSERT INTO ZWAMESSAGE VALUES (3, 2, 'w3', 700000200.0, 0, 'group msg', 0, '15559998888@s.whatsapp.net', 1);
        """
    )
    conn.commit()
    conn.close()


def _messages_mixed_db(path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE handle (ROWID INTEGER PRIMARY KEY, id TEXT);
        CREATE TABLE chat (
            ROWID INTEGER PRIMARY KEY, guid TEXT, service_name TEXT, display_name TEXT,
            last_read_message_timestamp INTEGER
        );
        CREATE TABLE chat_handle_join (chat_id INTEGER, handle_id INTEGER);
        CREATE TABLE message (
            ROWID INTEGER PRIMARY KEY, guid TEXT, date INTEGER, service TEXT, text TEXT,
            is_from_me INTEGER, handle_id INTEGER
        );
        CREATE TABLE chat_message_join (chat_id INTEGER, message_id INTEGER);
        CREATE TABLE attachment (
            ROWID INTEGER PRIMARY KEY, guid TEXT, filename TEXT, mime_type TEXT,
            total_bytes INTEGER, transfer_name TEXT
        );
        CREATE TABLE message_attachment_join (attachment_id INTEGER, message_id INTEGER);

        INSERT INTO handle VALUES (1, '+15551112222');
        INSERT INTO handle VALUES (2, '+15557776666');
        INSERT INTO handle VALUES (3, '+15555554444');
        -- 1:1 with Carol (same number as her WhatsApp chat -> merges into one person)
        INSERT INTO chat VALUES (1, 'iMessage;-;+15551112222', 'iMessage', 'Carol', 600000000000000000);
        INSERT INTO chat_handle_join VALUES (1, 1);
        INSERT INTO message VALUES (1, 'i1', 600000000000000000, 'iMessage', 'hi from carol', 0, 1);
        INSERT INTO message VALUES (2, 'i2', 600000000100000000, 'iMessage', 'imessage reply', 1, NULL);
        INSERT INTO chat_message_join VALUES (1, 1);
        INSERT INTO chat_message_join VALUES (1, 2);
        -- group conversation (two handles) — members must NOT surface as people
        INSERT INTO chat VALUES (2, 'iMessage;-;group', 'iMessage', 'Group', 600000000000000000);
        INSERT INTO chat_handle_join VALUES (2, 2);
        INSERT INTO chat_handle_join VALUES (2, 3);
        INSERT INTO message VALUES (3, 'i3', 600000000200000000, 'iMessage', 'group hi', 0, 2);
        INSERT INTO chat_message_join VALUES (2, 3);
        """
    )
    conn.commit()
    conn.close()


async def _indexed_mixed(tmp_path):
    from core.db.models import Backup, DecryptionStatus
    from core.db.session import async_session_factory
    from worker.tasks import _index_backup_job

    decrypted = tmp_path / "decrypted"
    decrypted.mkdir(parents=True, exist_ok=True)
    wa = decrypted / "ChatStorage.sqlite"
    msg = decrypted / "chat.db"
    _whatsapp_mixed_db(wa)
    _messages_mixed_db(msg)
    artifact_files = {"whatsapp": str(wa), "messages": str(msg)}
    backup_id = "PPL-MIX"

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


async def test_groups_excluded_and_multichannel_person_merges(db, tmp_path):
    from core.db.session import async_session_factory

    from api.routes import people

    backup_id = await _indexed_mixed(tmp_path)

    async with async_session_factory() as session:
        registry = _Registry(session)
        result = await people.list_people(backup_id, registry=registry, session=session)
    by_key = {p.key: p for p in result.items}

    # Carol is reachable via BOTH a 1:1 WhatsApp chat and a 1:1 iMessage thread on
    # the same number — they merge into one person with both counts.
    carol = by_key["phone:5551112222"]
    assert carol.whatsapp_count == 2
    assert carol.message_count == 2

    # Group participants must NOT surface as people.
    assert "phone:5559998888" not in by_key  # WhatsApp group member
    assert "phone:5557776666" not in by_key  # iMessage group member
    assert "phone:5555554444" not in by_key
    assert "phone:120363001" not in by_key  # the WhatsApp group itself

    async with async_session_factory() as session:
        registry = _Registry(session)
        detail = await people.get_person(backup_id, "phone:5551112222", registry=registry, session=session)

    # Both threads are deep-linkable and both channels' messages appear.
    assert detail.whatsapp_chat_guid is not None
    assert detail.conversation_guid is not None
    assert {"whatsapp_message", "message"} <= {e.artifact_type for e in detail.events}
