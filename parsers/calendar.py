from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

from .base import apple_timestamp, sqlite_connection, table_exists


@dataclass(slots=True)
class CalendarRecord:
    identifier: str
    name: str
    color: str | None
    source: str | None


@dataclass(slots=True)
class CalendarEventRecord:
    identifier: str
    calendar_identifier: str
    title: str | None
    location: str | None
    notes: str | None
    starts_at: datetime | None
    ends_at: datetime | None
    is_all_day: bool


def parse_calendar(db_path: Path) -> tuple[list[CalendarRecord], list[CalendarEventRecord]]:
    if not db_path.exists():
        return [], []

    with sqlite_connection(db_path) as conn:
        if not table_exists(conn, "Calendar") or not table_exists(conn, "Event"):
            return [], []

        calendars = _load_calendars(conn)
        events = _load_events(conn)

    return calendars, events


def _load_calendars(conn) -> list[CalendarRecord]:
    rows = conn.execute("SELECT ROWID, title, color, source, uid FROM Calendar").fetchall()
    records: list[CalendarRecord] = []
    for row in rows:
        identifier = row["uid"] or f"calendar-{row['ROWID']}"
        records.append(
            CalendarRecord(
                identifier=identifier,
                name=row["title"] or identifier,
                color=row["color"],
                source=row["source"],
            )
        )
    return records


def _load_events(conn) -> list[CalendarEventRecord]:
    rows = conn.execute(
        """
        SELECT
            Event.ROWID AS event_rowid,
            Event.uid,
            Event.summary,
            Event.location,
            Event.description,
            Event.start_date,
            Event.end_date,
            Event.all_day,
            Calendar.uid AS calendar_uid,
            Calendar.ROWID AS calendar_rowid
        FROM Event
        LEFT JOIN Calendar ON Calendar.ROWID = Event.calendar_id
        """
    ).fetchall()

    records: list[CalendarEventRecord] = []
    for row in rows:
        calendar_identifier = row["calendar_uid"] or f"calendar-{row['calendar_rowid']}"
        identifier = row["uid"] or f"event-{row['event_rowid']}"
        records.append(
            CalendarEventRecord(
                identifier=identifier,
                calendar_identifier=calendar_identifier,
                title=row["summary"],
                location=row["location"],
                notes=row["description"],
                starts_at=apple_timestamp(row["start_date"]),
                ends_at=apple_timestamp(row["end_date"]),
                is_all_day=bool(row["all_day"]),
            )
        )
    return records
