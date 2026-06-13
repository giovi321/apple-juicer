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
from core.db.artifacts import Message, MessageAttachment, MessageConversation
from core.services import BackupRegistry, UnlockManager

router = APIRouter(prefix="/backups", tags=["messages"], dependencies=[Depends(require_api_token)])

MESSAGE_FALLBACK_DOMAINS = ["MediaDomain", "HomeDomain"]


def _serialize_conversation(conv: MessageConversation) -> schemas.MessageConversationModel:
    return schemas.MessageConversationModel(
        conversation_guid=conv.conversation_guid,
        service=conv.service,
        display_name=conv.display_name,
        last_message_at=conv.last_message_at,
        participant_handles=conv.participant_handles or [],
    )


def _serialize_message_item(
    conversation_guid: str, message: Message, attachments: list[MessageAttachment]
) -> schemas.MessageItemModel:
    try:
        metadata = dict(message.metadata) if message.metadata else {}
    except (TypeError, ValueError):
        metadata = {}

    attachment_models = []
    for att in attachments:
        if not att.relative_path and not att.file_id:
            continue
        try:
            att_metadata = dict(att.metadata) if att.metadata else {}
        except (TypeError, ValueError):
            att_metadata = {}
        attachment_models.append(
            schemas.MessageAttachmentModel(
                file_id=att.file_id,
                relative_path=att.relative_path,
                mime_type=att.mime_type,
                size_bytes=att.size_bytes,
                metadata=att_metadata,
            )
        )

    return schemas.MessageItemModel(
        message_guid=message.message_guid,
        conversation_guid=conversation_guid,
        sender=message.sender,
        is_from_me=message.is_from_me,
        sent_at=message.sent_at,
        text=message.text,
        has_attachments=message.has_attachments,
        attachments=attachment_models,
        metadata=metadata,
    )


@router.get(
    "/{backup_id}/artifacts/messages/conversations",
    response_model=schemas.MessageConversationListResponse,
)
async def list_message_conversations(
    backup_id: str,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    await get_decrypted_backup(backup_id, registry)
    db_backup = await get_backup_or_404(backup_id, session)
    result = await session.scalars(
        select(MessageConversation)
        .where(MessageConversation.backup_id == db_backup.id)
        .order_by(MessageConversation.last_message_at.desc().nullslast(), MessageConversation.display_name)
    )
    conversations = [_serialize_conversation(conv) for conv in result]
    return schemas.MessageConversationListResponse(items=conversations)


@router.get(
    "/{backup_id}/artifacts/messages/conversations/{conversation_guid}",
    response_model=schemas.MessageConversationDetailResponse,
)
async def get_message_conversation(
    backup_id: str,
    conversation_guid: str,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    await get_decrypted_backup(backup_id, registry)
    db_backup = await get_backup_or_404(backup_id, session)
    conversation = await session.scalar(
        select(MessageConversation).where(
            MessageConversation.backup_id == db_backup.id,
            MessageConversation.conversation_guid == conversation_guid,
        )
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    messages_result = await session.scalars(
        select(Message)
        .options(selectinload(Message.attachments))
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.sent_at.asc().nullsfirst(), Message.id)
    )

    messages = []
    for msg in messages_result:
        attachments = msg.attachments if hasattr(msg, "attachments") else []
        messages.append(_serialize_message_item(conversation.conversation_guid, msg, attachments))

    return schemas.MessageConversationDetailResponse(
        conversation=_serialize_conversation(conversation), messages=messages
    )


@router.get("/{backup_id}/artifacts/messages/attachment")
async def download_message_attachment(
    backup_id: str,
    relative_path: str,
    registry: BackupRegistry = Depends(get_backup_registry),
    unlock_mgr: UnlockManager = Depends(get_unlock_manager),
    session_token: str | None = Header(None, alias="X-Backup-Session"),
):
    """Download an iMessage/SMS attachment by its relative path."""
    backup = await get_decrypted_backup(backup_id, registry)
    fs = resolve_filesystem(backup, backup_id, session_token, unlock_mgr)
    return download_attachment_response(
        fs,
        relative_path,
        fallback_domains=MESSAGE_FALLBACK_DOMAINS,
        strip_tilde=True,
        session_present=bool(session_token),
        label="message",
    )


@router.post("/{backup_id}/extract/messages/{conversation_guid}")
async def extract_message_files(
    backup_id: str,
    conversation_guid: str,
    db: AsyncSession = Depends(get_db_session),
    registry: BackupRegistry = Depends(get_backup_registry),
    unlock_mgr: UnlockManager = Depends(get_unlock_manager),
    session_token: str | None = Header(None, alias="X-Backup-Session"),
):
    """Extract iMessage/SMS files for a conversation into the decrypted dir."""
    backup = await get_decrypted_backup(backup_id, registry)
    db_backup = await get_backup_or_404(backup_id, db)
    stmt = (
        select(MessageAttachment.relative_path, MessageAttachment.file_id)
        .join(Message, Message.id == MessageAttachment.message_id)
        .join(MessageConversation, MessageConversation.id == Message.conversation_id)
        .where(MessageConversation.backup_id == db_backup.id)
        .where(MessageConversation.conversation_guid == conversation_guid)
    )
    result = await db.execute(stmt)
    attachment_rows = result.fetchall()
    if not attachment_rows:
        return {"extracted_files": 0, "extracted_bytes": 0}

    fs = resolve_filesystem(backup, backup_id, session_token, unlock_mgr)
    return extract_files(fs, Path(backup.decrypted_path), attachment_rows, strip_tilde=True)
