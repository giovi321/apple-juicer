from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db.base import Base


class MetadataJSONMixin:
    metadata_blob: Mapped[dict | None] = mapped_column("metadata", JSON)

    @property
    def metadata(self) -> dict | None:
        return self.metadata_blob

    @metadata.setter
    def metadata(self, value: dict | None) -> None:
        self.metadata_blob = value


class PhotoAsset(Base, MetadataJSONMixin):
    __tablename__ = "photo_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backup_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("backups.id", ondelete="CASCADE"), index=True, nullable=False
    )
    asset_id: Mapped[str] = mapped_column(String(255), index=True)
    original_filename: Mapped[str | None] = mapped_column(String(512))
    relative_path: Mapped[str | None] = mapped_column(String(1024))
    file_id: Mapped[str | None] = mapped_column(String(128), index=True)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    timezone_offset_minutes: Mapped[int | None] = mapped_column()
    width: Mapped[int | None]
    height: Mapped[int | None]
    media_type: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        Index("ix_photo_assets_backup_asset", "backup_id", "asset_id", unique=True),
    )


class WhatsAppChat(Base, MetadataJSONMixin):
    __tablename__ = "whatsapp_chats"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backup_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("backups.id", ondelete="CASCADE"), index=True)
    chat_guid: Mapped[str] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(255))
    participant_count: Mapped[int | None]
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    messages: Mapped[list["WhatsAppMessage"]] = relationship(back_populates="chat", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_whatsapp_chats_backup_guid", "backup_id", "chat_guid", unique=True),
    )


class WhatsAppMessage(Base, MetadataJSONMixin):
    __tablename__ = "whatsapp_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backup_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("backups.id", ondelete="CASCADE"), index=True)
    chat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("whatsapp_chats.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[str] = mapped_column(String(255), index=True)
    sender: Mapped[str | None] = mapped_column(String(255))
    sender_name: Mapped[str | None] = mapped_column(String(255))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    media_type: Mapped[str | None] = mapped_column(String(64))
    is_from_me: Mapped[bool] = mapped_column(Boolean, default=False)
    has_attachments: Mapped[bool] = mapped_column(Boolean, default=False)
    body: Mapped[str | None] = mapped_column(Text)

    chat: Mapped["WhatsAppChat"] = relationship(back_populates="messages")
    attachments: Mapped[list["WhatsAppAttachment"]] = relationship(
        "WhatsAppAttachment", back_populates="message", cascade="all, delete-orphan"
    )


class WhatsAppAttachment(Base, MetadataJSONMixin):
    __tablename__ = "whatsapp_attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("whatsapp_messages.id", ondelete="CASCADE"), index=True
    )
    file_id: Mapped[str | None] = mapped_column(String(128), index=True)
    relative_path: Mapped[str | None] = mapped_column(String(1024))
    mime_type: Mapped[str | None] = mapped_column(String(255))
    size_bytes: Mapped[int | None]
    message: Mapped["WhatsAppMessage"] = relationship(back_populates="attachments")


WhatsAppChat.messages = relationship(
    "WhatsAppMessage", order_by=WhatsAppMessage.sent_at, back_populates="chat", cascade="all, delete-orphan"
)


class MessageConversation(Base):
    __tablename__ = "message_conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backup_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("backups.id", ondelete="CASCADE"), index=True)
    conversation_guid: Mapped[str] = mapped_column(String(255), unique=True)
    service: Mapped[str | None] = mapped_column(String(32))
    display_name: Mapped[str | None] = mapped_column(String(255))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    participant_handles: Mapped[list | None] = mapped_column(JSON)


class Message(Base, MetadataJSONMixin):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backup_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("backups.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("message_conversations.id", ondelete="CASCADE"), index=True
    )
    message_guid: Mapped[str] = mapped_column(String(255), index=True)
    sender: Mapped[str | None] = mapped_column(String(255))
    is_from_me: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    text: Mapped[str | None] = mapped_column(Text)
    has_attachments: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_blob: Mapped[dict | None] = mapped_column("metadata", JSON)


class MessageAttachment(Base, MetadataJSONMixin):
    __tablename__ = "message_attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), index=True)
    file_id: Mapped[str | None] = mapped_column(String(128), index=True)
    relative_path: Mapped[str | None] = mapped_column(String(1024))
    mime_type: Mapped[str | None] = mapped_column(String(255))
    size_bytes: Mapped[int | None]
    metadata_blob: Mapped[dict | None] = mapped_column("metadata", JSON)


class Note(Base, MetadataJSONMixin):
    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backup_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("backups.id", ondelete="CASCADE"), index=True)
    note_identifier: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str | None] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(Text)
    folder: Mapped[str | None] = mapped_column(String(255))
    last_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Calendar(Base, MetadataJSONMixin):
    __tablename__ = "calendars"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backup_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("backups.id", ondelete="CASCADE"), index=True)
    calendar_identifier: Mapped[str] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(Text)
    folder: Mapped[str | None] = mapped_column(String(255))
    last_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    color: Mapped[str | None] = mapped_column(String(32))
    source: Mapped[str | None] = mapped_column(String(128))

    __table_args__ = (Index("ix_calendars_backup_identifier", "backup_id", "calendar_identifier", unique=True),)


class CalendarEvent(Base, MetadataJSONMixin):
    __tablename__ = "calendar_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backup_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("backups.id", ondelete="CASCADE"), index=True)
    calendar_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("calendars.id", ondelete="CASCADE"), index=True)
    event_identifier: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str | None] = mapped_column(String(512))
    location: Mapped[str | None] = mapped_column(String(512))
    notes: Mapped[str | None] = mapped_column(Text)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_all_day: Mapped[bool] = mapped_column(Boolean, default=False)


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backup_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("backups.id", ondelete="CASCADE"), index=True)
    contact_identifier: Mapped[str] = mapped_column(String(255), index=True)
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    company: Mapped[str | None] = mapped_column(String(255))
    emails: Mapped[list | None] = mapped_column(JSON)
    phones: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    avatar_file_id: Mapped[str | None] = mapped_column(String(128))


class ArtifactSearchIndex(Base):
    __tablename__ = "artifact_search_index"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backup_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("backups.id", ondelete="CASCADE"), index=True)
    artifact_type: Mapped[str] = mapped_column(String(64), index=True)
    artifact_ref: Mapped[str] = mapped_column(String(255), index=True)
    display_text: Mapped[str | None] = mapped_column(String(512))
    payload: Mapped[dict | None] = mapped_column(JSON)
    search_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
