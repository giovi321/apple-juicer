---
title: "Backend API"
description: "How the FastAPI backend is structured: a lifecycle router plus one router per artifact type, all driven by a registry."
---

The backend is a FastAPI app in `api/main.py`. Its surface is wide but regular: one lifecycle router handles discovery, decryption, unlocking, and the manifest/file browser, and then there is one router per artifact type, plus search, timeline, and a PDF report. Adding an artifact type is a single registration in the `ArtifactSpec` registry, not a change spread across four files.

## What happens at startup

`create_app()` builds the app in a fixed order:

1. Reads settings and constructs the FastAPI instance, with `/docs` enabled unless the environment is `production`.
2. Adds CORS from `settings.security.trusted_hosts` and exposes the `X-Backup-Session` response header.
3. Registers `/healthz`, `/`, and `/favicon.ico`.
4. Runs Alembic migrations to `head` in a startup hook, in a worker thread because Alembic's command API starts its own event loop.
5. Mounts the backups router, every artifact router, and the report/search/timeline routers.

`run()` then serves the app with Uvicorn on `0.0.0.0:8080` in both local and Docker runs.

## Settings and shared services

`core.config.get_settings()` caches an `AppSettings` object covering security, Postgres, Redis, and filesystem paths. Every environment variable uses the `APPLE_JUICER_` prefix with `__` as the nested delimiter, so the API token is `APPLE_JUICER_SECURITY__API_TOKEN`.

Two dependencies inject the long-lived services:

- `get_backup_registry()` — an async SQLAlchemy session plus filesystem discovery.
- `get_unlock_manager()` — manages `iphone-backup-decrypt` sessions and the decrypted Manifest handles.

The artifact routers share helpers in `api/routes/_common.py` — `get_decrypted_backup`, `resolve_filesystem`, `extract_attachment`, `download_attachment_response`, `extract_files` — so listing, detail, download, and extraction behave the same across every type.

## Authentication

Two headers gate the API, and they apply at different scopes:

- **`X-API-Token`** is required on every route, enforced at the router level by `require_api_token`.
- **`X-Backup-Session`** is required only on the manifest/file routes (`/lock`, `/files`, `/domains`, `/file/{file_id}`). It is optional on the artifact attachment and `/extract` routes, which fall back to the on-disk decrypted data, and unused by the artifact list/detail routes, which only need a `DECRYPTED` backup.

Tokens are compared directly. For anything beyond a trusted LAN, put the backend behind a TLS terminator or API gateway.

## The routers

Every artifact type has its own router under `api/routes/`, all mounted in `create_app()`. The lifecycle router owns discovery and decryption; the rest are registry-driven artifact browsers.

| Router module | Surface |
|---------------|---------|
| `backups.py` | list / refresh / decrypt / decrypt-status / delete-decrypted / unlock / lock / files / domains / file download |
| `artifacts_whatsapp.py` | WhatsApp chats, messages, attachment download, extract |
| `artifacts_messages.py` | iMessage/SMS conversations, messages, attachment download, extract |
| `artifacts_photos.py` | Photos list, image and thumbnail download |
| `artifacts_notes.py`, `artifacts_calendar.py`, `artifacts_contacts.py`, `artifacts_calls.py`, `artifacts_safari.py`, `artifacts_locations.py`, `artifacts_voicemail.py` | per-type list endpoints |
| `search.py` | global search over `artifact_search_index` |
| `timeline.py` | merged reverse-chronological view across timestamped artifacts |
| `report.py` | `GET /backups/{id}/report.pdf` summary |

The full per-endpoint contract — methods, parameters, response models, and error codes — is in the [API reference](../../reference/api/).

## Errors

The error codes are consistent across routers:

- **404** for a missing backup, chat, conversation, manifest entry, attachment, or file.
- **400** for a bad unlock password or an operation on a backup that is not yet decrypted.
- **403 / 401** for a session token that belongs to a different backup, or one that is missing or unknown.

File downloads stream through a `FileResponse` with a `BackgroundTask` that deletes the temporary directory once the response finishes, so decrypted payloads never linger.
