from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

from .base import apple_timestamp, sqlite_connection, table_exists


@dataclass(slots=True)
class SafariVisitRecord:
    identifier: str
    url: str | None
    title: str | None
    visited_at: datetime | None
    visit_count: int | None


def parse_safari_history(db_path: Path) -> List[SafariVisitRecord]:
    if not db_path.exists():
        return []

    records: List[SafariVisitRecord] = []
    with sqlite_connection(db_path) as conn:
        if not table_exists(conn, "history_items") or not table_exists(conn, "history_visits"):
            return []
        rows = conn.execute(
            """
            SELECT
                history_visits.id AS visit_id,
                history_items.url AS url,
                history_visits.title AS title,
                history_visits.visit_time AS visit_time,
                history_items.visit_count AS visit_count
            FROM history_visits
            JOIN history_items ON history_items.id = history_visits.history_item
            """
        ).fetchall()
        for row in rows:
            data = dict(row)
            records.append(
                SafariVisitRecord(
                    identifier=str(data.get("visit_id")),
                    url=data.get("url"),
                    title=data.get("title"),
                    visited_at=apple_timestamp(data.get("visit_time")),
                    visit_count=data.get("visit_count"),
                )
            )
    return records
