# Backend API

The backend is a FastAPI application defined in `api/main.py`. It exposes a small surface focused on backup discovery, unlocking, manifest browsing, and file download. Authentication uses static API tokens plus per-backup session tokens.

## App Lifecycle

1. `create_app()` builds the FastAPI instance, wiring CORS with trusted origins from Pydantic settings and registering the `/healthz` probe. (@api/main.py#10-34)
2. Routers from `api.routes` are mounted (currently only `backups` but structured for future expansion). (@api/main.py#6-34)
3. Uvicorn runs the ASGI app at `0.0.0.0:8080` in both local and Docker environments. (@api/main.py#37-41)

## Dependencies & Settings

`core.config.get_settings()` caches `AppSettings`, which aggregate security, Postgres, Redis, and filesystem configuration. Env vars use the `APPLE_JUICER_` prefix with nested delimiters. (@core/config/settings.py#50-68)

FastAPI dependencies inject long-lived services:

- `get_backup_registry()` – asynchronous SQLAlchemy session + filesystem discovery.
- `get_unlock_manager()` – orchestrates `iphone_backup_decrypt` sessions and keeps decrypted Manifest handles.

## Authentication

1. **API Token** (`X-API-Token`) enforced at router level using `require_api_token`. (@api/routes/backups.py#12, @api/security.py#8-12)
2. **Backup Session** (`X-Backup-Session`) enforced on manifest/file calls via `require_session_token`. (@api/security.py#19-20)

Tokens are compared directly; for production deployments place them behind TLS terminators or API gateways.

## Routes

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/healthz` | Basic readiness probe. (@api/main.py#28-33) |
| `GET` | `/backups` | List persisted backups with metadata. |
| `POST` | `/backups/refresh` | Rescan filesystem and upsert metadata. |
| `POST` | `/backups/{id}/unlock` | Unlock encrypted backup, returning a temporary session token. |
| `POST` | `/backups/{id}/lock` | Revoke session token. |
| `GET` | `/backups/{id}/files` | Page through manifest rows with optional domain/path filters. |
| `GET` | `/backups/{id}/domains` | Enumerate manifest domains. |
| `GET` | `/backups/{id}/file/{file_id}` | Stream an extracted file with cleanup background task. |

All `/backups/*` endpoints are defined in `api/routes/backups.py`. Their implementations rely on `BackupRegistry`, `UnlockManager`, and domain-specific schemas. (@api/routes/backups.py#12-141)

## Error Handling

- Missing backups return HTTP 404.
- Unlock failures (bad password) emit HTTP 400 with the parser error message.
- Session mismatches return HTTP 403/401, depending on whether the token is unknown or tied to a different backup. (@api/routes/backups.py#71-151)

`FileResponse` uses a `BackgroundTask` to delete temporary directories once a download completes, preventing leak of decrypted payloads. (@api/routes/backups.py#122-141)
