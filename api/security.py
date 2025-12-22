from __future__ import annotations

from fastapi import Header, HTTPException, status

from core.config import get_settings


async def require_api_token(x_api_token: str = Header(..., alias="X-API-Token")) -> str:
    settings = get_settings()
    if x_api_token != settings.security.api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API token.")
    return x_api_token


async def optional_api_token(x_api_token: str | None = Header(None, alias="X-API-Token")) -> str | None:
    return x_api_token


async def require_session_token(x_backup_session: str = Header(..., alias="X-Backup-Session")) -> str:
    return x_backup_session
