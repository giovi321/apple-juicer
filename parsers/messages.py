from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from .base import apple_timestamp, sqlite_connection, table_exists


@dataclass(slots=True)
class ConversationRecord:
    guid: str
    service: str | None
    display_name: str | None
    last_message_at: datetime | None
    participants: list[str]


@dataclass(slots=True)
class MessageRecord:
    guid: str
    chat_guid: str
    sender: str | None
    is_from_me: bool
    sent_at: datetime | None
    text: str | None
    attachments: list["AttachmentRecord"]


@dataclass(slots=True)
class AttachmentRecord:
    file_id: str | None
    relative_path: str | None
    mime_type: str | None
    size_bytes: int | None


def parse_messages(
    db_path: Path,
) -> Tuple[List[ConversationRecord], List[MessageRecord], List[Tuple[MessageRecord, AttachmentRecord]]]:
    if not db_path.exists():
        return [], [], []

    with sqlite_connection(db_path) as conn:
        if not table_exists(conn, "chat") or not table_exists(conn, "message"):
            return [], [], []

        handles = _load_handles(conn)
        participants_lookup = _chat_participants(conn, handles)
        conversations = _load_chats(conn, participants_lookup)
        chat_guid_map = {chat.guid: chat for chat in conversations}

        messages = _load_messages(conn, chat_guid_map, handles)
        attachments = _load_attachments(conn, messages)

    return conversations, messages, attachments


def _load_handles(conn) -> dict[int, str]:
    if not table_exists(conn, "handle"):
        return {}
    handle_rows = conn.execute("SELECT ROWID, id FROM handle").fetchall()
    return {row["ROWID"]: row["id"] for row in handle_rows if row["id"]}


def _chat_participants(conn, handles: dict[int, str]) -> dict[int, list[str]]:
    if not (table_exists(conn, "chat_handle_join") and handles):
        return {}
    rows = conn.execute("SELECT chat_id, handle_id FROM chat_handle_join").fetchall()
    mapping: dict[int, list[str]] = {}
    for row in rows:
        chat_id = row["chat_id"]
        handle_id = row["handle_id"]
        handle = handles.get(handle_id)
        if not handle:
            continue
        mapping.setdefault(chat_id, []).append(handle)
    return mapping


def _load_chats(conn, participants_lookup: dict[int, list[str]]) -> list[ConversationRecord]:
    rows = conn.execute("SELECT ROWID, guid, service_name, display_name, last_read_message_timestamp FROM chat").fetchall()
    chats: list[ConversationRecord] = []
    for row in rows:
        guid = row["guid"] or f"chat-{row['ROWID']}"
        chats.append(
            ConversationRecord(
                guid=guid,
                service=row["service_name"],
                display_name=row["display_name"],
                last_message_at=apple_timestamp(row["last_read_message_timestamp"]),
                participants=participants_lookup.get(row["ROWID"], []),
            )
        )
    return chats


def _load_messages(conn, chat_guid_map: dict[str, ConversationRecord], handles: dict[int, str]) -> list[MessageRecord]:
    rows = conn.execute(
        """
        SELECT
            message.ROWID AS message_rowid,
            message.guid,
            message.date,
            message.service,
            message.text,
            message.is_from_me,
            chat.guid AS chat_guid,
            handle.id AS sender_handle
        FROM message
        LEFT JOIN chat_message_join cmj ON cmj.message_id = message.ROWID
        LEFT JOIN chat ON chat.ROWID = cmj.chat_id
        LEFT JOIN handle ON handle.ROWID = message.handle_id
        ORDER BY message.date ASC
        """
    ).fetchall()

    messages: list[MessageRecord] = []
    for row in rows:
        chat_guid = row["chat_guid"] or ""
        if chat_guid not in chat_guid_map:
            # fallback to guid from row
            chat_guid = chat_guid or "chat-unknown"
        msg_guid = row["guid"] or f"message-{row['message_rowid']}"
        sent_at = apple_timestamp(row["date"])
        message = MessageRecord(
            guid=msg_guid,
            chat_guid=chat_guid,
            sender=row["sender_handle"],
            is_from_me=bool(row["is_from_me"]),
            sent_at=sent_at,
            text=row["text"],
            attachments=[],
        )
        messages.append(message)
    return messages


def _load_attachments(conn, messages: list[MessageRecord]):
    if not (table_exists(conn, "attachment") and table_exists(conn, "message_attachment_join")):
        return []

    message_map = {msg.guid: msg for msg in messages}
    rows = conn.execute(
        """
        SELECT
            attachment.ROWID AS attachment_rowid,
            attachment.guid AS attachment_guid,
            attachment.filename,
            attachment.mime_type,
            attachment.total_bytes,
            attachment.transfer_name,
            message.guid AS message_guid
        FROM attachment
        JOIN message_attachment_join maj ON maj.attachment_id = attachment.ROWID
        JOIN message ON message.ROWID = maj.message_id
        """
    ).fetchall()

    attachment_pairs: list[tuple[MessageRecord, AttachmentRecord]] = []
    for row in rows:
        message = message_map.get(row["message_guid"])
        if not message:
            continue
        attachment = AttachmentRecord(
            file_id=row["attachment_guid"] or row["attachment_rowid"],
            relative_path=row["filename"] or row["transfer_name"],
            mime_type=row["mime_type"],
            size_bytes=row["total_bytes"],
        )
        message.attachments.append(attachment)
        attachment_pairs.append((message, attachment))
    return attachment_pairs
