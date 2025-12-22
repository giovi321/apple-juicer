from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from .base import apple_timestamp, sqlite_connection, table_exists


@dataclass(slots=True)
class NoteRecord:
    identifier: str
    title: str | None
    body: str | None
    folder: str | None
    created_at: datetime | None
    modified_at: datetime | None
    metadata: Dict[str, Any]


def parse_notes(db_path: Path) -> List[NoteRecord]:
    if not db_path.exists():
        return []

    notes: List[NoteRecord] = []
    with sqlite_connection(db_path) as conn:
        if not table_exists(conn, "ZNOTE"):
            return []

        account_titles = _load_account_titles(conn)
        folder_titles = _load_folder_titles(conn, account_titles)

        rows = conn.execute(
            """
            SELECT
                ZNOTE.Z_PK AS note_pk,
                ZNOTE.ZIDENTIFIER,
                ZNOTE.ZTITLE1,
                ZNOTE.ZTITLE2,
                ZNOTE.ZBODY,
                ZNOTE.ZFOLDER,
                ZNOTE.ZACCOUNT,
                ZNOTE.ZCREATIONDATE,
                ZNOTE.ZMODIFICATIONDATE
            FROM ZNOTE
            """
        ).fetchall()

        for row in rows:
            data = dict(row)
            identifier = data.get("ZIDENTIFIER") or f"note-{data['note_pk']}"
            folder = folder_titles.get(data.get("ZFOLDER"))
            account = account_titles.get(data.get("ZACCOUNT"))

            body_text = data.get("ZBODY")
            if isinstance(body_text, bytes):
                try:
                    body_text = body_text.decode("utf-8", errors="ignore")
                except Exception:
                    body_text = None

            notes.append(
                NoteRecord(
                    identifier=identifier,
                    title=data.get("ZTITLE1") or data.get("ZTITLE2"),
                    body=body_text,
                    folder=folder or account,
                    created_at=apple_timestamp(data.get("ZCREATIONDATE")),
                    modified_at=apple_timestamp(data.get("ZMODIFICATIONDATE")),
                    metadata={
                        "account": account,
                        "folder_id": data.get("ZFOLDER"),
                        "account_id": data.get("ZACCOUNT"),
                    },
                )
            )

    return notes


def _load_account_titles(conn) -> dict[int, str]:
    if not table_exists(conn, "ZACCOUNT"):
        return {}
    rows = conn.execute("SELECT Z_PK, ZNAME FROM ZACCOUNT").fetchall()
    return {row["Z_PK"]: row["ZNAME"] for row in rows}


def _load_folder_titles(conn, account_titles: dict[int, str]) -> dict[int, str]:
    if not table_exists(conn, "ZFOLDER"):
        return {}
    rows = conn.execute("SELECT Z_PK, ZNAME, ZACCOUNT FROM ZFOLDER").fetchall()
    folders: dict[int, str] = {}
    for row in rows:
        name = row["ZNAME"]
        account_name = account_titles.get(row["ZACCOUNT"])
        if name and account_name:
            folders[row["Z_PK"]] = f"{account_name} / {name}"
        elif name:
            folders[row["Z_PK"]] = name
        elif account_name:
            folders[row["Z_PK"]] = account_name
    return folders
