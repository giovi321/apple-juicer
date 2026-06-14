from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api import schemas
from api.dependencies import get_backup_registry, get_db_session
from api.routes._common import get_backup_or_404, get_decrypted_backup
from api.security import require_api_token
from core.db.artifacts import SafariVisit
from core.services import BackupRegistry

router = APIRouter(prefix="/backups", tags=["safari"], dependencies=[Depends(require_api_token)])


def _serialize(visit: SafariVisit) -> schemas.SafariVisitModel:
    return schemas.SafariVisitModel(
        visit_identifier=visit.visit_identifier,
        url=visit.url,
        title=visit.title,
        visited_at=visit.visited_at,
        visit_count=visit.visit_count,
    )


@router.get("/{backup_id}/artifacts/safari", response_model=schemas.SafariVisitListResponse)
async def list_safari_history(
    backup_id: str,
    limit: int = 1000,
    offset: int = 0,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    await get_decrypted_backup(backup_id, registry)
    db_backup = await get_backup_or_404(backup_id, session)
    result = await session.scalars(
        select(SafariVisit)
        .where(SafariVisit.backup_id == db_backup.id)
        .order_by(SafariVisit.visited_at.desc().nullslast())
        .limit(limit)
        .offset(offset)
    )
    return schemas.SafariVisitListResponse(items=[_serialize(visit) for visit in result])
