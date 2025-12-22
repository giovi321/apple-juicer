from __future__ import annotations

from functools import lru_cache

from redis import Redis
from rq import Queue

from core.config import get_settings


@lru_cache()
def _redis_connection() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis.url)


def get_queue(name: str = "default") -> Queue:
    conn = _redis_connection()
    return Queue(name, connection=conn, default_timeout=600)


def get_connection() -> Redis:
    return _redis_connection()
