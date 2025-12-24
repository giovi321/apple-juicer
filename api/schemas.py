from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from core.backupfs.types import BackupStatus
from core.db.models import DecryptionStatus


class BackupSummaryModel(BaseModel):
    id: str
    display_name: str
    device_name: Optional[str] = None
    product_version: Optional[str] = None
    is_encrypted: bool
    status: BackupStatus
    decryption_status: DecryptionStatus
    last_indexed_at: Optional[datetime] = None
    decrypted_at: Optional[datetime] = None
    size_bytes: Optional[int] = None
    last_modified_at: Optional[datetime] = None
    indexing_progress: Optional[int] = None
    indexing_total: Optional[int] = None
    indexing_artifact: Optional[str] = None


class DiscoverResponse(BaseModel):
    backups: list[BackupSummaryModel]
    base_directory: str


class UnlockRequest(BaseModel):
    password: str


class UnlockResponse(BaseModel):
    session_token: str
    ttl_seconds: int


class DecryptRequest(BaseModel):
    password: str


class DecryptStatusResponse(BaseModel):
    backup_id: str
    decryption_status: DecryptionStatus
    decrypted_at: Optional[datetime] = None
    error: Optional[str] = None


class ManifestEntryModel(BaseModel):
    file_id: str
    domain: str
    relative_path: str
    size: Optional[int] = None
    mtime: Optional[int] = None


class FileListResponse(BaseModel):
    items: list[ManifestEntryModel]
    limit: int
    offset: int


class DomainListResponse(BaseModel):
    domains: list[str]


class WhatsAppChatModel(BaseModel):
    chat_guid: str
    title: Optional[str] = None
    participant_count: Optional[int] = None
    last_message_at: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = None


class WhatsAppAttachmentModel(BaseModel):
    file_id: Optional[str] = None
    relative_path: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    metadata: Optional[dict[str, Any]] = None


class WhatsAppMessageModel(BaseModel):
    chat_guid: str
    message_id: str
    sender: Optional[str] = None
    sender_name: Optional[str] = None
    sent_at: Optional[datetime] = None
    message_type: Optional[str] = None
    body: Optional[str] = None
    is_from_me: bool
    has_attachments: bool
    attachments: list[WhatsAppAttachmentModel] = []
    metadata: Optional[dict[str, Any]] = None


class WhatsAppChatListResponse(BaseModel):
    items: list[WhatsAppChatModel]


class WhatsAppChatDetailResponse(BaseModel):
    chat: WhatsAppChatModel
    messages: list[WhatsAppMessageModel]


class MessageConversationModel(BaseModel):
    conversation_guid: str
    service: Optional[str] = None
    display_name: Optional[str] = None
    last_message_at: Optional[datetime] = None
    participant_handles: Optional[list[str]] = None


class MessageAttachmentModel(BaseModel):
    file_id: Optional[str] = None
    relative_path: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    metadata: Optional[dict[str, Any]] = None


class MessageItemModel(BaseModel):
    message_guid: str
    conversation_guid: str
    sender: Optional[str] = None
    is_from_me: bool
    sent_at: Optional[datetime] = None
    text: Optional[str] = None
    has_attachments: bool
    attachments: list[MessageAttachmentModel] = []
    metadata: Optional[dict[str, Any]] = None


class MessageConversationListResponse(BaseModel):
    items: list[MessageConversationModel]


class MessageConversationDetailResponse(BaseModel):
    conversation: MessageConversationModel
    messages: list[MessageItemModel]
