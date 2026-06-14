# Backend API

The backend is a FastAPI application defined in `api/main.py`. Its surface spans
backup discovery and decryption, manifest browsing and file download, per-artifact
browsing for ten artifact types, a global cross-artifact search, a unified
timeline, and a PDF report. Authentication uses a static API token plus
per-backup session tokens. Adding a new artifact type is a single registration in
the `ArtifactSpec` registry (`core/artifacts/registry.py`) rather than a change
spread across parser, worker, routes and schemas.

## App Lifecycle

1. `create_app()` builds the FastAPI instance, wiring CORS with trusted origins
   from Pydantic settings (and exposing the `X-Backup-Session` response header),
   then registering the `/healthz`, `/` and `/favicon.ico` routes.
   (@api/main.py#37-65)
2. A `startup` hook applies Alembic migrations to `head` on boot, run in a worker
   thread because Alembic's command API starts its own event loop.
   (@api/main.py#67-72)
3. The backups router plus every per-artifact router and the report/search/
   timeline routers are mounted. (@api/main.py#74-87)
4. `run()` serves the ASGI app with Uvicorn at `0.0.0.0:8080` in both local and
   Docker environments. (@api/main.py#92-96)

## Dependencies & Settings

`core.config.get_settings()` caches `AppSettings`, which aggregate security,
Postgres, Redis, and filesystem configuration. Env vars use the `APPLE_JUICER_`
prefix with `__` as the nested delimiter (e.g. the API token is
`APPLE_JUICER_SECURITY__API_TOKEN`). (@core/config/settings.py#52-63)

FastAPI dependencies inject long-lived services:

- `get_backup_registry()` – asynchronous SQLAlchemy session + filesystem discovery.
- `get_unlock_manager()` – orchestrates `iphone_backup_decrypt` sessions and keeps decrypted Manifest handles.

The artifact routers share helpers in `api/routes/_common.py`
(`get_decrypted_backup`, `resolve_filesystem`, `extract_attachment`,
`download_attachment_response`, `extract_files`) so list/detail/download/extract
behave identically across artifact types.

## Authentication

1. **API Token** (`X-API-Token`) enforced at router level via `require_api_token`. (@api/security.py#8-12)
2. **Backup Session** (`X-Backup-Session`) is **required** on the manifest/file
   routes (`/lock`, `/files`, `/domains`, `/file/{file_id}`) via
   `require_session_token`, **optional** on the artifact attachment and `/extract`
   routes (which fall back to the on-disk decrypted data), and **unused** by the
   artifact list/detail routes, which only require the backup to be `DECRYPTED`.
   (@api/security.py#19-20)

Tokens are compared directly; for production deployments place them behind TLS
terminators or API gateways.

## Routers

Each artifact type is exposed by its own router under `api/routes/`, all mounted
in `create_app()`. The lifecycle router owns discovery, decryption and the
manifest/file browser; the rest are registry-driven artifact browsers.

| Router module | Surface |
| --- | --- |
| `backups.py` | list / refresh / decrypt / decrypt-status / delete-decrypted / unlock / lock / files / domains / file download |
| `artifacts_whatsapp.py` | WhatsApp chats, messages, attachment download, extract |
| `artifacts_messages.py` | iMessage/SMS conversations, messages, attachment download, extract |
| `artifacts_photos.py` | Photos list, image/thumbnail download |
| `artifacts_notes.py` · `artifacts_calendar.py` · `artifacts_contacts.py` · `artifacts_calls.py` · `artifacts_safari.py` · `artifacts_locations.py` · `artifacts_voicemail.py` | per-type list endpoints |
| `search.py` | global cross-artifact search over `ArtifactSearchIndex` |
| `timeline.py` | merged reverse-chronological view across timestamped artifacts |
| `report.py` | `GET /backups/{id}/report.pdf` summary |

The full per-endpoint contract — methods, params, response models and error codes
— lives in the [API reference](../reference/api.md).

## Error Handling

- Missing backups, chats/conversations, manifest entries, attachments, or files return HTTP 404.
- Unlock failures (bad password) and operations on a not-yet-decrypted backup emit HTTP 400.
- Session mismatches return HTTP 403/401, depending on whether the token is unknown or tied to a different backup.

`FileResponse` uses a `BackgroundTask` to delete temporary directories once a
download completes, preventing leak of decrypted payloads.
