from __future__ import annotations

from functools import lru_cache
from typing import Any

import orjson
from cryptography.fernet import Fernet, InvalidToken

from core.config import get_settings


class EncryptionError(RuntimeError):
    """Raised when encryption or decryption fails."""


@lru_cache()
def _fernet() -> Fernet:
    settings = get_settings()
    key = settings.security.encryption_key
    if not key:
        raise EncryptionError("Security encryption key is not configured.")
    try:
        return Fernet(key.encode())
    except Exception as exc:  # pragma: no cover - safety net
        raise EncryptionError("Invalid encryption key provided.") from exc


def _encrypt_bytes(data: bytes | None) -> bytes | None:
    if data is None:
        return None
    return _fernet().encrypt(data)


def _decrypt_bytes(blob: bytes | None) -> bytes | None:
    if blob is None:
        return None
    try:
        return _fernet().decrypt(blob)
    except InvalidToken as exc:
        raise EncryptionError("Corrupted encrypted payload.") from exc


def encrypt_text(value: str | None) -> bytes | None:
    if value is None:
        return None
    return _encrypt_bytes(value.encode("utf-8"))


def decrypt_text(blob: bytes | None) -> str | None:
    data = _decrypt_bytes(blob)
    return data.decode("utf-8") if data is not None else None


def encrypt_json(value: Any | None) -> bytes | None:
    if value is None:
        return None
    return _encrypt_bytes(orjson.dumps(value))


def decrypt_json(blob: bytes | None) -> Any | None:
    data = _decrypt_bytes(blob)
    if data is None:
        return None
    return orjson.loads(data)
