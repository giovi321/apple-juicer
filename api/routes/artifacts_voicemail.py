from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api import schemas
from api.dependencies import get_backup_registry, get_db_session
from api.routes._common import get_backup_or_404, get_decrypted_backup
from api.security import require_api_token
from core.db.artifacts import Voicemail
from core.services import BackupRegistry

router = APIRouter(prefix="/backups", tags=["voicemail"], dependencies=[Depends(require_api_token)])


def _serialize(vm: Voicemail) -> schemas.VoicemailModel:
    return schemas.VoicemailModel(
        voicemail_identifier=vm.voicemail_identifier,
        sender=vm.sender,
        received_at=vm.received_at,
        duration_seconds=vm.duration_seconds,
        trashed=vm.trashed,
    )


@router.get("/{backup_id}/artifacts/voicemail", response_model=schemas.VoicemailListResponse)
async def list_voicemail(
    backup_id: str,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    await get_decrypted_backup(backup_id, registry)
    db_backup = await get_backup_or_404(backup_id, session)
    result = await session.scalars(
        select(Voicemail)
        .where(Voicemail.backup_id == db_backup.id)
        .order_by(Voicemail.received_at.desc().nullslast())
    )
    return schemas.VoicemailListResponse(items=[_serialize(vm) for vm in result])
