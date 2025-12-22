from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, BaseModel, Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SecuritySettings(BaseModel):
    api_token: str = Field(default="dev-token")
    trusted_hosts: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "localhost",
        ]
    )

    @validator("api_token")
    def ensure_non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("API token must be provided.")
        return v

    @validator("trusted_hosts", pre=True)
    def coerce_hosts(cls, value: List[str] | dict | str) -> List[str] | str:
        if isinstance(value, dict):
            # Pydantic maps APPLE_JUICER_SECURITY__TRUSTED_HOSTS__0-style env vars into a dict
            return [value[key] for key in sorted(value.keys())]
        if isinstance(value, str):
            # Allow comma-separated entries when provided as a single env var
            return [part.strip() for part in value.split(",") if part.strip()]
        return value


class PostgresSettings(BaseModel):
    dsn: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/apple_juicer"


class RedisSettings(BaseModel):
    url: str = "redis://localhost:6379/0"


class BackupPathSettings(BaseModel):
    base_path: str = "/data/ios_backups"
    temp_path: str = "/tmp/apple_juicer"
    decrypted_path: str = "/data/decrypted_backups"
    host_display_path: str | None = None


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env",),
        env_file_encoding="utf-8",
        env_prefix="APPLE_JUICER_",
        env_nested_delimiter="__",
    )

    environment: str = "development"
    version: str = "0.1.0"
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    backup_paths: BackupPathSettings = Field(default_factory=BackupPathSettings)
    frontend_base_url: AnyHttpUrl | None = None


@lru_cache()
def get_settings() -> AppSettings:
    return AppSettings()  # type: ignore[arg-type]
