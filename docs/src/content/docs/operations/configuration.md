---
title: "Configuration"
description: "Every setting Apple Juicer reads, where it comes from, and how to set nested values."
---

Apple Juicer is configured entirely through environment variables. They are Pydantic settings defined in `core/config/settings.py`, all sharing the `APPLE_JUICER_` prefix, with `__` separating nested keys. Defaults are chosen so the tool runs out of the box; in practice you set the token and the backup path and leave the rest alone.

## The settings

| Variable | What it does | Default |
|----------|--------------|---------|
| `APPLE_JUICER_ENVIRONMENT` | `development` or `production`; `production` hides `/docs` | `development` |
| `APPLE_JUICER_SECURITY__API_TOKEN` | The token the frontend sends as `X-API-Token` | `dev-token` |
| `APPLE_JUICER_SECURITY__TRUSTED_HOSTS` | CORS origins, comma-separated | `http://localhost:5173,http://127.0.0.1:5173,localhost` |
| `APPLE_JUICER_POSTGRES__DSN` | Async SQLAlchemy DSN | `sqlite+aiosqlite:///./temp_data/apple_juicer.db` |
| `APPLE_JUICER_REDIS__URL` | Redis connection string | `redis://localhost:6379/0` |
| `APPLE_JUICER_BACKUP_PATHS__BASE_PATH` | Root directory containing backups | `/data/ios_backups` |
| `APPLE_JUICER_BACKUP_PATHS__TEMP_PATH` | Writable temp dir for extracted files | `/tmp/apple_juicer` |
| `APPLE_JUICER_BACKUP_PATHS__DECRYPTED_PATH` | Where decrypted data is stored | `/data/decrypted_backups` |
| `APPLE_JUICER_BACKUP_PATHS__HOST_DISPLAY_PATH` | Path shown in the UI, if different from the mount | none |

## Setting list values

For list-like settings, use indexed suffixes:

```bash
APPLE_JUICER_SECURITY__TRUSTED_HOSTS__0=https://ui.example.com
APPLE_JUICER_SECURITY__TRUSTED_HOSTS__1=https://admin.example.com
```

A single comma-separated string works too — the `trusted_hosts` validator coerces both into a real list.

## Where the values come from

Settings are read in this order of convenience:

- **A `.env` file** next to where you run the app. `AppSettings` loads `.env` automatically, which is the easiest path for local development.
- **The shell environment**, which is what Docker Compose uses — it maps friendly host variables like `APPLE_JUICER_API_TOKEN` onto the nested keys for you.

Keep the API token and database credentials out of source. A `.env` file or your orchestrator's secret store is the right home for them. Unlock passphrases are never written anywhere; the backend holds them in memory only for the life of a session.

## A local `.env` example

```ini
APPLE_JUICER_SECURITY__API_TOKEN=dev-token
APPLE_JUICER_POSTGRES__DSN=postgresql+asyncpg://postgres:postgres@localhost:5432/apple_juicer
APPLE_JUICER_REDIS__URL=redis://localhost:6379/0
APPLE_JUICER_BACKUP_PATHS__BASE_PATH=/Users/me/Library/Application Support/MobileSync/Backup
```

## Logging

Raise `LOG_LEVEL=debug` on the backend to trace discovery, unlock, and indexing. For the worker, `rq worker default --log-level DEBUG` does the same. If you need structured logs, run Uvicorn with `--log-config` pointing at a JSON logging config.
