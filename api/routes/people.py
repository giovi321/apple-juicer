"""Contact-centric correlation: group activity across artifacts by person.

This is a read layer over the already-indexed communication artifacts. Each
record's counterparty identifier (a WhatsApp JID, an iMessage handle, a dialled
number, a voicemail sender) is normalized to a single key, so one person's
messages, calls and voicemails collapse into a single view. Contacts supply the
display name where one matches.

Scope note: events are counterparty-authored — incoming WhatsApp/iMessage
messages plus the full call and voicemail log for that identifier. Full
bidirectional threads are a later enhancement.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api import schemas
from api.dependencies import get_backup_registry, get_db_session
from api.routes._common import get_backup_or_404, get_decrypted_backup
from api.security import require_api_token
from core.correlation import identity_key, normalize_identifier
from core.db.artifacts import (
    CallRecord,
    Contact,
    Message,
    MessageConversation,
    Voicemail,
    WhatsAppMessage,
)
from core.services import BackupRegistry

router = APIRouter(prefix="/backups", tags=["people"], dependencies=[Depends(require_api_token)])

# Per-table cap when gathering a person's events for the detail view.
_PER_TYPE = 2000


def _truncate(text: str | None, length: int = 90) -> str | None:
    if not text:
        return None
    return text if len(text) <= length else text[:length] + "…"


def _contact_name(contact: Contact) -> str:
    name = " ".join(p for p in (contact.first_name, contact.last_name) if p).strip()
    return name or contact.company or contact.contact_identifier


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


async def _aggregate(
    session: AsyncSession, backup_id, contacts: dict[str, tuple[str, Contact]]
) -> dict[str, schemas.PersonSummaryModel]:
    agg: dict[str, dict] = {}

    def bump(raw: str | None, name: str | None, ts: datetime | None, field: str) -> None:
        norm = normalize_identifier(raw)
        if not norm:
            return
        key = f"{norm[0]}:{norm[1]}"
        entry = agg.get(key)
        if entry is None:
            entry = agg[key] = {
                "kind": norm[0],
                "identifiers": [],
                "names": [],
                "whatsapp_count": 0,
                "message_count": 0,
                "call_count": 0,
                "voicemail_count": 0,
                "last_activity_at": None,
            }
        entry[field] += 1
        if raw and raw not in entry["identifiers"]:
            entry["identifiers"].append(raw)
        if name and name not in entry["names"]:
            entry["names"].append(name)
        if ts and (entry["last_activity_at"] is None or ts > entry["last_activity_at"]):
            entry["last_activity_at"] = ts

    wa = (
        await session.execute(
            select(WhatsAppMessage.sender, WhatsAppMessage.sender_name, WhatsAppMessage.sent_at).where(
                WhatsAppMessage.backup_id == backup_id,
                WhatsAppMessage.is_from_me.is_(False),
                WhatsAppMessage.sender.is_not(None),
            )
        )
    ).all()
    for sender, sender_name, ts in wa:
        bump(sender, sender_name, ts, "whatsapp_count")

    msgs = (
        await session.execute(
            select(Message.sender, MessageConversation.display_name, Message.sent_at)
            .join(MessageConversation, Message.conversation_id == MessageConversation.id)
            .where(
                Message.backup_id == backup_id,
                Message.is_from_me.is_(False),
                Message.sender.is_not(None),
            )
        )
    ).all()
    for sender, conv_name, ts in msgs:
        bump(sender, conv_name, ts, "message_count")

    calls = (
        await session.execute(
            select(CallRecord.address, CallRecord.display_name, CallRecord.occurred_at).where(
                CallRecord.backup_id == backup_id, CallRecord.address.is_not(None)
            )
        )
    ).all()
    for address, name, ts in calls:
        bump(address, name, ts, "call_count")

    vms = (
        await session.execute(
            select(Voicemail.sender, Voicemail.received_at).where(
                Voicemail.backup_id == backup_id, Voicemail.sender.is_not(None)
            )
        )
    ).all()
    for sender, ts in vms:
        bump(sender, None, ts, "voicemail_count")

    summaries: dict[str, schemas.PersonSummaryModel] = {}
    for key, entry in agg.items():
        contact_name = contacts.get(key, (None, None))[0]
        display = (
            contact_name
            or (entry["names"][0] if entry["names"] else None)
            or (entry["identifiers"][0] if entry["identifiers"] else key)
        )
        total = entry["whatsapp_count"] + entry["message_count"] + entry["call_count"] + entry["voicemail_count"]
        summaries[key] = schemas.PersonSummaryModel(
            key=key,
            kind=entry["kind"],
            display_name=display,
            is_contact=key in contacts,
            identifiers=entry["identifiers"],
            whatsapp_count=entry["whatsapp_count"],
            message_count=entry["message_count"],
            call_count=entry["call_count"],
            voicemail_count=entry["voicemail_count"],
            total_events=total,
            last_activity_at=entry["last_activity_at"],
        )
    return summaries


async def _events_for_key(session: AsyncSession, backup_id, key: str) -> list[schemas.TimelineEventModel]:
    events: list[schemas.TimelineEventModel] = []

    wa = (
        await session.execute(
            select(WhatsAppMessage.sender, WhatsAppMessage.body, WhatsAppMessage.sent_at)
            .where(
                WhatsAppMessage.backup_id == backup_id,
                WhatsAppMessage.is_from_me.is_(False),
                WhatsAppMessage.sender.is_not(None),
            )
            .limit(_PER_TYPE)
        )
    ).all()
    for sender, body, ts in wa:
        if ts is not None and identity_key(sender) == key:
            events.append(
                schemas.TimelineEventModel(
                    timestamp=ts, artifact_type="whatsapp_message", title=_truncate(body) or "(media)", subtitle="WhatsApp"
                )
            )

    msgs = (
        await session.execute(
            select(Message.sender, Message.text, Message.sent_at)
            .where(
                Message.backup_id == backup_id,
                Message.is_from_me.is_(False),
                Message.sender.is_not(None),
            )
            .limit(_PER_TYPE)
        )
    ).all()
    for sender, text, ts in msgs:
        if ts is not None and identity_key(sender) == key:
            events.append(
                schemas.TimelineEventModel(
                    timestamp=ts, artifact_type="message", title=_truncate(text) or "(attachment)", subtitle="iMessage / SMS"
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
            .where(CallRecord.backup_id == backup_id, CallRecord.address.is_not(None))
            .limit(_PER_TYPE)
        )
    ).all()
    for address, name, ts, is_outgoing, answered, duration in calls:
        if ts is not None and identity_key(address) == key:
            direction = "outgoing" if is_outgoing else "answered" if answered else "missed"
            mins = f" · {duration}s" if duration else ""
            events.append(
                schemas.TimelineEventModel(
                    timestamp=ts, artifact_type="call", title=name or address or "Call", subtitle=f"Call · {direction}{mins}"
                )
            )

    vms = (
        await session.execute(
            select(Voicemail.sender, Voicemail.received_at, Voicemail.duration_seconds)
            .where(Voicemail.backup_id == backup_id, Voicemail.sender.is_not(None))
            .limit(_PER_TYPE)
        )
    ).all()
    for sender, ts, duration in vms:
        if ts is not None and identity_key(sender) == key:
            mins = f" · {duration}s" if duration else ""
            events.append(
                schemas.TimelineEventModel(
                    timestamp=ts, artifact_type="voicemail", title="Voicemail", subtitle=f"Voicemail{mins}"
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
    summaries = await _aggregate(session, db_backup.id, contacts)
    items = sorted(summaries.values(), key=_sort_key, reverse=True)
    return schemas.PersonListResponse(items=items)


@router.get("/{backup_id}/people/{key}", response_model=schemas.PersonDetailResponse)
async def get_person(
    backup_id: str,
    key: str,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    """One person's contact card plus their merged activity across artifacts."""
    await get_decrypted_backup(backup_id, registry)
    db_backup = await get_backup_or_404(backup_id, session)
    contacts = await _contacts_by_key(session, db_backup.id)
    summaries = await _aggregate(session, db_backup.id, contacts)
    person = summaries.get(key)
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

    events = await _events_for_key(session, db_backup.id, key)
    return schemas.PersonDetailResponse(person=person, contact=contact_model, events=events)
