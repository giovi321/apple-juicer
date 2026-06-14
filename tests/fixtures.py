"""Builders for minimal synthetic iOS artifact SQLite databases.

Each builder writes the smallest schema + rows that the matching parser in
``parsers/`` actually reads, so the indexing pipeline can be exercised
end-to-end without a real (multi-GB, encrypted) iOS backup.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Apple Core Data timestamps are seconds since 2001-01-01; nanosecond-scale
# values (chat.db) are auto-detected and downscaled by parsers.base.
_APPLE_SECONDS = 700_000_000.0


def make_calendar_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE Calendar (ROWID INTEGER PRIMARY KEY, title TEXT, color TEXT, source TEXT, uid TEXT);
        CREATE TABLE Event (
            ROWID INTEGER PRIMARY KEY, uid TEXT, summary TEXT, location TEXT, description TEXT,
            start_date REAL, end_date REAL, all_day INTEGER, calendar_id INTEGER
        );
        INSERT INTO Calendar (ROWID, title, color, source, uid)
            VALUES (1, 'Home', '#ff0000', 'iCloud', 'cal-uid-1');
        INSERT INTO Event (ROWID, uid, summary, location, description, start_date, end_date, all_day, calendar_id)
            VALUES (1, 'evt-1', 'Meeting', 'Office', 'Sync', 700000000.0, 700003600.0, 0, 1);
        INSERT INTO Event (ROWID, uid, summary, location, description, start_date, end_date, all_day, calendar_id)
            VALUES (2, 'evt-2', 'Lunch', 'Cafe', NULL, 700100000.0, 700103600.0, 0, 1);
        """
    )
    conn.commit()
    conn.close()


def make_photos_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE ZASSET (
            Z_PK INTEGER PRIMARY KEY, ZUUID TEXT, ZORIGINALFILENAME TEXT, ZDIRECTORY TEXT,
            ZFILEHASH TEXT, ZDATECREATED REAL, ZPIXELWIDTH INTEGER, ZPIXELHEIGHT INTEGER,
            ZKIND INTEGER, ZLATITUDE REAL, ZLONGITUDE REAL
        );
        INSERT INTO ZASSET VALUES
            (1, 'uuid-1', 'IMG_0001.JPG', 'DCIM/100APPLE', 'hash1', 700000000.0, 4032, 3024, 0, 47.1, 8.5);
        INSERT INTO ZASSET VALUES
            (2, 'uuid-2', 'IMG_0002.MOV', 'DCIM/100APPLE', 'hash2', 700100000.0, 1920, 1080, 1, NULL, NULL);
        """
    )
    conn.commit()
    conn.close()


def make_notes_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE ZACCOUNT (Z_PK INTEGER PRIMARY KEY, ZNAME TEXT);
        CREATE TABLE ZFOLDER (Z_PK INTEGER PRIMARY KEY, ZNAME TEXT, ZACCOUNT INTEGER);
        CREATE TABLE ZNOTE (
            Z_PK INTEGER PRIMARY KEY, ZIDENTIFIER TEXT, ZTITLE1 TEXT, ZTITLE2 TEXT, ZBODY TEXT,
            ZFOLDER INTEGER, ZACCOUNT INTEGER, ZCREATIONDATE REAL, ZMODIFICATIONDATE REAL
        );
        INSERT INTO ZACCOUNT VALUES (1, 'iCloud');
        INSERT INTO ZFOLDER VALUES (1, 'Notes', 1);
        INSERT INTO ZNOTE VALUES (1, 'note-1', 'Shopping', NULL, 'Milk, eggs', 1, 1, 700000000.0, 700000500.0);
        INSERT INTO ZNOTE VALUES (2, 'note-2', 'Ideas', NULL, 'Build a thing', 1, 1, 700100000.0, 700100500.0);
        """
    )
    conn.commit()
    conn.close()


def make_contacts_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE ABPerson (
            ROWID INTEGER PRIMARY KEY, First TEXT, Last TEXT, Organization TEXT,
            CreationDate REAL, ModificationDate REAL, ImageURI TEXT
        );
        CREATE TABLE ABMultiValueLabel (ROWID INTEGER PRIMARY KEY, value TEXT);
        CREATE TABLE ABMultiValue (record_id INTEGER, property INTEGER, label INTEGER, value TEXT);
        INSERT INTO ABPerson VALUES (1, 'Ada', 'Lovelace', 'Analytical Engines', 700000000.0, 700000500.0, NULL);
        INSERT INTO ABMultiValueLabel VALUES (1, '_$!<Mobile>!$_');
        INSERT INTO ABMultiValue VALUES (1, 3, 1, '+15550001111');
        INSERT INTO ABMultiValue VALUES (1, 4, 1, 'ada@example.com');
        """
    )
    conn.commit()
    conn.close()


def make_whatsapp_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE ZWACHATSESSION (
            Z_PK INTEGER PRIMARY KEY, ZCONTACTJID TEXT, ZPARTNERNAME TEXT,
            ZPARTICIPANTSCOUNT INTEGER, ZLASTMESSAGEDATE REAL, ZISARCHIVED INTEGER
        );
        CREATE TABLE ZWAMESSAGE (
            Z_PK INTEGER PRIMARY KEY, ZCHATSESSION INTEGER, ZMESSAGEID TEXT, ZMESSAGEDATE REAL,
            ZMESSAGETYPE INTEGER, ZTEXT TEXT, ZISFROMME INTEGER, ZFROMJID TEXT, ZISREAD INTEGER
        );
        CREATE TABLE ZWAMEDIAITEM (
            Z_PK INTEGER PRIMARY KEY, ZMESSAGE INTEGER, ZFILEHASH TEXT, ZMEDIALOCALPATH TEXT,
            ZMEDIAMIMETYPE TEXT, ZMEDIAFILESIZE INTEGER
        );
        INSERT INTO ZWACHATSESSION VALUES (1, '15550001111@s.whatsapp.net', 'Ada', 2, 700000000.0, 0);
        INSERT INTO ZWAMESSAGE VALUES
            (1, 1, 'msg-1', 700000000.0, 0, 'Hi there', 0, '15550001111@s.whatsapp.net', 1);
        INSERT INTO ZWAMESSAGE VALUES
            (2, 1, 'msg-2', 700000100.0, 0, 'See attached', 1, NULL, 1);
        INSERT INTO ZWAMEDIAITEM VALUES (1, 2, 'mediahash1', 'Media/photo.jpg', 'image/jpeg', 12345);
        """
    )
    conn.commit()
    conn.close()


def make_calls_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE ZCALLRECORD (
            Z_PK INTEGER PRIMARY KEY, ZUNIQUE_ID TEXT, ZADDRESS TEXT, ZNAME TEXT,
            ZDATE REAL, ZDURATION REAL, ZORIGINATED INTEGER, ZANSWERED INTEGER, ZSERVICE_PROVIDER TEXT
        );
        INSERT INTO ZCALLRECORD VALUES
            (1, 'call-1', '+15550001111', 'Ada', 700000000.0, 65.0, 1, 1, 'com.apple.Telephony');
        INSERT INTO ZCALLRECORD VALUES
            (2, 'call-2', '+15550002222', NULL, 700100000.0, 0.0, 0, 0, 'com.apple.Telephony');
        """
    )
    conn.commit()
    conn.close()


def make_safari_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE history_items (id INTEGER PRIMARY KEY, url TEXT, visit_count INTEGER);
        CREATE TABLE history_visits (id INTEGER PRIMARY KEY, history_item INTEGER, title TEXT, visit_time REAL);
        INSERT INTO history_items VALUES (1, 'https://example.com', 3);
        INSERT INTO history_items VALUES (2, 'https://apple.com', 1);
        INSERT INTO history_visits VALUES (1, 1, 'Example Domain', 700000000.0);
        INSERT INTO history_visits VALUES (2, 1, 'Example Domain', 700050000.0);
        INSERT INTO history_visits VALUES (3, 2, 'Apple', 700100000.0);
        """
    )
    conn.commit()
    conn.close()


def make_messages_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE handle (ROWID INTEGER PRIMARY KEY, id TEXT);
        CREATE TABLE chat (
            ROWID INTEGER PRIMARY KEY, guid TEXT, service_name TEXT, display_name TEXT,
            last_read_message_timestamp INTEGER
        );
        CREATE TABLE chat_handle_join (chat_id INTEGER, handle_id INTEGER);
        CREATE TABLE message (
            ROWID INTEGER PRIMARY KEY, guid TEXT, date INTEGER, service TEXT, text TEXT,
            is_from_me INTEGER, handle_id INTEGER
        );
        CREATE TABLE chat_message_join (chat_id INTEGER, message_id INTEGER);
        CREATE TABLE attachment (
            ROWID INTEGER PRIMARY KEY, guid TEXT, filename TEXT, mime_type TEXT,
            total_bytes INTEGER, transfer_name TEXT
        );
        CREATE TABLE message_attachment_join (attachment_id INTEGER, message_id INTEGER);

        INSERT INTO handle VALUES (1, '+15550002222');
        INSERT INTO chat VALUES (1, 'iMessage;-;+15550002222', 'iMessage', 'Grace', 600000000000000000);
        INSERT INTO chat_handle_join VALUES (1, 1);
        INSERT INTO message VALUES (1, 'imsg-1', 600000000000000000, 'iMessage', 'Hello from Grace', 0, 1);
        INSERT INTO message VALUES (2, 'imsg-2', 600000000100000000, 'iMessage', 'Photo attached', 1, NULL);
        INSERT INTO chat_message_join VALUES (1, 1);
        INSERT INTO chat_message_join VALUES (1, 2);
        INSERT INTO attachment VALUES (1, 'att-1', '~/Library/SMS/Attachments/x.jpg', 'image/jpeg', 5555, 'x.jpg');
        INSERT INTO message_attachment_join VALUES (1, 2);
        """
    )
    conn.commit()
    conn.close()


def build_all(decrypted_dir: Path) -> dict[str, str]:
    """Write every artifact DB into ``decrypted_dir`` and return the
    artifact_files mapping that worker.tasks.index_backup_job expects."""
    decrypted_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "photos": decrypted_dir / "Photos.sqlite",
        "whatsapp": decrypted_dir / "ChatStorage.sqlite",
        "messages": decrypted_dir / "chat.db",
        "notes": decrypted_dir / "notes.sqlite",
        "calendar": decrypted_dir / "Calendar.sqlite",
        "contacts": decrypted_dir / "AddressBook.sqlitedb",
        "calls": decrypted_dir / "CallHistory.storedata",
        "safari": decrypted_dir / "History.db",
    }
    make_photos_db(files["photos"])
    make_whatsapp_db(files["whatsapp"])
    make_messages_db(files["messages"])
    make_notes_db(files["notes"])
    make_calendar_db(files["calendar"])
    make_contacts_db(files["contacts"])
    make_calls_db(files["calls"])
    make_safari_db(files["safari"])
    return {key: str(value) for key, value in files.items()}
