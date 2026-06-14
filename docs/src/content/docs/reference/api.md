---
title: "API Reference"
description: "Every endpoint: backup lifecycle, the ten artifact browsers, search, timeline, and the PDF report."
---

Every endpoint requires `X-API-Token`. Routes that read decrypted artifact data also require the backup to be in the `DECRYPTED` state. A live unlock session (`X-Backup-Session`) is required only by the manifest and file-browser routes; on the artifact attachment and extract routes it is optional, and those fall back to the on-disk decrypted data when it is absent. The backend listens on port 8080 by default, and serves interactive docs at `/docs` unless the environment is `production`.

## Health and system

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/healthz` | Returns `{"status":"ok"}`. No auth. Useful for readiness probes. |
| `GET` | `/` | Returns `{"name":"apple-juicer","status":"ok"}`. No auth, hidden from the schema. |
| `GET` | `/favicon.ico` | Returns `null`. Hidden from the schema. |

## Backups

Base path `/backups`. The router requires `X-API-Token` on every route below.

### `GET /backups`

Returns a `DiscoverResponse` (`{ backups: [...], base_directory }`). If the database holds no backups yet, the handler runs a filesystem refresh first, then returns the persisted summaries (each a `BackupSummaryModel`).

### `POST /backups/refresh`

Rescans the filesystem via `BackupRegistry.refresh()`, upserting metadata for each backup under `backup_paths.base_path`. Returns a `DiscoverResponse`; refreshed entries report `decryption_status = PENDING`.

### `POST /backups/{backup_id}/decrypt`

Body: `DecryptRequest` (`{ "password": "<iTunes passphrase>" }`). Marks the backup `DECRYPTING`, enqueues `decrypt_backup_job` with `result_ttl=0` so the password does not linger in Redis, and returns immediately with a `DecryptStatusResponse`. Poll `/decrypt-status` for completion. Returns `404` if the backup is unknown.

### `GET /backups/{backup_id}/decrypt-status`

Returns a `DecryptStatusResponse` (`backup_id`, `decryption_status`, `decrypted_at`, `error`). Returns `404` if the backup is unknown.

### `DELETE /backups/{backup_id}/decrypted`

Deletes the on-disk decrypted files and truncates the indexed artifacts, then resets the backup to `PENDING`. Returns `204 No Content`. Errors: `404` if unknown, `400` if the backup is not currently `DECRYPTED`, `500` if the filesystem deletion fails.

### `POST /backups/{backup_id}/unlock`

Body: `UnlockRequest` (`{ "password": "<iTunes passphrase>" }`). Response: `UnlockResponse` (`{ "session_token": "...", "ttl_seconds": ... }`). Errors: `404` if unknown, `400` if the passphrase is wrong.

### `POST /backups/{backup_id}/lock`

Requires `X-Backup-Session`. Revokes the session token and returns `{"status":"ok"}`. Idempotent — a missing or expired token is swallowed.

### `GET /backups/{backup_id}/files`

Lists manifest entries for a `DECRYPTED` backup. Response: `FileListResponse` (`{ items: [ManifestEntryModel], limit, offset }`). Errors: `404` if unknown, `400` if not decrypted or the decrypted data is missing.

| Param | In | Type | Default | Description |
|-------|-----|------|---------|-------------|
| `domain` | query | string | – | Filter by manifest domain (e.g. `AppDomain-com.apple.MobileSMS`). |
| `path_like` | query | string | – | SQL `LIKE` pattern for `relative_path` (use `%` wildcards). |
| `limit` | query | int | `100` | Page size. |
| `offset` | query | int | `0` | Pagination offset. |

### `GET /backups/{backup_id}/domains`

Returns `DomainListResponse` (`{ domains: [...] }`) for the unlocked or decrypted backup. Errors: `404` if unknown, `400` if not decrypted.

### `GET /backups/{backup_id}/file/{file_id}`

Streams the contents of a single manifest entry. The handler extracts the file to a temp sandbox, serves it via `FileResponse` (`application/octet-stream`), and deletes the sandbox after the response completes. Errors: `404` if the backup or file ID is unknown, `400` if not decrypted.

## Artifacts

Every artifact router uses the `/backups` prefix and requires `X-API-Token`. They all call `get_decrypted_backup()`, which returns `404` if the backup is unknown and `400` if it is not `DECRYPTED`. List and detail endpoints read from the indexed database and do not require `X-Backup-Session`.

The attachment-download and `extract` endpoints accept an optional `X-Backup-Session`. When present, the live unlock session's filesystem is used; when absent, the on-disk decrypted data is.

### WhatsApp

| Method | Path | Response | Notes |
|--------|------|----------|-------|
| `GET` | `/backups/{id}/artifacts/whatsapp/chats` | `WhatsAppChatListResponse` | Chats ordered by last message. |
| `GET` | `/backups/{id}/artifacts/whatsapp/chats/{chat_guid}` | `WhatsAppChatDetailResponse` | Chat plus all messages and attachments. `404` if the chat is unknown. |
| `GET` | `/backups/{id}/artifacts/whatsapp/attachment` | `FileResponse` | Download an attachment by required `relative_path`. Optional `X-Backup-Session`. |
| `POST` | `/backups/{id}/extract/whatsapp/{chat_guid}` | `{ extracted_files, extracted_bytes }` | Copies a chat's attachments into the decrypted dir. Optional `X-Backup-Session`. |

The attachment endpoint tries `WHATSAPP_FALLBACK_DOMAINS` when the manifest lookup fails.

### Messages (iMessage / SMS)

| Method | Path | Response | Notes |
|--------|------|----------|-------|
| `GET` | `/backups/{id}/artifacts/messages/conversations` | `MessageConversationListResponse` | Conversations ordered by last message. |
| `GET` | `/backups/{id}/artifacts/messages/conversations/{conversation_guid}` | `MessageConversationDetailResponse` | Conversation plus all messages and attachments. `404` if unknown. |
| `GET` | `/backups/{id}/artifacts/messages/attachment` | `FileResponse` | Download by required `relative_path`. Optional `X-Backup-Session`. |
| `POST` | `/backups/{id}/extract/messages/{conversation_guid}` | `{ extracted_files, extracted_bytes }` | Copies a conversation's attachments into the decrypted dir. Optional `X-Backup-Session`. |

Attachment resolution strips a leading `~` and falls back to `MESSAGE_FALLBACK_DOMAINS` (`MediaDomain`, `HomeDomain`).

### Photos

| Method | Path | Response | Notes |
|--------|------|----------|-------|
| `GET` | `/backups/{id}/artifacts/photos` | `PhotoListResponse` | Assets ordered by `taken_at`. |
| `GET` | `/backups/{id}/artifacts/photos/file` | `FileResponse` or JPEG | Download an image, or a JPEG thumbnail when `?thumb=N`. Optional `X-Backup-Session`. |

| Param | In | Type | Default | Description |
|-------|-----|------|---------|-------------|
| `limit` | query | int | `1000` | List page size. |
| `offset` | query | int | `0` | List pagination offset. |
| `relative_path` | query | string | required | Photo path, for the `file` endpoint. |
| `thumb` | query | int | – | Returns a JPEG thumbnail clamped to 32–1024 px. Non-image input yields `415`. |

### Notes, Calendar, Contacts, Calls, Safari, Locations, Voicemail

Each is a single list endpoint returning items ordered by their natural timestamp.

| Method | Path | Response | Order |
|--------|------|----------|-------|
| `GET` | `/backups/{id}/artifacts/notes` | `NoteListResponse` | `last_modified_at` |
| `GET` | `/backups/{id}/artifacts/calendar/events` | `CalendarEventListResponse` | `starts_at`, joined to its calendar |
| `GET` | `/backups/{id}/artifacts/contacts` | `ContactListResponse` | last / first name |
| `GET` | `/backups/{id}/artifacts/calls` | `CallListResponse` | `occurred_at` |
| `GET` | `/backups/{id}/artifacts/safari` | `SafariVisitListResponse` | `visited_at` (`limit` 1000) |
| `GET` | `/backups/{id}/artifacts/locations` | `LocationListResponse` | `recorded_at` (`limit` 2000) |
| `GET` | `/backups/{id}/artifacts/voicemail` | `VoicemailListResponse` | `received_at` |

## Search

### `GET /backups/{backup_id}/search`

Cross-artifact substring search over the backup's `artifact_search_index` (`search_text ILIKE %q%`). Requires a `DECRYPTED` backup. Returns a `SearchResponse` (`{ query, items: [SearchResultModel] }`). A blank `q` short-circuits to an empty result without touching the index.

| Param | In | Type | Default | Description |
|-------|-----|------|---------|-------------|
| `q` | query | string | `""` | Search term. |
| `limit` | query | int | `100` | Max results. |

## Timeline

### `GET /backups/{backup_id}/timeline`

A merged, reverse-chronological view across nine timestamped artifact types (WhatsApp, iMessage, calls, calendar events, photos, Safari visits, locations, voicemails, notes). Each type contributes up to 400 candidates, which are merged, sorted newest-first, and paginated. Requires a `DECRYPTED` backup. Returns a `TimelineResponse` (`{ items: [TimelineEventModel] }`).

| Param | In | Type | Default | Description |
|-------|-----|------|---------|-------------|
| `limit` | query | int | `200` | Page size, applied after the global merge. |
| `offset` | query | int | `0` | Pagination offset. |

## Report

### `GET /backups/{backup_id}/report.pdf`

Generates a one-page PDF (device metadata plus a count per artifact type) with FPDF. Requires a `DECRYPTED` backup. Returns the raw PDF (`application/pdf`) with a `Content-Disposition: attachment; filename="report-<id>.pdf"` header.

CSV export is a frontend feature — the tables generate CSV in the browser — so there is no CSV endpoint. The report router exposes only the PDF above.

## Response models

Response shapes live in `api/schemas.py`. The ones you'll meet most:

| Model | Key fields |
|-------|-----------|
| `BackupSummaryModel` | `id`, `display_name`, `device_name`, `product_version`, `is_encrypted`, `status`, `decryption_status`, `last_indexed_at`, `decrypted_at`, `size_bytes`, `last_modified_at`, `indexing_progress`, `indexing_total`, `indexing_artifact` |
| `DiscoverResponse` | `backups`, `base_directory` |
| `UnlockResponse` | `session_token`, `ttl_seconds` |
| `DecryptStatusResponse` | `backup_id`, `decryption_status`, `decrypted_at`, `error` |
| `ManifestEntryModel` | `file_id`, `domain`, `relative_path`, `size`, `mtime` |
| `FileListResponse` | `items`, `limit`, `offset` |
| `SearchResponse` | `query`, `items` (`artifact_type`, `artifact_ref`, `display_text`, `payload`) |
| `TimelineResponse` | `items` (`timestamp`, `artifact_type`, `title`, `subtitle`) |

Each artifact type has a matching `*ListResponse` (and, for WhatsApp and Messages, a `*DetailResponse`). The `extract` endpoints return ad-hoc JSON (`{ extracted_files, extracted_bytes }`) rather than a declared schema.

## Authentication headers

| Header | Required | Description |
|--------|----------|-------------|
| `X-API-Token` | Always | Matches `settings.security.api_token`. Set it with `APPLE_JUICER_SECURITY__API_TOKEN`. An invalid token returns `401`. |
| `X-Backup-Session` | Manifest/file routes; optional on attachment and extract routes | Issued by `/unlock`. Required on `/lock`, `/files`, `/domains`, and `/file/{file_id}`; optional elsewhere. |

## Error codes

- **400** — invalid unlock password, backup not decrypted, decrypted data missing, or a delete on a backup that is not `DECRYPTED`.
- **401** — missing or invalid `X-API-Token`, or an unknown session token where one is required.
- **403** — the session token belongs to a different backup.
- **404** — missing backup, chat, conversation, manifest entry, attachment, or file.
- **415** — `?thumb=N` requested on a non-image photo.
- **500** — a filesystem deletion failure or other unexpected worker/filesystem error.
