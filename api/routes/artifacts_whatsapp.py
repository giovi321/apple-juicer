from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api import schemas
from api.dependencies import get_backup_registry, get_db_session, get_unlock_manager
from api.routes._common import (
    download_attachment_response,
    extract_files,
    get_backup_or_404,
    get_decrypted_backup,
    resolve_filesystem,
)
from api.security import require_api_token
from core.db.artifacts import WhatsAppAttachment, WhatsAppChat, WhatsAppMessage
from core.services import BackupRegistry, UnlockManager

router = APIRouter(prefix="/backups", tags=["whatsapp"], dependencies=[Depends(require_api_token)])

# Domains tried (in order) when an attachment can't be resolved via the manifest.
WHATSAPP_FALLBACK_DOMAINS = [
    "MediaDomain",
    "AppDomainGroup-group.net.whatsapp.WhatsApp.shared",
    "AppDomainGroup-group.net.whatsapp.WhatsAppSMB.shared",
    "AppDomainGroup-group.net.whatsapp.WhatsApp",
    "AppDomain-net.whatsapp.WhatsApp",
]


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
        if not att.relative_path and not att.file_id:
            continue
        try:
            att_metadata = dict(att.metadata) if att.metadata else {}
        except (TypeError, ValueError):
            att_metadata = {}
        attachments.append(
            schemas.WhatsAppAttachmentModel(
                file_id=att.file_id,
                relative_path=att.relative_path,
                mime_type=att.mime_type,
                size_bytes=att.size_bytes,
                metadata=att_metadata,
            )
        )

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


@router.get("/{backup_id}/artifacts/whatsapp/chats", response_model=schemas.WhatsAppChatListResponse)
async def list_whatsapp_chats(
    backup_id: str,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    await get_decrypted_backup(backup_id, registry)
    db_backup = await get_backup_or_404(backup_id, session)
    result = await session.scalars(
        select(WhatsAppChat)
        .where(WhatsAppChat.backup_id == db_backup.id)
        .order_by(WhatsAppChat.last_message_at.desc().nullslast(), WhatsAppChat.title)
    )
    chats = [_serialize_chat(chat) for chat in result]
    return schemas.WhatsAppChatListResponse(items=chats)


@router.get("/{backup_id}/artifacts/whatsapp/chats/{chat_guid}", response_model=schemas.WhatsAppChatDetailResponse)
async def get_whatsapp_chat(
    backup_id: str,
    chat_guid: str,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    await get_decrypted_backup(backup_id, registry)
    db_backup = await get_backup_or_404(backup_id, session)
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
    backup = await get_decrypted_backup(backup_id, registry)
    fs = resolve_filesystem(backup, backup_id, session_token, unlock_mgr)
    return download_attachment_response(
        fs,
        relative_path,
        fallback_domains=WHATSAPP_FALLBACK_DOMAINS,
        strip_tilde=False,
        session_present=bool(session_token),
        label="WhatsApp",
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
    """Extract WhatsApp files for a chat into the decrypted dir for offline access."""
    backup = await get_decrypted_backup(backup_id, registry)
    db_backup = await get_backup_or_404(backup_id, db)
    stmt = (
        select(WhatsAppAttachment.relative_path, WhatsAppAttachment.file_id)
        .join(WhatsAppMessage, WhatsAppMessage.id == WhatsAppAttachment.message_id)
        .join(WhatsAppChat, WhatsAppChat.id == WhatsAppMessage.chat_id)
        .where(WhatsAppChat.backup_id == db_backup.id)
        .where(WhatsAppChat.chat_guid == chat_guid)
    )
    result = await db.execute(stmt)
    attachment_rows = result.fetchall()
    if not attachment_rows:
        return {"extracted_files": 0, "extracted_bytes": 0}

    fs = resolve_filesystem(backup, backup_id, session_token, unlock_mgr)
    return extract_files(fs, Path(backup.decrypted_path), attachment_rows, strip_tilde=False)
