"""Map endpoint: a single stream of geo points to plot.

Unions significant-location points with geotagged photos into one flat list of
{kind, latitude, longitude, label, timestamp}. Both sources are filtered to
rows that actually carry coordinates — for photos that means presence of
latitude/longitude, not media type, so geotagged videos are included too.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api import schemas
from api.dependencies import get_backup_registry, get_db_session
from api.routes._common import get_backup_or_404, get_decrypted_backup
from api.security import require_api_token
from core.db.artifacts import LocationPoint, PhotoAsset
from core.services import BackupRegistry

router = APIRouter(prefix="/backups", tags=["map"], dependencies=[Depends(require_api_token)])

# Cap the number of plotted points; the UI notes when it is hit.
_MAX_POINTS = 5000


@router.get("/{backup_id}/map", response_model=schemas.MapResponse)
async def backup_map(
    backup_id: str,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    """Significant locations + geotagged photos as a single set of map points."""
    await get_decrypted_backup(backup_id, registry)
    db_backup = await get_backup_or_404(backup_id, session)
    bid = db_backup.id

    loc_geo = (
        LocationPoint.backup_id == bid,
        LocationPoint.latitude.is_not(None),
        LocationPoint.longitude.is_not(None),
    )
    photo_geo = (
        PhotoAsset.backup_id == bid,
        PhotoAsset.latitude.is_not(None),
        PhotoAsset.longitude.is_not(None),
    )

    # Exact totals without materializing every row.
    total = (await session.scalar(select(func.count()).select_from(LocationPoint).where(*loc_geo))) or 0
    total += (await session.scalar(select(func.count()).select_from(PhotoAsset).where(*photo_geo))) or 0

    points: list[schemas.MapPointModel] = []

    # Fetch at most _MAX_POINTS per source (most recent first), then cap the
    # merged set, so memory stays bounded regardless of backup size.
    locations = await session.scalars(
        select(LocationPoint).where(*loc_geo).order_by(LocationPoint.recorded_at.desc().nullslast()).limit(_MAX_POINTS)
    )
    for loc in locations:
        points.append(
            schemas.MapPointModel(
                kind="location",
                latitude=loc.latitude,
                longitude=loc.longitude,
                label="Significant location",
                timestamp=loc.recorded_at,
            )
        )

    photos = await session.scalars(
        select(PhotoAsset).where(*photo_geo).order_by(PhotoAsset.taken_at.desc().nullslast()).limit(_MAX_POINTS)
    )
    for photo in photos:
        points.append(
            schemas.MapPointModel(
                kind="photo",
                latitude=photo.latitude,
                longitude=photo.longitude,
                label=photo.original_filename or "Photo",
                timestamp=photo.taken_at,
            )
        )

    return schemas.MapResponse(items=points[:_MAX_POINTS], total=total, capped=total > _MAX_POINTS)
