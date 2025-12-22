from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import get_settings
from core.db.base import Base
# Import models so SQLAlchemy metadata is populated before init_models/create_all runs.
# These imports are intentionally unused.
from core.db import models, artifacts  # noqa: F401

settings = get_settings()

engine = create_async_engine(settings.postgres.dsn, future=True, echo=settings.environment == "development")
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def init_models() -> None:
    """Create tables during bootstrap (for development)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
