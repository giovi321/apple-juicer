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
    sender_name: str | None
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


import logging

logger = logging.getLogger(__name__)


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
        
        # Log available tables for debugging
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        logger.info(f"WhatsApp DB tables: {[t[0] for t in tables]}")
        
        # Log ZWAMESSAGE columns for debugging
        msg_cols = conn.execute("PRAGMA table_info(ZWAMESSAGE)").fetchall()
        logger.info(f"ZWAMESSAGE columns: {[c[1] for c in msg_cols]}")
        
        # Check for profile/contact tables and build JID -> name lookup
        jid_to_name: dict[str, str] = {}
        
        if table_exists(conn, "ZWAPROFILEPUSHNAME"):
            logger.info("Found ZWAPROFILEPUSHNAME table")
            profile_cols = conn.execute("PRAGMA table_info(ZWAPROFILEPUSHNAME)").fetchall()
            logger.info(f"ZWAPROFILEPUSHNAME columns: {[c[1] for c in profile_cols]}")
            profile_rows = conn.execute("SELECT * FROM ZWAPROFILEPUSHNAME").fetchall()
            for row in profile_rows:
                pdata = dict(row)
                jid = pdata.get("ZJID") or pdata.get("ZCONTACTJID")
                name = pdata.get("ZPUSHNAME") or pdata.get("ZNAME")
                if jid and name:
                    jid_to_name[jid] = name
            logger.info(f"Loaded {len(jid_to_name)} profile push names")
        
        if table_exists(conn, "ZWAGROUPMEMBER"):
            logger.info("Found ZWAGROUPMEMBER table")
            member_cols = conn.execute("PRAGMA table_info(ZWAGROUPMEMBER)").fetchall()
            logger.info(f"ZWAGROUPMEMBER columns: {[c[1] for c in member_cols]}")

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

        # Build lookups for group members: PK -> JID and (chat_pk, member_jid) -> name
        group_member_pk_to_jid: dict[int, str] = {}  # Z_PK -> ZMEMBERJID
        group_member_names: dict[tuple[int, str], str] = {}  # (chat_pk, member_jid) -> name
        if table_exists(conn, "ZWAGROUPMEMBER"):
            member_rows = conn.execute("SELECT * FROM ZWAGROUPMEMBER").fetchall()
            for row in member_rows:
                mdata = dict(row)
                member_pk = mdata.get("Z_PK")
                chat_fk = mdata.get("ZCHATSESSION")
                member_jid = mdata.get("ZMEMBERJID")
                member_name = mdata.get("ZCONTACTNAME") or mdata.get("ZPUSHNAME")
                if member_pk and member_jid:
                    group_member_pk_to_jid[member_pk] = member_jid
                if chat_fk and member_jid and member_name:
                    group_member_names[(chat_fk, member_jid)] = member_name

        # Build a lookup for chat partner names (for 1:1 chats)
        chat_pk_to_partner_name: dict[int, str] = {}
        chat_pk_to_partner_jid: dict[int, str] = {}
        for row in chat_rows:
            data = dict(row)
            pk = data.get("Z_PK")
            partner_name = data.get("ZPARTNERNAME") or data.get("ZPARTNERDISPLAYNAME")
            partner_jid = data.get("ZCONTACTJID")
            if pk and partner_name:
                chat_pk_to_partner_name[pk] = partner_name
            if pk and partner_jid:
                chat_pk_to_partner_jid[pk] = partner_jid

        message_rows = conn.execute("SELECT * FROM ZWAMESSAGE").fetchall()
        message_pk_to_record: dict[int, WhatsAppMessageRecord] = {}
        
        # Log sample message data for debugging (first 3 non-from-me messages)
        sample_count = 0
        for row in message_rows:
            if sample_count >= 3:
                break
            data = dict(row)
            if not data.get("ZISFROMME"):
                logger.info(f"Sample message data: ZFROMJID={data.get('ZFROMJID')}, ZSENDERJID={data.get('ZSENDERJID')}, ZPUSHNAME={data.get('ZPUSHNAME')}, ZTEXT={str(data.get('ZTEXT'))[:50] if data.get('ZTEXT') else None}")
                sample_count += 1

        for row in message_rows:
            data = dict(row)
            chat_pk = data.get("ZCHATSESSION")
            chat_guid = chat_pk_to_guid.get(chat_pk, str(chat_pk))
            message_id = str(data.get("ZMESSAGEID") or data.get("ZSTANZAID") or data.get("Z_PK"))
            sent_raw = data.get("ZMESSAGEDATE") or data.get("ZMESSAGETIME")
            sent_at = apple_timestamp(sent_raw)
            
            # Get sender JID - for group chats, use ZGROUPMEMBER FK to get actual sender
            # ZFROMJID often contains the group JID, not the individual sender
            group_member_fk = data.get("ZGROUPMEMBER")
            if group_member_fk and group_member_fk in group_member_pk_to_jid:
                # Group chat: get sender JID from group member table
                sender_jid = group_member_pk_to_jid[group_member_fk]
            else:
                # 1:1 chat or fallback: use ZFROMJID
                raw_jid = data.get("ZFROMJID") or data.get("ZSENDERJID")
                # For 1:1 chats, ZFROMJID might be the chat JID, use partner JID instead
                if raw_jid and "@g.us" in str(raw_jid):
                    # This is a group JID, try to get partner JID for 1:1 chats
                    sender_jid = chat_pk_to_partner_jid.get(chat_pk) if chat_pk else raw_jid
                else:
                    sender_jid = raw_jid
            
            # Get sender name - try multiple sources:
            # 1. Profile push name lookup (from ZWAPROFILEPUSHNAME table) - most reliable
            # 2. Group member lookup (for group chats)
            # 3. Chat partner name (for 1:1 chats where sender is the partner)
            # Note: ZPUSHNAME in ZWAMESSAGE is often a blob, not usable
            sender_name = None
            if sender_jid:
                # Try profile push name lookup first
                sender_name = jid_to_name.get(sender_jid)
            if not sender_name and chat_pk and sender_jid:
                # Try group member lookup
                sender_name = group_member_names.get((chat_pk, sender_jid))
            if not sender_name and chat_pk:
                # For 1:1 chats, if sender is not me, use the chat partner name
                is_from_me = bool(data.get("ZISFROMME"))
                if not is_from_me:
                    sender_name = chat_pk_to_partner_name.get(chat_pk)
            
            message = WhatsAppMessageRecord(
                chat_guid=chat_guid,
                message_id=message_id,
                sender=sender_jid,
                sender_name=sender_name,
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
