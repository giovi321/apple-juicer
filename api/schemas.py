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


class PhotoAssetModel(BaseModel):
    asset_id: Optional[str] = None
    original_filename: Optional[str] = None
    relative_path: Optional[str] = None
    file_id: Optional[str] = None
    taken_at: Optional[datetime] = None
    timezone_offset_minutes: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    media_type: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class PhotoListResponse(BaseModel):
    items: list[PhotoAssetModel]


class NoteModel(BaseModel):
    note_identifier: str
    title: Optional[str] = None
    body: Optional[str] = None
    folder: Optional[str] = None
    created_at: Optional[datetime] = None
    last_modified_at: Optional[datetime] = None


class NoteListResponse(BaseModel):
    items: list[NoteModel]


class CalendarEventModel(BaseModel):
    event_identifier: str
    calendar_identifier: Optional[str] = None
    calendar_name: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_all_day: bool = False


class CalendarEventListResponse(BaseModel):
    items: list[CalendarEventModel]


class ContactModel(BaseModel):
    contact_identifier: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    emails: list[str] = []
    phones: list[str] = []
    avatar_file_id: Optional[str] = None


class ContactListResponse(BaseModel):
    items: list[ContactModel]


class CallModel(BaseModel):
    call_identifier: str
    address: Optional[str] = None
    display_name: Optional[str] = None
    occurred_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    is_outgoing: bool = False
    answered: bool = False
    service: Optional[str] = None


class CallListResponse(BaseModel):
    items: list[CallModel]


class SafariVisitModel(BaseModel):
    visit_identifier: str
    url: Optional[str] = None
    title: Optional[str] = None
    visited_at: Optional[datetime] = None
    visit_count: Optional[int] = None


class SafariVisitListResponse(BaseModel):
    items: list[SafariVisitModel]


class LocationModel(BaseModel):
    location_identifier: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    speed: Optional[float] = None
    horizontal_accuracy: Optional[float] = None
    recorded_at: Optional[datetime] = None


class LocationListResponse(BaseModel):
    items: list[LocationModel]


class VoicemailModel(BaseModel):
    voicemail_identifier: str
    sender: Optional[str] = None
    received_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    trashed: bool = False


class VoicemailListResponse(BaseModel):
    items: list[VoicemailModel]


class SearchResultModel(BaseModel):
    artifact_type: str
    artifact_ref: str
    display_text: Optional[str] = None
    payload: Optional[dict[str, Any]] = None


class SearchResponse(BaseModel):
    query: str
    items: list[SearchResultModel]


class TimelineEventModel(BaseModel):
    timestamp: datetime
    artifact_type: str
    title: Optional[str] = None
    subtitle: Optional[str] = None


class TimelineResponse(BaseModel):
    items: list[TimelineEventModel]
