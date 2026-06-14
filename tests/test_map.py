"""The map endpoint unions significant locations and geotagged photos into one
flat list of points, filtered to rows that actually carry coordinates.
"""

from __future__ import annotations

import sqlite3

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from fixtures import build_all


class _Registry:
    def __init__(self, session):
        self.session = session

    async def get_backup(self, identifier: str):
        from core.db.models import Backup

        return await self.session.scalar(select(Backup).where(Backup.ios_identifier == identifier))


async def _indexed_backup(tmp_path, backup_id="MAP-1"):
    from core.db.models import Backup, DecryptionStatus
    from core.db.session import async_session_factory
    from worker.tasks import _index_backup_job

    decrypted = tmp_path / "decrypted"
    artifact_files = build_all(decrypted)

    async with async_session_factory() as session:
        session.add(
            Backup(ios_identifier=backup_id, path=str(tmp_path / "src"), display_name="t", is_encrypted=True)
        )
        await session.commit()

    await _index_backup_job(backup_id, str(decrypted), artifact_files)

    async with async_session_factory() as session:
        backup = await session.scalar(select(Backup).where(Backup.ios_identifier == backup_id))
        backup.decryption_status = DecryptionStatus.DECRYPTED
        backup.decrypted_path = str(decrypted)
        await session.commit()

    return backup_id


async def test_map_unions_locations_and_geotagged_photos(db, tmp_path):
    from core.db.session import async_session_factory

    from api.routes import artifacts_map

    backup_id = await _indexed_backup(tmp_path)

    async with async_session_factory() as session:
        registry = _Registry(session)
        result = await artifacts_map.backup_map(backup_id, registry=registry, session=session)

    # 2 significant locations + 1 geotagged photo (the second photo is a video
    # with no GPS, so it is filtered out).
    assert result.total == 3
    assert len(result.items) == 3
    assert result.capped is False

    by_kind = {}
    for point in result.items:
        by_kind.setdefault(point.kind, []).append((round(point.latitude, 4), round(point.longitude, 4)))

    assert by_kind["photo"] == [(47.1, 8.5)]
    assert set(by_kind["location"]) == {(47.3769, 8.5417), (37.3349, -122.009)}


def _photos_geotagged_video_db(path) -> None:
    """A single asset that is a VIDEO (ZKIND=1) carrying valid GPS — it must
    still appear on the map, since filtering is by coordinates, not media type."""
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE ZASSET (
            Z_PK INTEGER PRIMARY KEY, ZUUID TEXT, ZORIGINALFILENAME TEXT, ZDIRECTORY TEXT,
            ZFILEHASH TEXT, ZDATECREATED REAL, ZPIXELWIDTH INTEGER, ZPIXELHEIGHT INTEGER,
            ZKIND INTEGER, ZLATITUDE REAL, ZLONGITUDE REAL
        );
        INSERT INTO ZASSET VALUES
            (1, 'vid-1', 'IMG_9001.MOV', 'DCIM/100APPLE', 'h1', 700000000.0, 1920, 1080, 1, 51.5, -0.12);
        """
    )
    conn.commit()
    conn.close()


async def test_map_includes_geotagged_videos(db, tmp_path):
    from core.db.models import Backup, DecryptionStatus
    from core.db.session import async_session_factory
    from worker.tasks import _index_backup_job

    from api.routes import artifacts_map

    decrypted = tmp_path / "decrypted"
    decrypted.mkdir(parents=True, exist_ok=True)
    photos = decrypted / "Photos.sqlite"
    _photos_geotagged_video_db(photos)
    backup_id = "MAP-VID"

    async with async_session_factory() as session:
        session.add(
            Backup(ios_identifier=backup_id, path=str(tmp_path / "src"), display_name="t", is_encrypted=True)
        )
        await session.commit()
    await _index_backup_job(backup_id, str(decrypted), {"photos": str(photos)})
    async with async_session_factory() as session:
        backup = await session.scalar(select(Backup).where(Backup.ios_identifier == backup_id))
        backup.decryption_status = DecryptionStatus.DECRYPTED
        backup.decrypted_path = str(decrypted)
        await session.commit()

    async with async_session_factory() as session:
        registry = _Registry(session)
        result = await artifacts_map.backup_map(backup_id, registry=registry, session=session)

    assert result.total == 1
    assert len(result.items) == 1
    point = result.items[0]
    assert point.kind == "photo"
    assert round(point.latitude, 2) == 51.5 and round(point.longitude, 2) == -0.12


async def test_map_requires_decrypted_backup(db, tmp_path):
    from core.db.models import Backup
    from core.db.session import async_session_factory

    from api.routes import artifacts_map

    backup_id = "MAP-LOCKED"
    async with async_session_factory() as session:
        session.add(Backup(ios_identifier=backup_id, path=str(tmp_path), display_name="t", is_encrypted=True))
        await session.commit()

    async with async_session_factory() as session:
        registry = _Registry(session)
        with pytest.raises(HTTPException) as exc:
            await artifacts_map.backup_map(backup_id, registry=registry, session=session)
    assert exc.value.status_code == 400
