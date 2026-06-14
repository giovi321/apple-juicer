from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api import schemas
from api.dependencies import get_backup_registry, get_db_session
from api.routes._common import get_backup_or_404, get_decrypted_backup
from api.security import require_api_token
from core.db.artifacts import (
    CalendarEvent,
    CallRecord,
    LocationPoint,
    Message,
    Note,
    PhotoAsset,
    SafariVisit,
    Voicemail,
    WhatsAppMessage,
)
from core.services import BackupRegistry

router = APIRouter(prefix="/backups", tags=["timeline"], dependencies=[Depends(require_api_token)])

# Per-type cap when gathering candidates before the global merge/sort.
_PER_TYPE = 400


def _truncate(text: str | None, length: int = 90) -> str | None:
    if not text:
        return None
    return text if len(text) <= length else text[:length] + "…"


async def _gather(session, model, ts_column, artifact_type, title_fn, subtitle_fn, backup_id):
    rows = await session.scalars(
        select(model)
        .where(model.backup_id == backup_id, ts_column.is_not(None))
        .order_by(ts_column.desc())
        .limit(_PER_TYPE)
    )
    events: list[schemas.TimelineEventModel] = []
    for row in rows:
        ts = getattr(row, ts_column.key)
        if ts is None:
            continue
        events.append(
            schemas.TimelineEventModel(
                timestamp=ts,
                artifact_type=artifact_type,
                title=title_fn(row),
                subtitle=subtitle_fn(row),
            )
        )
    return events


@router.get("/{backup_id}/timeline", response_model=schemas.TimelineResponse)
async def backup_timeline(
    backup_id: str,
    limit: int = 200,
    offset: int = 0,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    """A merged, chronological view of timestamped events across artifact types."""
    await get_decrypted_backup(backup_id, registry)
    db_backup = await get_backup_or_404(backup_id, session)
    bid = db_backup.id

    events: list[schemas.TimelineEventModel] = []
    events += await _gather(
        session, WhatsAppMessage, WhatsAppMessage.sent_at, "whatsapp_message",
        lambda r: _truncate(r.body) or "(media)",
        lambda r: f"WhatsApp · {r.sender_name or r.sender or ''}".strip(" ·"),
        bid,
    )
    events += await _gather(
        session, Message, Message.sent_at, "message",
        lambda r: _truncate(r.text) or "(attachment)",
        lambda r: f"iMessage · {r.sender or ''}".strip(" ·"),
        bid,
    )
    events += await _gather(
        session, CallRecord, CallRecord.occurred_at, "call",
        lambda r: r.display_name or r.address or "Call",
        lambda r: "Call · " + ("outgoing" if r.is_outgoing else "answered" if r.answered else "missed"),
        bid,
    )
    events += await _gather(
        session, CalendarEvent, CalendarEvent.starts_at, "calendar_event",
        lambda r: r.title or "Event",
        lambda r: "Calendar",
        bid,
    )
    events += await _gather(
        session, PhotoAsset, PhotoAsset.taken_at, "photo",
        lambda r: r.original_filename or "Photo",
        lambda r: f"Photo · {r.media_type or ''}".strip(" ·"),
        bid,
    )
    events += await _gather(
        session, SafariVisit, SafariVisit.visited_at, "safari",
        lambda r: r.title or r.url or "Visit",
        lambda r: "Safari",
        bid,
    )
    events += await _gather(
        session, LocationPoint, LocationPoint.recorded_at, "location",
        lambda r: f"{r.latitude}, {r.longitude}",
        lambda r: "Location",
        bid,
    )
    events += await _gather(
        session, Voicemail, Voicemail.received_at, "voicemail",
        lambda r: r.sender or "Voicemail",
        lambda r: "Voicemail",
        bid,
    )
    events += await _gather(
        session, Note, Note.last_modified_at, "note",
        lambda r: r.title or "Note",
        lambda r: "Note",
        bid,
    )

    events.sort(key=lambda e: e.timestamp, reverse=True)
    return schemas.TimelineResponse(items=events[offset : offset + limit])
