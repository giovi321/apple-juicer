from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

from .base import apple_timestamp, sqlite_connection, table_exists


@dataclass(slots=True)
class CallRecord:
    identifier: str
    address: str | None
    name: str | None
    occurred_at: datetime | None
    duration_seconds: int | None
    is_outgoing: bool
    answered: bool
    service: str | None


def _decode_address(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray, memoryview)):
        try:
            value = bytes(value).decode("utf-8", errors="ignore")
        except Exception:
            return None
    text = str(value).strip()
    return text or None


def parse_call_history(db_path: Path) -> List[CallRecord]:
    if not db_path.exists():
        return []

    records: List[CallRecord] = []
    with sqlite_connection(db_path) as conn:
        if not table_exists(conn, "ZCALLRECORD"):
            return []
        for row in conn.execute("SELECT * FROM ZCALLRECORD").fetchall():
            data = dict(row)
            identifier = str(data.get("ZUNIQUE_ID") or data.get("Z_PK"))
            duration = data.get("ZDURATION")
            records.append(
                CallRecord(
                    identifier=identifier,
                    address=_decode_address(data.get("ZADDRESS")),
                    name=data.get("ZNAME"),
                    occurred_at=apple_timestamp(data.get("ZDATE")),
                    duration_seconds=int(duration) if duration is not None else None,
                    is_outgoing=bool(data.get("ZORIGINATED")),
                    answered=bool(data.get("ZANSWERED")),
                    service=data.get("ZSERVICE_PROVIDER"),
                )
            )
    return records
