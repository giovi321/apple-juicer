from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api import schemas
from api.dependencies import get_backup_registry, get_db_session
from api.routes._common import get_backup_or_404, get_decrypted_backup
from api.security import require_api_token
from core.db.artifacts import PhotoAsset
from core.services import BackupRegistry

router = APIRouter(prefix="/backups", tags=["photos"], dependencies=[Depends(require_api_token)])


def _serialize(photo: PhotoAsset) -> schemas.PhotoAssetModel:
    try:
        metadata = dict(photo.metadata) if photo.metadata else {}
    except (TypeError, ValueError):
        metadata = {}
    return schemas.PhotoAssetModel(
        asset_id=photo.asset_id,
        original_filename=photo.original_filename,
        relative_path=photo.relative_path,
        file_id=photo.file_id,
        taken_at=photo.taken_at,
        timezone_offset_minutes=photo.timezone_offset_minutes,
        width=photo.width,
        height=photo.height,
        media_type=photo.media_type,
        metadata=metadata,
    )


@router.get("/{backup_id}/artifacts/photos", response_model=schemas.PhotoListResponse)
async def list_photos(
    backup_id: str,
    limit: int = 1000,
    offset: int = 0,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    await get_decrypted_backup(backup_id, registry)
    db_backup = await get_backup_or_404(backup_id, session)
    result = await session.scalars(
        select(PhotoAsset)
        .where(PhotoAsset.backup_id == db_backup.id)
        .order_by(PhotoAsset.taken_at.desc().nullslast())
        .limit(limit)
        .offset(offset)
    )
    return schemas.PhotoListResponse(items=[_serialize(photo) for photo in result])
