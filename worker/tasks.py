from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.backupfs.types import BackupStatus
from core.config import get_settings
from core.db.artifacts import (
    ArtifactSearchIndex,
    Calendar,
    CalendarEvent,
    Contact,
    Message,
    MessageAttachment,
    MessageConversation,
    Note,
    PhotoAsset,
    WhatsAppAttachment,
    WhatsAppChat,
    WhatsAppMessage,
)
from core.db.models import Backup
from core.db.session import async_session_factory
from parsers import calendar as calendar_parser
from parsers import contacts as contacts_parser
from parsers import messages as messages_parser
from parsers import notes as notes_parser
from parsers import photos as photos_parser
from parsers import whatsapp as whatsapp_parser

logger = logging.getLogger(__name__)


async def _index_backup_job(
    backup_identifier: str,
    artifact_bundle_dir: str,
    artifact_files: dict[str, str],
) -> None:
    settings = get_settings()
    job_dir = Path(artifact_bundle_dir)
    if not job_dir.exists():
        raise FileNotFoundError(f"Artifact bundle missing: {artifact_bundle_dir}")

    async with async_session_factory() as session:
        backup = await session.scalar(select(Backup).where(Backup.ios_identifier == backup_identifier))
        if not backup:
            raise RuntimeError(f"Unknown backup {backup_identifier}")

        backup.status = BackupStatus.INDEXING
        backup.indexing_progress = 0
        backup.indexing_total = 1
        backup.indexing_artifact = None
        await session.flush()
        await session.commit()

        await _truncate_artifacts(session, backup)
        await session.commit()

        await _ingest_photos(session, backup, Path(artifact_files["photos"]) if "photos" in artifact_files else None)
        await session.commit()
        await _ingest_whatsapp(session, backup, Path(artifact_files["whatsapp"]) if "whatsapp" in artifact_files else None)
        await session.commit()
        await _ingest_messages(session, backup, Path(artifact_files["messages"]) if "messages" in artifact_files else None)
        await session.commit()
        await _ingest_notes(session, backup, Path(artifact_files["notes"]) if "notes" in artifact_files else None)
        await session.commit()
        await _ingest_calendar(session, backup, Path(artifact_files["calendar"]) if "calendar" in artifact_files else None)
        await session.commit()
        await _ingest_contacts(session, backup, Path(artifact_files["contacts"]) if "contacts" in artifact_files else None)
        await session.commit()

        backup.status = BackupStatus.INDEXED
        backup.last_indexed_at = datetime.now(timezone.utc)
        backup.indexing_progress = backup.indexing_total
        backup.indexing_artifact = None
        await session.commit()


async def _truncate_artifacts(session: AsyncSession, backup: Backup) -> None:
    # Delete WhatsAppAttachments BEFORE deleting messages (no backup_id on attachments)
    await session.execute(
        delete(WhatsAppAttachment).where(
            WhatsAppAttachment.message_id.in_(
                select(WhatsAppMessage.id).where(WhatsAppMessage.backup_id == backup.id)
            )
        )
    )
    
    # Delete MessageAttachments BEFORE deleting messages (no backup_id on attachments)
    await session.execute(
        delete(MessageAttachment).where(
            MessageAttachment.message_id.in_(
                select(Message.id).where(Message.backup_id == backup.id)
            )
        )
    )
    
    tables_with_backup_id = [
        PhotoAsset,
        WhatsAppMessage,
        WhatsAppChat,
        Message,
        MessageConversation,
        Note,
        CalendarEvent,
        Calendar,
        Contact,
        ArtifactSearchIndex,
    ]
    for table in tables_with_backup_id:
        await session.execute(delete(table).where(table.backup_id == backup.id))


async def _ingest_photos(session: AsyncSession, backup: Backup, db_path: Path | None) -> None:
    if not db_path or not str(db_path).strip() or not db_path.exists():
        return
    backup.indexing_artifact = "photos"
    await session.flush()
    await session.commit()

    assets = photos_parser.parse_photos(db_path)
    backup.indexing_total = (backup.indexing_total or 0) + len(assets)
    await session.flush()
    await session.commit()

    chunk_size = 500
    for offset in range(0, len(assets), chunk_size):
        chunk = assets[offset : offset + chunk_size]
        photo_rows = [
            PhotoAsset(
                backup_id=backup.id,
                asset_id=asset.asset_id,
                original_filename=asset.original_filename,
                relative_path=asset.relative_path,
                file_id=asset.file_id,
                taken_at=asset.taken_at,
                timezone_offset_minutes=asset.timezone_offset_minutes,
                width=asset.width,
                height=asset.height,
                media_type=asset.media_type,
                metadata=asset.metadata,
            )
            for asset in chunk
        ]
        session.add_all(photo_rows)
        await _add_search_rows(
            session,
            backup,
            "photo",
            [
                ArtifactSearchIndex(
                    backup_id=backup.id,
                    artifact_type="photo",
                    artifact_ref=asset.asset_id or asset.file_id or "",
                    display_text=asset.original_filename,
                    payload=asset.metadata,
                    search_text=" ".join(filter(None, [asset.original_filename, asset.relative_path])),
                )
                for asset in chunk
            ],
        )
        backup.indexing_progress = (backup.indexing_progress or 0) + len(chunk)
        await session.flush()
        await session.commit()


async def _ingest_whatsapp(session: AsyncSession, backup: Backup, db_path: Path | None) -> None:
    if not db_path or not str(db_path).strip() or not db_path.exists():
        return
    backup.indexing_artifact = "whatsapp"
    await session.flush()
    await session.commit()

    # Delete existing WhatsApp data for this backup to allow re-indexing
    await session.execute(delete(WhatsAppChat).where(WhatsAppChat.backup_id == backup.id))
    await session.commit()

    chats, messages, attachments = whatsapp_parser.parse_whatsapp(db_path)
    backup.indexing_total = (backup.indexing_total or 0) + len(chats) + len(messages) + len(attachments)
    await session.flush()
    await session.commit()

    chunk_size = 1000

    chat_guid_to_id: dict[str, object] = {}
    for offset in range(0, len(chats), chunk_size):
        chunk = chats[offset : offset + chunk_size]
        chat_rows = [
            WhatsAppChat(
                backup_id=backup.id,
                chat_guid=chat.chat_guid,
                title=chat.title,
                participant_count=chat.participant_count,
                last_message_at=chat.last_message_at,
                metadata=chat.metadata,
            )
            for chat in chunk
        ]
        session.add_all(chat_rows)
        await session.flush()
        for row in chat_rows:
            chat_guid_to_id[row.chat_guid] = row.id
        backup.indexing_progress = (backup.indexing_progress or 0) + len(chunk)
        await session.flush()
        await session.commit()

    messages_with_attachments = {(msg.chat_guid, msg.message_id) for msg, _ in attachments}
    message_key: dict[tuple[str, str], object] = {}

    for offset in range(0, len(messages), chunk_size):
        chunk = messages[offset : offset + chunk_size]
        message_rows: list[WhatsAppMessage] = []
        message_pairs: list[tuple[object, WhatsAppMessage]] = []
        for message in chunk:
            chat_id = chat_guid_to_id.get(message.chat_guid)
            if not chat_id:
                continue
            row = WhatsAppMessage(
                backup_id=backup.id,
                chat_id=chat_id,
                message_id=message.message_id,
                sender=message.sender,
                sender_name=message.sender_name,
                sent_at=message.sent_at,
                media_type=message.message_type,
                body=message.body,
                is_from_me=message.is_from_me,
                has_attachments=(message.chat_guid, message.message_id) in messages_with_attachments,
                metadata=message.metadata,
            )
            message_rows.append(row)
            message_pairs.append((message, row))

        if not message_rows:
            continue

        session.add_all(message_rows)
        await session.flush()
        for msg, msg_row in message_pairs:
            message_key[(msg.chat_guid, msg.message_id)] = msg_row.id

        backup.indexing_progress = (backup.indexing_progress or 0) + len(message_rows)
        await session.flush()
        await session.commit()

    for offset in range(0, len(attachments), chunk_size):
        chunk = attachments[offset : offset + chunk_size]
        attachment_rows: list[WhatsAppAttachment] = []
        for msg, attachment in chunk:
            message_id = message_key.get((msg.chat_guid, msg.message_id))
            if not message_id:
                continue
            attachment_rows.append(
                WhatsAppAttachment(
                    message_id=message_id,
                    file_id=attachment.file_id,
                    relative_path=attachment.relative_path,
                    mime_type=attachment.mime_type,
                    size_bytes=attachment.size_bytes,
                    metadata=attachment.metadata,
                )
            )

        if not attachment_rows:
            continue

        session.add_all(attachment_rows)
        await session.flush()
        backup.indexing_progress = (backup.indexing_progress or 0) + len(attachment_rows)
        await session.flush()
        await session.commit()


async def _ingest_messages(session: AsyncSession, backup: Backup, db_path: Path | None) -> None:
    if not db_path or not str(db_path).strip() or not db_path.exists():
        return
    backup.indexing_artifact = "messages"
    await session.flush()
    conversations, messages, attachments = messages_parser.parse_messages(db_path)

    conversation_rows = [
        MessageConversation(
            backup_id=backup.id,
            conversation_guid=conv.guid,
            service=conv.service,
            display_name=conv.display_name,
            last_message_at=conv.last_message_at,
            participant_handles=conv.participants,
        )
        for conv in conversations
    ]
    session.add_all(conversation_rows)
    await session.flush()

    conversation_map = {conv.guid: row.id for conv, row in zip(conversations, conversation_rows)}

    message_rows = []
    for msg in messages:
        conversation_id = conversation_map.get(msg.chat_guid)
        if not conversation_id:
            continue
        message_rows.append(
            Message(
                backup_id=backup.id,
                conversation_id=conversation_id,
                message_guid=msg.guid,
                sender=msg.sender,
                is_from_me=msg.is_from_me,
                sent_at=msg.sent_at,
                text=msg.text,
                has_attachments=bool(msg.attachments),
            )
        )
    session.add_all(message_rows)
    await session.flush()
    message_map = {msg.guid: row.id for msg, row in zip(messages, message_rows)}

    attachment_rows = []
    for msg, attachment in attachments:
        message_id = message_map.get(msg.guid)
        if not message_id:
            continue
        attachment_rows.append(
            MessageAttachment(
                message_id=message_id,
                file_id=attachment.file_id,
                relative_path=attachment.relative_path,
                mime_type=attachment.mime_type,
                size_bytes=attachment.size_bytes,
            )
        )
    session.add_all(attachment_rows)
    backup.indexing_progress = (backup.indexing_progress or 0) + 1
    await session.flush()


async def _ingest_notes(session: AsyncSession, backup: Backup, db_path: Path | None) -> None:
    if not db_path or not str(db_path).strip() or not db_path.exists():
        return
    backup.indexing_artifact = "notes"
    await session.flush()
    notes = notes_parser.parse_notes(db_path)
    note_rows = [
        Note(
            backup_id=backup.id,
            note_identifier=note.identifier,
            title=note.title,
            body=note.body,
            folder=note.folder,
            last_modified_at=note.modified_at,
            created_at=note.created_at,
            metadata=note.metadata,
        )
        for note in notes
    ]
    session.add_all(note_rows)
    backup.indexing_progress = (backup.indexing_progress or 0) + 1
    await session.flush()


async def _ingest_calendar(session: AsyncSession, backup: Backup, db_path: Path | None) -> None:
    if not db_path or not str(db_path).strip() or not db_path.exists():
        return
    backup.indexing_artifact = "calendar"
    await session.flush()
    calendars, events = calendar_parser.parse_calendar(db_path)
    calendar_rows = [
        Calendar(
            backup_id=backup.id,
            calendar_identifier=cal.identifier,
            name=cal.name,
            color=cal.color,
            source=cal.source,
        )
        for cal in calendars
    ]
    session.add_all(calendar_rows)
    await session.flush()
    calendar_map = {cal.identifier: row.id for cal, row in zip(calendars, calendar_rows)}

    event_rows = []
    for event in events:
        calendar_id = calendar_map.get(event.calendar_identifier)
        if not calendar_id:
            continue
        event_rows.append(
            CalendarEvent(
                backup_id=backup.id,
                calendar_id=calendar_id,
                event_identifier=event.identifier,
                title=event.title,
                location=event.location,
                notes=event.notes,
                starts_at=event.starts_at,
                ends_at=event.ends_at,
                is_all_day=event.is_all_day,
            )
        )
    session.add_all(event_rows)
    backup.indexing_progress = (backup.indexing_progress or 0) + 1
    await session.flush()


async def _ingest_contacts(session: AsyncSession, backup: Backup, db_path: Path | None) -> None:
    if not db_path or not str(db_path).strip() or not db_path.exists():
        return
    backup.indexing_artifact = "contacts"
    await session.flush()
    contacts = contacts_parser.parse_contacts(db_path)
    contact_rows = [
        Contact(
            backup_id=backup.id,
            contact_identifier=contact.identifier,
            first_name=contact.first_name,
            last_name=contact.last_name,
            company=contact.company,
            emails=contact.emails,
            phones=contact.phones,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
            avatar_file_id=contact.avatar_file_id,
        )
        for contact in contacts
    ]
    session.add_all(contact_rows)
    backup.indexing_progress = (backup.indexing_progress or 0) + 1
    await session.flush()


async def _add_search_rows(session: AsyncSession, backup: Backup, artifact: str, rows: Iterable[ArtifactSearchIndex]):
    for row in rows:
        if not row.artifact_ref:
            continue
        session.add(row)


def index_backup_job(backup_identifier: str, artifact_bundle_dir: str, artifact_files: dict[str, str]) -> None:
    asyncio.run(_index_backup_job(backup_identifier, artifact_bundle_dir, artifact_files))
