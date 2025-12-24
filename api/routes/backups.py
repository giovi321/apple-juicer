import shutil
from datetime import datetime, timezone
from pathlib import Path
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from redis import Redis

from api import schemas
from api.dependencies import get_backup_registry, get_db_session, get_unlock_manager, get_decrypt_orchestrator
from api.security import require_api_token, require_session_token
from core.config import get_settings
from core.services import BackupRegistry, SessionNotFoundError, UnlockError, UnlockManager, DecryptOrchestrator, DecryptionError
from core.db.models import DecryptionStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.artifacts import WhatsAppChat, WhatsAppMessage, WhatsAppAttachment
from core.db.models import Backup
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backups", tags=["backups"], dependencies=[Depends(require_api_token)])
settings = get_settings()
host_display_path = settings.backup_paths.host_display_path or settings.backup_paths.base_path


@router.get("", response_model=schemas.DiscoverResponse)
async def list_backups(registry: BackupRegistry = Depends(get_backup_registry)):
    # First check if database is empty, if so discover backups from filesystem
    backups = await registry.list_backups()
    if not backups:
        # Database is empty, discover backups from filesystem
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
    """Extract artifact database file paths from decrypted backup."""
    decrypted_dir = Path(decrypted_path)
    artifact_files = {}
    
    # Map of database names to artifact types
    db_mappings = {
        "Photos.sqlite": "photos",
        "ChatStorage.sqlite": "whatsapp",
        "chat.db": "messages",
        "notes.sqlite": "notes",
        "Calendar.sqlite": "calendar",
        "AddressBook.sqlitedb": "contacts",
    }
    
    for db_name, artifact_type in db_mappings.items():
        db_path = decrypted_dir / db_name
        if db_path.exists():
            artifact_files[artifact_type] = str(db_path)
    
    return artifact_files


def _queue_artifact_indexing(backup_id: str, decrypted_path: str) -> None:
    """Queue artifact indexing job for the decrypted backup using RQ."""
    try:
        from rq import Queue
        redis_conn = Redis.from_url(settings.redis.url)
        queue = Queue(connection=redis_conn)
        
        artifact_files = _extract_artifact_databases(decrypted_path)
        if artifact_files:  # Only queue if there are artifacts to index
            from worker.tasks import _index_backup_job
            queue.enqueue(_index_backup_job, backup_id, decrypted_path, artifact_files)
            logger.info(f"Queued artifact indexing job for backup {backup_id} with {len(artifact_files)} artifacts")
        else:
            logger.info(f"No artifact databases found for backup {backup_id}")
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Backup is not decrypted."
        )
    
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
                    detail=f"Failed to delete decrypted data: {str(exc)}"
                ) from exc
    
    # Delete indexed artifacts from database
    from worker.tasks import _truncate_artifacts
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
    backup = await registry.get_backup(backup_id)
    if not backup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found.")
    if backup.decryption_status != DecryptionStatus.DECRYPTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Backup not decrypted.")
    
    fs = _get_filesystem_from_decrypted(backup)
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
    backup = await registry.get_backup(backup_id)
    if not backup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found.")
    if backup.decryption_status != DecryptionStatus.DECRYPTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Backup not decrypted.")
    
    fs = _get_filesystem_from_decrypted(backup)
    return schemas.DomainListResponse(domains=fs.list_domains())


@router.get("/{backup_id}/file/{file_id}")
async def download_file(
    backup_id: str,
    file_id: str,
    registry: BackupRegistry = Depends(get_backup_registry),
):
    backup = await registry.get_backup(backup_id)
    if not backup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found.")
    if backup.decryption_status != DecryptionStatus.DECRYPTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Backup not decrypted.")
    
    fs = _get_filesystem_from_decrypted(backup)
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


def _ensure_session(backup_id: str, session_token: str, unlock_mgr: UnlockManager):
    try:
        session_backup_id, fs = unlock_mgr.get_filesystem(session_token)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    if session_backup_id != backup_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session does not match backup.")
    return fs


def _get_filesystem_from_decrypted(backup: Backup):
    from core.backupfs import BackupFS
    decrypted_path = Path(backup.decrypted_path)
    if not decrypted_path.exists():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Decrypted backup data missing.")
    return BackupFS(handle=None, sandbox_root=settings.backup_paths.temp_path, backup_root=str(decrypted_path))


def _safe_last_modified(path_str: str) -> datetime | None:
    path = Path(path_str)
    try:
        stat = path.stat()
    except OSError:
        return None
    return datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)


async def _get_backup_or_404(backup_id: str, session: AsyncSession) -> Backup:
    backup = await session.scalar(select(Backup).where(Backup.ios_identifier == backup_id))
    if not backup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found.")
    return backup


def _serialize_chat(chat: WhatsAppChat) -> schemas.WhatsAppChatModel:
    try:
        metadata = dict(chat.metadata) if chat.metadata else {}
    except (TypeError, ValueError):
        metadata = {}
    return schemas.WhatsAppChatModel(
        chat_guid=chat.chat_guid,
        title=chat.title,
        participant_count=chat.participant_count,
        last_message_at=chat.last_message_at,
        metadata=metadata,
    )


def _normalize_whatsapp_sender(sender: object | None) -> str | None:
    if sender is None:
        return None
    if isinstance(sender, (bytes, bytearray, memoryview)):
        try:
            sender_str = bytes(sender).decode("utf-8", errors="replace")
        except Exception:
            sender_str = str(sender)
    else:
        sender_str = str(sender)

    sender_str = sender_str.strip()
    if not sender_str:
        return None

    if sender_str.startswith("Optional(") and sender_str.endswith(")"):
        sender_str = sender_str[len("Optional(") : -1].strip()

    sender_str = sender_str.strip("\"'")

    if sender_str.lower().startswith("whatsapp:"):
        sender_str = sender_str.split(":", 1)[1].strip()

    for suffix in ("@s.whatsapp.net", "@c.us", "@g.us"):
        if sender_str.endswith(suffix):
            sender_str = sender_str[: -len(suffix)]
            break

    sender_str = sender_str.strip()
    return sender_str or None


def _serialize_message(chat_guid: str, message: WhatsAppMessage) -> schemas.WhatsAppMessageModel:
    try:
        metadata = dict(message.metadata) if message.metadata else {}
    except (TypeError, ValueError):
        metadata = {}
    
    attachments = []
    for att in message.attachments:
        # Only include attachments that have actual data
        if not att.relative_path and not att.file_id:
            continue
        try:
            att_metadata = dict(att.metadata) if att.metadata else {}
        except (TypeError, ValueError):
            att_metadata = {}
        attachments.append(schemas.WhatsAppAttachmentModel(
            file_id=att.file_id,
            relative_path=att.relative_path,
            mime_type=att.mime_type,
            size_bytes=att.size_bytes,
            metadata=att_metadata,
        ))
    
    return schemas.WhatsAppMessageModel(
        chat_guid=chat_guid,
        message_id=message.message_id,
        sender=_normalize_whatsapp_sender(message.sender),
        sender_name=message.sender_name,
        sent_at=message.sent_at,
        message_type=message.media_type,
        body=message.body,
        is_from_me=message.is_from_me,
        has_attachments=message.has_attachments,
        attachments=attachments,
        metadata=metadata,
    )


@router.get(
    "/{backup_id}/artifacts/whatsapp/chats",
    response_model=schemas.WhatsAppChatListResponse,
)
async def list_whatsapp_chats(
    backup_id: str,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    backup = await registry.get_backup(backup_id)
    if not backup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found.")
    if backup.decryption_status != DecryptionStatus.DECRYPTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Backup not decrypted.")
    
    db_backup = await _get_backup_or_404(backup_id, session)
    result = await session.scalars(
        select(WhatsAppChat)
        .where(WhatsAppChat.backup_id == db_backup.id)
        .order_by(WhatsAppChat.last_message_at.desc().nullslast(), WhatsAppChat.title)
    )
    chats = [_serialize_chat(chat) for chat in result]
    return schemas.WhatsAppChatListResponse(items=chats)


@router.get(
    "/{backup_id}/artifacts/whatsapp/chats/{chat_guid}",
    response_model=schemas.WhatsAppChatDetailResponse,
)
async def get_whatsapp_chat(
    backup_id: str,
    chat_guid: str,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    backup = await registry.get_backup(backup_id)
    if not backup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found.")
    if backup.decryption_status != DecryptionStatus.DECRYPTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Backup not decrypted.")
    
    db_backup = await _get_backup_or_404(backup_id, session)
    chat = await session.scalar(
        select(WhatsAppChat).where(
            WhatsAppChat.backup_id == db_backup.id, WhatsAppChat.chat_guid == chat_guid
        )
    )
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")
    messages_result = await session.scalars(
        select(WhatsAppMessage)
        .options(selectinload(WhatsAppMessage.attachments))
        .where(WhatsAppMessage.chat_id == chat.id)
        .order_by(WhatsAppMessage.sent_at.asc().nullsfirst(), WhatsAppMessage.id)
    )
    messages = [_serialize_message(chat.chat_guid, msg) for msg in messages_result]
    return schemas.WhatsAppChatDetailResponse(chat=_serialize_chat(chat), messages=messages)


@router.get("/{backup_id}/artifacts/whatsapp/attachment")
async def download_whatsapp_attachment(
    backup_id: str,
    relative_path: str,
    registry: BackupRegistry = Depends(get_backup_registry),
    unlock_mgr: UnlockManager = Depends(get_unlock_manager),
    session_token: str | None = Header(None, alias="X-Backup-Session"),
):
    """Download a WhatsApp attachment by its relative path."""
    backup = await registry.get_backup(backup_id)
    if not backup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found.")
    if backup.decryption_status != DecryptionStatus.DECRYPTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Backup not decrypted.")
    
    if session_token:
        fs = _ensure_session(backup_id, session_token, unlock_mgr)
    else:
        fs = _get_filesystem_from_decrypted(backup)

    requested_path = (relative_path or "").lstrip("/")
    if not requested_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="relative_path is required")

    resolved_domain: str | None = None
    resolved_relative_path: str | None = None

    def _pick_candidate(entries, wanted: str) -> tuple[str, str] | None:
        for entry in entries:
            if entry.relative_path == wanted:
                return entry.domain, entry.relative_path
        for entry in entries:
            if entry.relative_path.endswith("/" + wanted) or entry.relative_path.endswith(wanted):
                return entry.domain, entry.relative_path
        return None

    try:
        candidates = fs.search_paths(requested_path, limit=50)
        picked = _pick_candidate(candidates, requested_path)
        if picked:
            resolved_domain, resolved_relative_path = picked
    except Exception as e:
        logger.warning(f"Manifest search failed for WhatsApp attachment {requested_path}: {e}")

    if not resolved_domain or not resolved_relative_path:
        filename_only = Path(requested_path).name
        if filename_only:
            try:
                candidates = fs.search_paths(filename_only, limit=50)
                picked = _pick_candidate(candidates, filename_only)
                if picked:
                    resolved_domain, resolved_relative_path = picked
            except Exception as e:
                logger.warning(f"Filename manifest search failed for WhatsApp attachment {filename_only}: {e}")

    if not resolved_domain or not resolved_relative_path:
        # Last resort: try common WhatsApp-related domains with the provided relative path.
        domain_candidates = [
            "MediaDomain",
            "AppDomainGroup-group.net.whatsapp.WhatsApp.shared",
            "AppDomainGroup-group.net.whatsapp.WhatsAppSMB.shared",
            "AppDomainGroup-group.net.whatsapp.WhatsApp",
            "AppDomain-net.whatsapp.WhatsApp",
        ]
        for domain in domain_candidates:
            try:
                payload_path, sandbox_dir = fs.extract_to_temp(domain=domain, relative_path=requested_path)
                resolved_domain, resolved_relative_path = domain, requested_path
                break
            except Exception:
                continue
        else:
            logger.error(f"Failed to resolve WhatsApp attachment in manifest: {requested_path}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment file not found.")

    try:
        payload_path, sandbox_dir = fs.extract_to_temp(domain=resolved_domain, relative_path=resolved_relative_path)
    except Exception as e:
        logger.error(
            f"Failed to extract WhatsApp attachment domain={resolved_domain} relative_path={resolved_relative_path}: {e}"
        )
        if not session_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attachment not present in decrypted data. Unlock the backup and retry.",
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment file not found.")
    
    filename = Path(resolved_relative_path).name or "attachment"
    background = BackgroundTask(shutil.rmtree, sandbox_dir, True)
    
    # Determine media type based on file extension
    import mimetypes
    mime_type, _ = mimetypes.guess_type(filename)
    
    return FileResponse(
        path=str(payload_path),
        media_type=mime_type or "application/octet-stream",
        filename=filename,
        background=background,
    )


@router.post("/{backup_id}/extract/whatsapp/{chat_guid}")
async def extract_whatsapp_files(
    backup_id: str,
    chat_guid: str,
    db: AsyncSession = Depends(get_db_session),
    registry: BackupRegistry = Depends(get_backup_registry),
    unlock_mgr: UnlockManager = Depends(get_unlock_manager),
    session_token: str | None = Header(None, alias="X-Backup-Session"),
):
    """Extract WhatsApp files for a specific chat to decrypted backup directory for offline access."""
    backup = await registry.get_backup(backup_id)
    if not backup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found.")
    if backup.decryption_status != DecryptionStatus.DECRYPTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Backup not decrypted.")
    
    # Get the database backup record to get the actual UUID
    db_backup = await _get_backup_or_404(backup_id, db)
    
    # Get attachment file IDs and relative paths for this chat
    logger.info(f"Extracting WhatsApp files for chat_guid={chat_guid}, backup.id={db_backup.id}")
    stmt = (
        select(WhatsAppAttachment.relative_path, WhatsAppAttachment.file_id)
        .join(WhatsAppMessage, WhatsAppMessage.id == WhatsAppAttachment.message_id)
        .join(WhatsAppChat, WhatsAppChat.id == WhatsAppMessage.chat_id)
        .where(WhatsAppChat.backup_id == db_backup.id)
        .where(WhatsAppChat.chat_guid == chat_guid)
    )
    result = await db.execute(stmt)
    attachment_rows = result.fetchall()
    logger.info(f"Found {len(attachment_rows)} attachments for chat_guid={chat_guid}")
    
    if not attachment_rows:
        return {"extracted_files": 0, "extracted_bytes": 0}
    
    total_attachments = len(attachment_rows)
    logger.info(f"Starting extraction of {total_attachments} attachments for chat_guid={chat_guid}")
    
    if session_token:
        fs = _ensure_session(backup_id, session_token, unlock_mgr)
    else:
        fs = _get_filesystem_from_decrypted(backup)
    decrypted_path = Path(backup.decrypted_path)
    
    # Batch lookup all file_ids at once to avoid opening SQLite connection for each file
    file_ids = [file_id for _, file_id in attachment_rows if file_id]
    logger.info(f"Batch looking up {len(file_ids)} file IDs in manifest")
    manifest_entries = fs.get_entries_by_file_ids(file_ids)
    logger.info(f"Found {len(manifest_entries)} entries in manifest")
    
    extracted_files = 0
    extracted_bytes = 0
    skipped_exists = 0
    skipped_not_found = 0
    
    for idx, (relative_path, file_id) in enumerate(attachment_rows):
        # Log progress every 500 files
        if idx > 0 and idx % 500 == 0:
            logger.info(f"Extraction progress: {idx}/{total_attachments} processed, {extracted_files} extracted, {skipped_exists} already exist")
        
        manifest_entry = None
        if file_id:
            manifest_entry = manifest_entries.get(file_id)
        if not manifest_entry and relative_path:
            try:
                manifest_candidates = fs.search_paths(relative_path, limit=5)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(f"Manifest search failed for attachment path {relative_path}: {exc}")
                manifest_candidates = []
            if manifest_candidates:
                manifest_entry = manifest_candidates[0]

        if not manifest_entry:
            skipped_not_found += 1
            continue

        mf = manifest_entry
        target_path = decrypted_path / mf.domain / mf.relative_path
        if target_path.exists():
            skipped_exists += 1
            continue
        
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            payload_path, sandbox_dir = fs.extract_to_temp(domain=mf.domain, relative_path=mf.relative_path)
            shutil.copy2(payload_path, target_path)
            shutil.rmtree(sandbox_dir, ignore_errors=True)
            extracted_files += 1
            if mf.size:
                extracted_bytes += int(mf.size)
        except Exception as e:
            logger.warning(f"Failed to extract {mf.domain}/{mf.relative_path}: {e}")
            continue
    
    logger.info(f"Extraction complete: {extracted_files} extracted, {skipped_exists} already existed, {skipped_not_found} not found in manifest")
    return {"extracted_files": extracted_files, "extracted_bytes": extracted_bytes}
