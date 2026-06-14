from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api import schemas
from api.dependencies import get_backup_registry, get_db_session
from api.routes._common import get_backup_or_404, get_decrypted_backup
from api.security import require_api_token
from core.db.artifacts import LocationPoint
from core.services import BackupRegistry

router = APIRouter(prefix="/backups", tags=["locations"], dependencies=[Depends(require_api_token)])


def _serialize(point: LocationPoint) -> schemas.LocationModel:
    return schemas.LocationModel(
        location_identifier=point.location_identifier,
        latitude=point.latitude,
        longitude=point.longitude,
        altitude=point.altitude,
        speed=point.speed,
        horizontal_accuracy=point.horizontal_accuracy,
        recorded_at=point.recorded_at,
    )


@router.get("/{backup_id}/artifacts/locations", response_model=schemas.LocationListResponse)
async def list_locations(
    backup_id: str,
    limit: int = 2000,
    offset: int = 0,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    await get_decrypted_backup(backup_id, registry)
    db_backup = await get_backup_or_404(backup_id, session)
    result = await session.scalars(
        select(LocationPoint)
        .where(LocationPoint.backup_id == db_backup.id)
        .order_by(LocationPoint.recorded_at.desc().nullslast())
        .limit(limit)
        .offset(offset)
    )
    return schemas.LocationListResponse(items=[_serialize(point) for point in result])
