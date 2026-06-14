"""The Alembic baseline migration builds the full schema and stays in sync
with the ORM metadata.
"""

from __future__ import annotations

import sqlite3


def test_migrations_build_full_schema(tmp_path):
    from alembic import command
    from alembic.config import Config

    import core.db.artifacts  # noqa: F401  (register tables)
    import core.db.models  # noqa: F401
    from core.db.base import Base

    db_path = tmp_path / "migrated.db"
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_path.as_posix()}")
    command.upgrade(cfg, "head")

    conn = sqlite3.connect(db_path)
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        photo_cols = {row[1] for row in conn.execute("PRAGMA table_info(photo_assets)")}
    finally:
        conn.close()

    expected = set(Base.metadata.tables.keys())
    missing = expected - tables
    assert not missing, f"migration is missing tables: {missing}"
    assert "alembic_version" in tables
    # Column-level guard: a migration that forgot/misnamed a column (or fails on a
    # dialect other than SQLite) would otherwise pass the table-name check alone.
    assert {"latitude", "longitude"} <= photo_cols, "photo geotag columns missing from migration"
