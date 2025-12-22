from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, List, Tuple

from .base import apple_timestamp, sqlite_connection, table_exists


@dataclass(slots=True)
class WhatsAppChatRecord:
    chat_guid: str
    title: str | None
    participant_count: int | None
    last_message_at: datetime | None
    metadata: dict[str, Any]


@dataclass(slots=True)
class WhatsAppMessageRecord:
    chat_guid: str
    message_id: str
    sender: str | None
    sent_at: datetime | None
    message_type: str | None
    body: str | None
    is_from_me: bool
    metadata: dict[str, Any]


@dataclass(slots=True)
class WhatsAppAttachmentRecord:
    file_id: str | None
    relative_path: str | None
    mime_type: str | None
    size_bytes: int | None
    metadata: dict[str, Any]


def parse_whatsapp(db_path: Path) -> Tuple[
    List[WhatsAppChatRecord],
    List[WhatsAppMessageRecord],
    List[Tuple[WhatsAppMessageRecord, WhatsAppAttachmentRecord]],
]:
    if not db_path.exists():
        return [], [], []

    chats: list[WhatsAppChatRecord] = []
    messages: list[WhatsAppMessageRecord] = []
    attachments: list[tuple[WhatsAppMessageRecord, WhatsAppAttachmentRecord]] = []

    with sqlite_connection(db_path) as conn:
        if not table_exists(conn, "ZWACHATSESSION"):
            return [], [], []
        if not table_exists(conn, "ZWAMESSAGE"):
            return [], [], []

        chat_rows = conn.execute("SELECT * FROM ZWACHATSESSION").fetchall()
        chat_pk_to_guid: dict[int, str] = {}
        for row in chat_rows:
            data = dict(row)
            chat_guid = str(
                data.get("ZCONTACTJID")
                or data.get("ZIDENTIFIER")
                or data.get("ZGROUPEVENTID")
                or data.get("Z_PK")
            )
            chat_pk_to_guid[data.get("Z_PK")] = chat_guid
            chats.append(
                WhatsAppChatRecord(
                    chat_guid=chat_guid,
                    title=data.get("ZPARTNERNAME") or data.get("ZPARTNERDISPLAYNAME"),
                    participant_count=data.get("ZPARTICIPANTSCOUNT"),
                    last_message_at=apple_timestamp(
                        data.get("ZLASTMESSAGEDATE") or data.get("ZLASTMESSAGETIME")
                    ),
                    metadata={
                        key: data.get(key)
                        for key in ("ZGROUPID", "ZGROUPMEMBER", "ZISARCHIVED")
                        if key in data
                    },
                )
            )

        message_rows = conn.execute("SELECT * FROM ZWAMESSAGE").fetchall()
        message_pk_to_record: dict[int, WhatsAppMessageRecord] = {}

        for row in message_rows:
            data = dict(row)
            chat_pk = data.get("ZCHATSESSION")
            chat_guid = chat_pk_to_guid.get(chat_pk, str(chat_pk))
            message_id = str(data.get("ZMESSAGEID") or data.get("ZSTANZAID") or data.get("Z_PK"))
            sent_raw = data.get("ZMESSAGEDATE") or data.get("ZMESSAGETIME")
            sent_at = apple_timestamp(sent_raw)
            message = WhatsAppMessageRecord(
                chat_guid=chat_guid,
                message_id=message_id,
                sender=data.get("ZFROMJID") or data.get("ZSENDERJID"),
                sent_at=sent_at,
                message_type=str(data.get("ZGROUPEVENTTYPE") or data.get("ZMESSAGETYPE")),
                body=data.get("ZTEXT"),
                is_from_me=bool(data.get("ZISFROMME")),
                metadata={
                    key: data.get(key)
                    for key in ("ZISREAD", "ZMESSAGEDATE", "ZMESSAGEDATEVALUE", "ZSTARRED")
                    if key in data
                },
            )
            messages.append(message)
            message_pk_to_record[data.get("Z_PK")] = message

        if table_exists(conn, "ZWAMEDIAITEM"):
            media_rows = conn.execute("SELECT * FROM ZWAMEDIAITEM").fetchall()
            for row in media_rows:
                data = dict(row)
                message_fk = data.get("ZMESSAGE") or data.get("ZMESSAGEID")
                message = message_pk_to_record.get(message_fk)
                if not message:
                    continue
                attachment = WhatsAppAttachmentRecord(
                    file_id=str(data.get("ZFILEHASH") or data.get("Z_PK")),
                    relative_path=data.get("ZMEDIALOCALPATH") or data.get("ZLOCALPATH"),
                    mime_type=data.get("ZMEDIAMIMETYPE"),
                    size_bytes=data.get("ZMEDIAFILESIZE") or data.get("ZMEDIASIZE"),
                    metadata={
                        key: data.get(key)
                        for key in ("ZDURATION", "ZWIDTH", "ZHEIGHT", "ZTHUMBNAIL")
                        if key in data
                    },
                )
                attachments.append((message, attachment))

    return chats, messages, attachments
