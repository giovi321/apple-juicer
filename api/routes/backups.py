import inspect
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from api import schemas
from api.dependencies import (
    get_backup_registry,
    get_db_session,
    get_decrypt_orchestrator,
    get_unlock_manager,
)
from api.routes._common import get_decrypted_backup, get_filesystem_from_decrypted
from api.security import require_api_token, require_session_token
from core.artifacts import filename_to_key
from core.config import get_settings
from core.db.models import DecryptionStatus
from core.queue import get_queue
from core.services import (
    BackupRegistry,
    DecryptionError,
    DecryptOrchestrator,
    SessionNotFoundError,
    UnlockError,
    UnlockManager,
)
from worker.tasks import _truncate_artifacts, index_backup_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backups", tags=["backups"], dependencies=[Depends(require_api_token)])
settings = get_settings()
host_display_path = settings.backup_paths.host_display_path or settings.backup_paths.base_path


@router.get("", response_model=schemas.DiscoverResponse)
async def list_backups(registry: BackupRegistry = Depends(get_backup_registry)):
    # First check if database is empty, if so discover backups from filesystem
    backups = await registry.list_backups()
    if not backups:
        await registry.refresh()
        backups = await registry.list_backups()

    payload = [
        schemas.BackupSummaryModel(
            id=backup.ios_identifier,
            display_name=backup.display_name,
            device_name=backup.device_name,
            product_version=backup.product_version,
            is_encrypted=backup.is_encrypted,
            status=backup.status,
            decryption_status=backup.decryption_status,
            last_indexed_at=backup.last_indexed_at,
            decrypted_at=backup.decrypted_at,
            size_bytes=backup.size_bytes,
            last_modified_at=_safe_last_modified(backup.path),
            indexing_progress=backup.indexing_progress,
            indexing_total=backup.indexing_total,
            indexing_artifact=backup.indexing_artifact,
        )
        for backup in backups
    ]
    return schemas.DiscoverResponse(backups=payload, base_directory=host_display_path)


@router.post("/refresh", response_model=schemas.DiscoverResponse)
async def refresh_backups(registry: BackupRegistry = Depends(get_backup_registry)):
    summaries = await registry.refresh()
    payload = [
        schemas.BackupSummaryModel(
            id=summary.backup_id,
            display_name=summary.display_name,
            device_name=summary.device_name,
            product_version=summary.product_version,
            is_encrypted=summary.is_encrypted,
            status=summary.status,
            decryption_status=DecryptionStatus.PENDING,
            last_indexed_at=summary.last_indexed_at,
            size_bytes=summary.size_bytes,
            last_modified_at=summary.last_modified_at,
            indexing_progress=None,
            indexing_total=None,
            indexing_artifact=None,
        )
        for summary in summaries
    ]
    return schemas.DiscoverResponse(backups=payload, base_directory=host_display_path)


def _extract_artifact_databases(decrypted_path: str) -> dict[str, str]:
    """Map present artifact DB files to their artifact keys (registry-driven)."""
    decrypted_dir = Path(decrypted_path)
    artifact_files = {}
    for db_name, artifact_type in filename_to_key().items():
        db_path = decrypted_dir / db_name
        if db_path.exists():
            artifact_files[artifact_type] = str(db_path)
    return artifact_files


def _queue_artifact_indexing(backup_id: str, decrypted_path: str) -> None:
    """Queue artifact indexing job for the decrypted backup using RQ."""
    try:
        artifact_files = _extract_artifact_databases(decrypted_path)
        if not artifact_files:
            logger.info(f"No artifact databases found for backup {backup_id}")
            return

        # RQ runs the enqueued callable synchronously in the worker and never
        # awaits it. Enqueueing a coroutine function (the async _index_backup_job)
        # therefore silently no-ops. Enqueue the sync wrapper and fail loudly if
        # that contract is ever broken.
        if inspect.iscoroutinefunction(index_backup_job):
            raise TypeError("index_backup_job must be a synchronous callable for RQ")

        queue = get_queue()
        queue.enqueue(index_backup_job, backup_id, decrypted_path, artifact_files)
        logger.info(f"Queued artifact indexing job for backup {backup_id} with {len(artifact_files)} artifacts")
    except Exception as exc:
        logger.error(f"Failed to queue artifact indexing for backup {backup_id}: {exc}")


@router.post("/{backup_id}/decrypt", response_model=schemas.DecryptStatusResponse)
async def decrypt_backup(
    backup_id: str,
    body: schemas.DecryptRequest,
    registry: BackupRegistry = Depends(get_backup_registry),
    orchestrator: DecryptOrchestrator = Depends(get_decrypt_orchestrator),
    session: AsyncSession = Depends(get_db_session),
):
    backup = await registry.get_backup(backup_id)
    if not backup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found.")

    backup.decryption_status = DecryptionStatus.DECRYPTING
    backup.decryption_error = None
    await session.flush()

    try:
        decrypted_path = orchestrator.decrypt_backup(backup, body.password)
        backup.decrypted_path = decrypted_path
        backup.decryption_status = DecryptionStatus.DECRYPTED
        backup.decrypted_at = datetime.now(timezone.utc)
    except DecryptionError as exc:
        backup.decryption_status = DecryptionStatus.FAILED
        backup.decryption_error = str(exc)
        await session.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await session.commit()

    # Queue artifact indexing in background
    _queue_artifact_indexing(backup.ios_identifier, decrypted_path)

    return schemas.DecryptStatusResponse(
        backup_id=backup.ios_identifier,
        decryption_status=backup.decryption_status,
        decrypted_at=backup.decrypted_at,
    )


@router.get("/{backup_id}/decrypt-status", response_model=schemas.DecryptStatusResponse)
async def get_decrypt_status(
    backup_id: str,
    registry: BackupRegistry = Depends(get_backup_registry),
):
    backup = await registry.get_backup(backup_id)
    if not backup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found.")

    return schemas.DecryptStatusResponse(
        backup_id=backup.ios_identifier,
        decryption_status=backup.decryption_status,
        decrypted_at=backup.decrypted_at,
        error=backup.decryption_error,
    )


@router.delete("/{backup_id}/decrypted", status_code=status.HTTP_204_NO_CONTENT)
async def delete_decrypted_data(
    backup_id: str,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    backup = await registry.get_backup(backup_id)
    if not backup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found.")

    if backup.decryption_status != DecryptionStatus.DECRYPTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Backup is not decrypted.")

    # Delete decrypted files from filesystem
    if backup.decrypted_path:
        decrypted_path = Path(backup.decrypted_path)
        if decrypted_path.exists():
            try:
                shutil.rmtree(decrypted_path)
                logger.info(f"Deleted decrypted data at {decrypted_path}")
            except Exception as exc:
                logger.error(f"Failed to delete decrypted data: {exc}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to delete decrypted data: {str(exc)}",
                ) from exc

    # Delete indexed artifacts from database
    await _truncate_artifacts(session, backup)

    # Update database
    backup.decryption_status = DecryptionStatus.PENDING
    backup.decrypted_path = None
    backup.decrypted_at = None
    backup.last_indexed_at = None
    await session.commit()

    return None


@router.post("/{backup_id}/unlock", response_model=schemas.UnlockResponse)
async def unlock_backup(
    backup_id: str,
    body: schemas.UnlockRequest,
    registry: BackupRegistry = Depends(get_backup_registry),
    unlock_mgr: UnlockManager = Depends(get_unlock_manager),
):
    backup = await registry.get_backup(backup_id)
    if not backup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found.")
    try:
        result = unlock_mgr.unlock(backup, body.password)
    except UnlockError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await registry.session.commit()
    return schemas.UnlockResponse(session_token=result.token, ttl_seconds=result.ttl_seconds)


@router.post("/{backup_id}/lock")
async def lock_backup(
    backup_id: str,
    session_token: str = Depends(require_session_token),
    unlock_mgr: UnlockManager = Depends(get_unlock_manager),
):
    try:
        unlock_mgr.revoke(session_token)
    except SessionNotFoundError:
        pass
    return {"status": "ok"}


@router.get("/{backup_id}/files", response_model=schemas.FileListResponse)
async def list_files(
    backup_id: str,
    domain: str | None = None,
    path_like: str | None = None,
    limit: int = 100,
    offset: int = 0,
    registry: BackupRegistry = Depends(get_backup_registry),
):
    backup = await get_decrypted_backup(backup_id, registry)
    fs = get_filesystem_from_decrypted(backup)
    items = fs.list_files(domain=domain, path_like=path_like, limit=limit, offset=offset)
    return schemas.FileListResponse(
        items=[
            schemas.ManifestEntryModel(
                file_id=item.file_id,
                domain=item.domain,
                relative_path=item.relative_path,
                size=item.size,
                mtime=item.mtime,
            )
            for item in items
        ],
        limit=limit,
        offset=offset,
    )


@router.get("/{backup_id}/domains", response_model=schemas.DomainListResponse)
async def list_domains(
    backup_id: str,
    registry: BackupRegistry = Depends(get_backup_registry),
):
    backup = await get_decrypted_backup(backup_id, registry)
    fs = get_filesystem_from_decrypted(backup)
    return schemas.DomainListResponse(domains=fs.list_domains())


@router.get("/{backup_id}/file/{file_id}")
async def download_file(
    backup_id: str,
    file_id: str,
    registry: BackupRegistry = Depends(get_backup_registry),
):
    backup = await get_decrypted_backup(backup_id, registry)
    fs = get_filesystem_from_decrypted(backup)
    entry = fs.get_entry_by_file_id(file_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    payload_path, sandbox_dir = fs.extract_to_temp(domain=entry.domain, relative_path=entry.relative_path)
    filename = entry.relative_path.split("/")[-1] or entry.file_id
    background = BackgroundTask(shutil.rmtree, sandbox_dir, True)
    return FileResponse(
        path=str(payload_path),
        media_type="application/octet-stream",
        filename=filename,
        background=background,
    )


def _safe_last_modified(path_str: str) -> datetime | None:
    path = Path(path_str)
    try:
        stat = path.stat()
    except OSError:
        return None
    return datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
