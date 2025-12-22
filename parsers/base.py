from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)


def apple_timestamp(value: float | int | None) -> datetime | None:
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if value > 10_000_000_000:  # nanoseconds
        value = value / 1_000_000_000
    return APPLE_EPOCH + timedelta(seconds=value)


def unix_timestamp(value: float | int | None) -> datetime | None:
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if value > 10_000_000_000:  # milliseconds or nanoseconds
        value = value / 1000
    return datetime.fromtimestamp(value, tz=timezone.utc)


@contextmanager
def sqlite_connection(path: Path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def available_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def columns_subset(conn: sqlite3.Connection, table: str, desired: Iterable[str]) -> list[str]:
    cols = available_columns(conn, table)
    return [col for col in desired if col in cols]


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cursor = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? COLLATE NOCASE",
        (table,),
    )
    return cursor.fetchone() is not None
