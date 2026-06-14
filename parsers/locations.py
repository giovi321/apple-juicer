from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

from .base import apple_timestamp, sqlite_connection, table_exists

# routined "significant locations" moment tables, newest naming first.
_MOMENT_TABLES = ("ZRTCLLOCATIONMOMENT", "ZRTCLLOCATIONMOMENTCANDIDATE")


@dataclass(slots=True)
class LocationRecord:
    identifier: str
    latitude: float | None
    longitude: float | None
    altitude: float | None
    speed: float | None
    horizontal_accuracy: float | None
    recorded_at: datetime | None


def parse_locations(db_path: Path) -> List[LocationRecord]:
    if not db_path.exists():
        return []

    records: List[LocationRecord] = []
    with sqlite_connection(db_path) as conn:
        table = next((name for name in _MOMENT_TABLES if table_exists(conn, name)), None)
        if not table:
            return []
        for row in conn.execute(f"SELECT * FROM {table}").fetchall():
            data = dict(row)
            latitude = data.get("ZLATITUDE")
            longitude = data.get("ZLONGITUDE")
            if latitude is None or longitude is None:
                continue
            records.append(
                LocationRecord(
                    identifier=str(data.get("Z_PK")),
                    latitude=latitude,
                    longitude=longitude,
                    altitude=data.get("ZALTITUDE"),
                    speed=data.get("ZSPEED"),
                    horizontal_accuracy=data.get("ZHORIZONTALACCURACY"),
                    recorded_at=apple_timestamp(data.get("ZTIMESTAMP") or data.get("ZDATE")),
                )
            )
    return records
