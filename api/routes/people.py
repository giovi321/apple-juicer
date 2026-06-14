"""Contact-centric correlation: group activity across artifacts by person.

A read layer over the indexed communication artifacts. Each person is keyed by a
normalized identifier — a WhatsApp JID, an iMessage handle, a dialled number, and
a voicemail sender all collapse to one key. For WhatsApp and iMessage the
person's full 1:1 thread is returned in both directions (from-me replies
included), so matching pivots on the thread container rather than the per-message
sender, which is null on outgoing messages. Calls and voicemails are matched by
their counterparty number. Contacts supply the display name.

Group chats are excluded from per-person threads — a person there is one of many
participants — detected by WhatsApp participant count / `@g.us` guid and by
iMessage handle count.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api import schemas
from api.dependencies import get_backup_registry, get_db_session
from api.routes._common import get_backup_or_404, get_decrypted_backup
from api.security import require_api_token
from core.correlation import identity_key
from core.db.artifacts import (
    CallRecord,
    Contact,
    Message,
    MessageConversation,
    Voicemail,
    WhatsAppChat,
    WhatsAppMessage,
)
from core.services import BackupRegistry

router = APIRouter(prefix="/backups", tags=["people"], dependencies=[Depends(require_api_token)])

# Per-table / per-thread cap when gathering a person's events.
_PER_TYPE = 2000


def _truncate(text: str | None, length: int = 90) -> str | None:
    if not text:
        return None
    return text if len(text) <= length else text[:length] + "…"


def _later(a: datetime | None, b: datetime | None) -> datetime | None:
    if a is None:
        return b
    if b is None:
        return a
    return a if a > b else b


def _contact_name(contact: Contact) -> str:
    name = " ".join(p for p in (contact.first_name, contact.last_name) if p).strip()
    return name or contact.company or contact.contact_identifier


def _is_one_to_one_chat(chat: WhatsAppChat) -> bool:
    """A WhatsApp chat is 1:1 when it isn't a group: not a @g.us guid and at
    most two participants. ``identity_key`` alone can't tell a group apart,
    because a group JID still normalizes to a phone-like key."""
    guid = chat.chat_guid or ""
    if "g.us" in guid:  # group JID marker (e.g. ...@g.us)
        return False
    return chat.participant_count is None or chat.participant_count <= 2


async def _contacts_by_key(session: AsyncSession, backup_id) -> dict[str, tuple[str, Contact]]:
    """Map each normalized phone/email a contact owns to (name, contact)."""
    mapping: dict[str, tuple[str, Contact]] = {}
    contacts = await session.scalars(select(Contact).where(Contact.backup_id == backup_id))
    for contact in contacts:
        name = _contact_name(contact)
        for raw in list(contact.phones or []) + list(contact.emails or []):
            key = identity_key(raw)
            if key:
                mapping.setdefault(key, (name, contact))
    return mapping


class _Person:
    """Per-key accumulator while scanning a backup."""

    __slots__ = (
        "key",
        "kind",
        "identifiers",
        "names",
        "whatsapp_count",
        "message_count",
        "call_count",
        "voicemail_count",
        "last_at",
        "wa_chats",
        "imsg_convs",
    )

    def __init__(self, key: str) -> None:
        self.key = key
        self.kind = key.split(":", 1)[0]
        self.identifiers: list[str] = []
        self.names: list[str] = []
        self.whatsapp_count = 0
        self.message_count = 0
        self.call_count = 0
        self.voicemail_count = 0
        self.last_at: datetime | None = None
        self.wa_chats: list[tuple] = []  # (chat_id, chat_guid)
        self.imsg_convs: list[tuple] = []  # (conversation_id, conversation_guid)

    def note_identifier(self, raw: str | None) -> None:
        if raw and raw not in self.identifiers:
            self.identifiers.append(raw)

    def note_name(self, name: str | None) -> None:
        if name and name not in self.names:
            self.names.append(name)


async def _build(session: AsyncSession, backup_id) -> dict[str, _Person]:
    people: dict[str, _Person] = {}

    def ensure(key: str) -> _Person:
        person = people.get(key)
        if person is None:
            person = people[key] = _Person(key)
        return person

    # WhatsApp 1:1 chats — the chat_guid is the counterparty JID. Most-recent
    # first so wa_chats[0] is the thread to deep-link to.
    wa_chat_key: dict = {}
    chats = await session.scalars(
        select(WhatsAppChat)
        .where(WhatsAppChat.backup_id == backup_id)
        .order_by(WhatsAppChat.last_message_at.desc().nullslast())
    )
    for chat in chats:
        if not _is_one_to_one_chat(chat):
            continue
        key = identity_key(chat.chat_guid)
        if not key:
            continue
        person = ensure(key)
        person.wa_chats.append((chat.id, chat.chat_guid))
        person.note_identifier(chat.chat_guid)
        person.note_name(chat.title)
        wa_chat_key[chat.id] = key
    if wa_chat_key:
        # Count only timestamped messages, to match the events the detail shows.
        rows = (
            await session.execute(
                select(WhatsAppMessage.chat_id, func.count(), func.max(WhatsAppMessage.sent_at))
                .where(WhatsAppMessage.chat_id.in_(list(wa_chat_key)), WhatsAppMessage.sent_at.is_not(None))
                .group_by(WhatsAppMessage.chat_id)
            )
        ).all()
        for chat_id, count, last in rows:
            person = people[wa_chat_key[chat_id]]
            person.whatsapp_count += count
            person.last_at = _later(person.last_at, last)

    # iMessage 1:1 conversations — keyed by the single participant handle.
    conv_key: dict = {}
    convs = await session.scalars(
        select(MessageConversation)
        .where(MessageConversation.backup_id == backup_id)
        .order_by(MessageConversation.last_message_at.desc().nullslast())
    )
    for conv in convs:
        handles = conv.participant_handles or []
        if len(handles) != 1:
            continue
        key = identity_key(handles[0])
        if not key:
            continue
        person = ensure(key)
        person.imsg_convs.append((conv.id, conv.conversation_guid))
        person.note_identifier(handles[0])
        person.note_name(conv.display_name)
        conv_key[conv.id] = key
    if conv_key:
        rows = (
            await session.execute(
                select(Message.conversation_id, func.count(), func.max(Message.sent_at))
                .where(Message.conversation_id.in_(list(conv_key)), Message.sent_at.is_not(None))
                .group_by(Message.conversation_id)
            )
        ).all()
        for conv_id, count, last in rows:
            person = people[conv_key[conv_id]]
            person.message_count += count
            person.last_at = _later(person.last_at, last)

    # Calls and voicemails — matched by the counterparty number. Only timestamped
    # rows are counted, to match the events the detail returns.
    calls = (
        await session.execute(
            select(CallRecord.address, CallRecord.display_name, CallRecord.occurred_at).where(
                CallRecord.backup_id == backup_id,
                CallRecord.address.is_not(None),
                CallRecord.occurred_at.is_not(None),
            )
        )
    ).all()
    for address, name, ts in calls:
        key = identity_key(address)
        if not key:
            continue
        person = ensure(key)
        person.call_count += 1
        person.note_identifier(address)
        person.note_name(name)
        person.last_at = _later(person.last_at, ts)

    vms = (
        await session.execute(
            select(Voicemail.sender, Voicemail.received_at).where(
                Voicemail.backup_id == backup_id,
                Voicemail.sender.is_not(None),
                Voicemail.received_at.is_not(None),
            )
        )
    ).all()
    for sender, ts in vms:
        key = identity_key(sender)
        if not key:
            continue
        person = ensure(key)
        person.voicemail_count += 1
        person.note_identifier(sender)
        person.last_at = _later(person.last_at, ts)

    return people


def _summary(person: _Person, contacts: dict[str, tuple[str, Contact]]) -> schemas.PersonSummaryModel:
    contact_name = contacts.get(person.key, (None, None))[0]
    display = (
        contact_name
        or (person.names[0] if person.names else None)
        or (person.identifiers[0] if person.identifiers else person.key)
    )
    total = person.whatsapp_count + person.message_count + person.call_count + person.voicemail_count
    return schemas.PersonSummaryModel(
        key=person.key,
        kind=person.kind,
        display_name=display,
        is_contact=person.key in contacts,
        identifiers=person.identifiers,
        whatsapp_count=person.whatsapp_count,
        message_count=person.message_count,
        call_count=person.call_count,
        voicemail_count=person.voicemail_count,
        total_events=total,
        last_activity_at=person.last_at,
    )


async def _events_for_person(session: AsyncSession, backup_id, person: _Person) -> list[schemas.PersonEventModel]:
    events: list[schemas.PersonEventModel] = []

    # Per-thread cap takes the most recent _PER_TYPE timestamped messages.
    for chat_id, _guid in person.wa_chats:
        msgs = await session.scalars(
            select(WhatsAppMessage)
            .where(WhatsAppMessage.chat_id == chat_id, WhatsAppMessage.sent_at.is_not(None))
            .order_by(WhatsAppMessage.sent_at.desc(), WhatsAppMessage.id.desc())
            .limit(_PER_TYPE)
        )
        for m in msgs:
            events.append(
                schemas.PersonEventModel(
                    timestamp=m.sent_at,
                    artifact_type="whatsapp_message",
                    title=_truncate(m.body) or "(media)",
                    subtitle="WhatsApp",
                    is_from_me=m.is_from_me,
                )
            )

    for conv_id, _guid in person.imsg_convs:
        msgs = await session.scalars(
            select(Message)
            .where(Message.conversation_id == conv_id, Message.sent_at.is_not(None))
            .order_by(Message.sent_at.desc(), Message.id.desc())
            .limit(_PER_TYPE)
        )
        for m in msgs:
            events.append(
                schemas.PersonEventModel(
                    timestamp=m.sent_at,
                    artifact_type="message",
                    title=_truncate(m.text) or "(attachment)",
                    subtitle="iMessage / SMS",
                    is_from_me=m.is_from_me,
                )
            )

    calls = (
        await session.execute(
            select(
                CallRecord.address,
                CallRecord.display_name,
                CallRecord.occurred_at,
                CallRecord.is_outgoing,
                CallRecord.answered,
                CallRecord.duration_seconds,
            )
            .where(
                CallRecord.backup_id == backup_id,
                CallRecord.address.is_not(None),
                CallRecord.occurred_at.is_not(None),
            )
        )
    ).all()
    for address, name, ts, is_outgoing, answered, duration in calls:
        if identity_key(address) == person.key:
            direction = "outgoing" if is_outgoing else "answered" if answered else "missed"
            dur = f" · {duration}s" if duration else ""
            events.append(
                schemas.PersonEventModel(
                    timestamp=ts,
                    artifact_type="call",
                    title=name or address or "Call",
                    subtitle=f"Call · {direction}{dur}",
                )
            )

    vms = (
        await session.execute(
            select(Voicemail.sender, Voicemail.received_at, Voicemail.duration_seconds).where(
                Voicemail.backup_id == backup_id,
                Voicemail.sender.is_not(None),
                Voicemail.received_at.is_not(None),
            )
        )
    ).all()
    for sender, ts, duration in vms:
        if identity_key(sender) == person.key:
            dur = f" · {duration}s" if duration else ""
            events.append(
                schemas.PersonEventModel(
                    timestamp=ts, artifact_type="voicemail", title="Voicemail", subtitle=f"Voicemail{dur}"
                )
            )

    events.sort(key=lambda e: e.timestamp, reverse=True)
    return events


def _sort_key(person: schemas.PersonSummaryModel):
    return (person.last_activity_at is not None, person.last_activity_at, person.total_events)


@router.get("/{backup_id}/people", response_model=schemas.PersonListResponse)
async def list_people(
    backup_id: str,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    """People who appear across the communication artifacts, most recent first."""
    await get_decrypted_backup(backup_id, registry)
    db_backup = await get_backup_or_404(backup_id, session)
    contacts = await _contacts_by_key(session, db_backup.id)
    people = await _build(session, db_backup.id)
    items = [_summary(person, contacts) for person in people.values()]
    items.sort(key=_sort_key, reverse=True)
    return schemas.PersonListResponse(items=items)


@router.get("/{backup_id}/people/{key}", response_model=schemas.PersonDetailResponse)
async def get_person(
    backup_id: str,
    key: str,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    """One person's contact card, their full 1:1 threads, and call/voicemail log."""
    await get_decrypted_backup(backup_id, registry)
    db_backup = await get_backup_or_404(backup_id, session)
    contacts = await _contacts_by_key(session, db_backup.id)
    people = await _build(session, db_backup.id)
    person = people.get(key)
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found.")

    contact_model = None
    if key in contacts:
        contact = contacts[key][1]
        contact_model = schemas.ContactModel(
            contact_identifier=contact.contact_identifier,
            first_name=contact.first_name,
            last_name=contact.last_name,
            company=contact.company,
            emails=list(contact.emails or []),
            phones=list(contact.phones or []),
            avatar_file_id=contact.avatar_file_id,
        )

    events = await _events_for_person(session, db_backup.id, person)
    return schemas.PersonDetailResponse(
        person=_summary(person, contacts),
        contact=contact_model,
        events=events,
        whatsapp_chat_guid=person.wa_chats[0][1] if person.wa_chats else None,
        conversation_guid=person.imsg_convs[0][1] if person.imsg_convs else None,
    )
