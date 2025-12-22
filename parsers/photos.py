from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, List

from .base import apple_timestamp, sqlite_connection, table_exists


@dataclass(slots=True)
class PhotoAssetRecord:
    asset_id: str | None
    original_filename: str | None
    relative_path: str | None
    file_id: str | None
    taken_at: datetime | None
    timezone_offset_minutes: int | None
    width: int | None
    height: int | None
    media_type: str | None
    metadata: dict[str, Any] | None = None


def parse_photos(db_path: Path) -> List[PhotoAssetRecord]:
    if not db_path.exists():
        return []

    results: list[PhotoAssetRecord] = []
    with sqlite_connection(db_path) as conn:
        if not table_exists(conn, "ZASSET"):
            return []
        cursor = conn.execute("SELECT * FROM ZASSET")
        for row in cursor.fetchall():
            data = dict(row)
            asset_id = data.get("ZUUID") or data.get("ZFILENAME") or str(data.get("Z_PK"))
            filename = data.get("ZORIGINALFILENAME") or data.get("ZFILENAME")
            directory = data.get("ZDIRECTORY") or data.get("ZRELATIVEDIRECTORY")
            relative_path = None
            if directory and filename:
                relative_path = f"{directory.rstrip('/')}/{filename}"
            elif filename:
                relative_path = filename

            file_id = (
                data.get("ZFILEHASH")
                or data.get("ZHASHEDASSETID")
                or data.get("ZMASTER")
                or data.get("Z_PK")
            )

            taken_at = apple_timestamp(data.get("ZDATECREATED") or data.get("ZADDEDDATE"))
            tz_offset = data.get("ZCAMERATIMESHIFT") or data.get("ZTIMEZONESHIFT")
            width = data.get("ZPIXELWIDTH")
            height = data.get("ZPIXELHEIGHT")
            media_type = _media_type_from_kind(data.get("ZKIND"))

            metadata = {
                key: data.get(key)
                for key in (
                    "ZLATITUDE",
                    "ZLONGITUDE",
                    "ZFAVORITE",
                    "ZHDRGAIN",
                    "ZBURST",
                    "ZORIENTATION",
                )
                if key in data
            }

            results.append(
                PhotoAssetRecord(
                    asset_id=str(asset_id) if asset_id is not None else None,
                    original_filename=filename,
                    relative_path=relative_path,
                    file_id=str(file_id) if file_id is not None else None,
                    taken_at=taken_at,
                    timezone_offset_minutes=int(tz_offset) if tz_offset is not None else None,
                    width=int(width) if width is not None else None,
                    height=int(height) if height is not None else None,
                    media_type=media_type,
                    metadata=metadata,
                )
            )
    return results


def _media_type_from_kind(kind_value: Any) -> str | None:
    if kind_value is None:
        return None
    kind_map = {
        0: "photo",
        1: "video",
        2: "screenshot",
        3: "panorama",
    }
    try:
        return kind_map.get(int(kind_value), "photo")
    except (TypeError, ValueError):
        return "photo"
