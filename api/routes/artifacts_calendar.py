from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api import schemas
from api.dependencies import get_backup_registry, get_db_session
from api.routes._common import get_backup_or_404, get_decrypted_backup
from api.security import require_api_token
from core.db.artifacts import Calendar, CalendarEvent
from core.services import BackupRegistry

router = APIRouter(prefix="/backups", tags=["calendar"], dependencies=[Depends(require_api_token)])


@router.get("/{backup_id}/artifacts/calendar/events", response_model=schemas.CalendarEventListResponse)
async def list_calendar_events(
    backup_id: str,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    await get_decrypted_backup(backup_id, registry)
    db_backup = await get_backup_or_404(backup_id, session)
    result = await session.execute(
        select(CalendarEvent, Calendar.calendar_identifier, Calendar.name)
        .join(Calendar, Calendar.id == CalendarEvent.calendar_id)
        .where(CalendarEvent.backup_id == db_backup.id)
        .order_by(CalendarEvent.starts_at.desc().nullslast())
    )
    items = [
        schemas.CalendarEventModel(
            event_identifier=event.event_identifier,
            calendar_identifier=calendar_identifier,
            calendar_name=calendar_name,
            title=event.title,
            location=event.location,
            notes=event.notes,
            starts_at=event.starts_at,
            ends_at=event.ends_at,
            is_all_day=event.is_all_day,
        )
        for event, calendar_identifier, calendar_name in result.all()
    ]
    return schemas.CalendarEventListResponse(items=items)
