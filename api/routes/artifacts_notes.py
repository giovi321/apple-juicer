from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api import schemas
from api.dependencies import get_backup_registry, get_db_session
from api.routes._common import get_backup_or_404, get_decrypted_backup
from api.security import require_api_token
from core.db.artifacts import Note
from core.services import BackupRegistry

router = APIRouter(prefix="/backups", tags=["notes"], dependencies=[Depends(require_api_token)])


def _serialize(note: Note) -> schemas.NoteModel:
    return schemas.NoteModel(
        note_identifier=note.note_identifier,
        title=note.title,
        body=note.body,
        folder=note.folder,
        created_at=note.created_at,
        last_modified_at=note.last_modified_at,
    )


@router.get("/{backup_id}/artifacts/notes", response_model=schemas.NoteListResponse)
async def list_notes(
    backup_id: str,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    await get_decrypted_backup(backup_id, registry)
    db_backup = await get_backup_or_404(backup_id, session)
    result = await session.scalars(
        select(Note)
        .where(Note.backup_id == db_backup.id)
        .order_by(Note.last_modified_at.desc().nullslast(), Note.title)
    )
    return schemas.NoteListResponse(items=[_serialize(note) for note in result])
