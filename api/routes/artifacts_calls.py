from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api import schemas
from api.dependencies import get_backup_registry, get_db_session
from api.routes._common import get_backup_or_404, get_decrypted_backup
from api.security import require_api_token
from core.db.artifacts import CallRecord
from core.services import BackupRegistry

router = APIRouter(prefix="/backups", tags=["calls"], dependencies=[Depends(require_api_token)])


def _serialize(call: CallRecord) -> schemas.CallModel:
    return schemas.CallModel(
        call_identifier=call.call_identifier,
        address=call.address,
        display_name=call.display_name,
        occurred_at=call.occurred_at,
        duration_seconds=call.duration_seconds,
        is_outgoing=call.is_outgoing,
        answered=call.answered,
        service=call.service,
    )


@router.get("/{backup_id}/artifacts/calls", response_model=schemas.CallListResponse)
async def list_calls(
    backup_id: str,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    await get_decrypted_backup(backup_id, registry)
    db_backup = await get_backup_or_404(backup_id, session)
    result = await session.scalars(
        select(CallRecord)
        .where(CallRecord.backup_id == db_backup.id)
        .order_by(CallRecord.occurred_at.desc().nullslast())
    )
    return schemas.CallListResponse(items=[_serialize(call) for call in result])
