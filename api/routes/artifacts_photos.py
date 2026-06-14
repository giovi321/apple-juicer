from __future__ import annotations

import io
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api import schemas
from api.dependencies import get_backup_registry, get_db_session, get_unlock_manager
from api.routes._common import (
    download_attachment_response,
    extract_attachment,
    get_backup_or_404,
    get_decrypted_backup,
    resolve_filesystem,
)
from api.security import require_api_token
from core.db.artifacts import PhotoAsset
from core.services import BackupRegistry, UnlockManager

router = APIRouter(prefix="/backups", tags=["photos"], dependencies=[Depends(require_api_token)])

PHOTO_FALLBACK_DOMAINS = ["CameraRollDomain", "MediaDomain"]


def _thumbnail_jpeg(path: Path, size: int) -> bytes | None:
    """Render a downscaled JPEG thumbnail, or None if the file isn't an image."""
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(path) as img:
            img = img.convert("RGB")
            img.thumbnail((size, size))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=72)
            return buffer.getvalue()
    except (UnidentifiedImageError, OSError, ValueError):
        return None


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


@router.get("/{backup_id}/artifacts/photos/file")
async def download_photo(
    backup_id: str,
    relative_path: str,
    thumb: int | None = None,
    registry: BackupRegistry = Depends(get_backup_registry),
    unlock_mgr: UnlockManager = Depends(get_unlock_manager),
    session_token: str | None = Header(None, alias="X-Backup-Session"),
):
    """Stream a photo's image file (or a downscaled JPEG thumbnail when ?thumb=N)."""
    backup = await get_decrypted_backup(backup_id, registry)
    fs = resolve_filesystem(backup, backup_id, session_token, unlock_mgr)

    if thumb:
        size = max(32, min(thumb, 1024))
        payload_path, sandbox_dir = extract_attachment(
            fs,
            relative_path,
            fallback_domains=PHOTO_FALLBACK_DOMAINS,
            strip_tilde=False,
            session_present=bool(session_token),
            label="photo",
        )
        try:
            data = _thumbnail_jpeg(payload_path, size)
        finally:
            shutil.rmtree(sandbox_dir, ignore_errors=True)
        if data is None:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Not an image.")
        return Response(content=data, media_type="image/jpeg")

    return download_attachment_response(
        fs,
        relative_path,
        fallback_domains=PHOTO_FALLBACK_DOMAINS,
        strip_tilde=False,
        session_present=bool(session_token),
        label="photo",
    )
