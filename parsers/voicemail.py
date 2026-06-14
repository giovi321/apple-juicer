from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

from .base import sqlite_connection, table_exists, unix_timestamp


@dataclass(slots=True)
class VoicemailRecord:
    identifier: str
    sender: str | None
    received_at: datetime | None
    duration_seconds: int | None
    trashed: bool


def parse_voicemail(db_path: Path) -> List[VoicemailRecord]:
    if not db_path.exists():
        return []

    records: List[VoicemailRecord] = []
    with sqlite_connection(db_path) as conn:
        if not table_exists(conn, "voicemail"):
            return []
        for row in conn.execute("SELECT * FROM voicemail").fetchall():
            data = dict(row)
            duration = data.get("duration")
            trashed_date = data.get("trashed_date")
            records.append(
                VoicemailRecord(
                    identifier=str(data.get("ROWID")),
                    sender=data.get("sender") or data.get("callback_num"),
                    received_at=unix_timestamp(data.get("date")),
                    duration_seconds=int(duration) if duration is not None else None,
                    trashed=bool(trashed_date),
                )
            )
    return records
