# API Reference

All endpoints require `X-API-Token` unless noted. Routes that read decrypted
artifact data require the backup to be in the `DECRYPTED` state; a live unlock
session (`X-Backup-Session`) is only required by the manifest/file-browser
routes and is *optional* on the artifact attachment and extract routes (those
fall back to the on-disk decrypted data when no session header is sent). The
backend runs on port `8080` by default. (@api/main.py#92-96)

The FastAPI app is assembled in `create_app()`, which registers the backups
router, every per-artifact router, and the report/search/timeline routers.
Interactive docs are served at `/docs` unless `environment` is `production`.
(@api/main.py#37-89)

## Health & system

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/healthz` | Returns `{"status":"ok"}`. No auth. Useful for readiness probes. (@api/main.py#55-57) |
| `GET` | `/` | Returns `{"name":"apple-juicer","status":"ok"}`. No auth, hidden from schema. (@api/main.py#59-61) |
| `GET` | `/favicon.ico` | Returns `null`. Hidden from schema. (@api/main.py#63-65) |

## Backups

Base path: `/backups`. The router is declared with
`dependencies=[Depends(require_api_token)]`, so every route below requires
`X-API-Token`. (@api/routes/backups.py#32)

### `GET /backups`

Returns a `DiscoverResponse` (`{ backups: [...], base_directory }`). If the
database holds no backups yet, the handler triggers a filesystem refresh first,
then returns the persisted summaries (each a `BackupSummaryModel`).
(@api/routes/backups.py#37-64)

### `POST /backups/refresh`

Forces a filesystem rescan via `BackupRegistry.refresh()`, upserting metadata
for each backup discovered under `backup_paths.base_path`. Returns a
`DiscoverResponse`; refreshed entries report `decryption_status = PENDING`.
(@api/routes/backups.py#67-88)

### `POST /backups/{backup_id}/decrypt`

Body: `DecryptRequest` (`{ "password": "<iTunes passphrase>" }`). Marks the
backup `DECRYPTING`, enqueues `decrypt_backup_job` on the worker queue
(`result_ttl=0` so the password does not linger in Redis), and returns
immediately with a `DecryptStatusResponse`. Clients poll `/decrypt-status` for
completion. Errors: `404` if the backup is unknown.
(@api/routes/backups.py#91-118)

### `GET /backups/{backup_id}/decrypt-status`

Returns a `DecryptStatusResponse` (`backup_id`, `decryption_status`,
`decrypted_at`, `error`). Errors: `404` if the backup is unknown.
(@api/routes/backups.py#121-135)

### `DELETE /backups/{backup_id}/decrypted`

Deletes the on-disk decrypted files (`shutil.rmtree`) and truncates the indexed
artifacts for the backup, then resets it to `PENDING`. Returns `204 No Content`.
Errors: `404` if the backup is unknown, `400` if the backup is not currently
`DECRYPTED`, `500` if the filesystem deletion fails.
(@api/routes/backups.py#138-175)

### `POST /backups/{backup_id}/unlock`

Body: `UnlockRequest` (`{ "password": "<iTunes passphrase>" }`).
Response: `UnlockResponse` (`{ "session_token": "...", "ttl_seconds": ... }`).
Errors: `404` if the backup is unknown, `400` if the passphrase is incorrect
(`UnlockError`). (@api/routes/backups.py#178-193)

### `POST /backups/{backup_id}/lock`

Headers: `X-Backup-Session` (enforced by `require_session_token`). Revokes the
session token and returns `{"status":"ok"}`. Idempotent: a missing/expired
token is swallowed (`SessionNotFoundError`). (@api/routes/backups.py#196-206)

### `GET /backups/{backup_id}/files`

Lists manifest entries for a `DECRYPTED` backup. Response: `FileListResponse`
(`{ items: [ManifestEntryModel], limit, offset }`). Errors: `404` if the backup
is unknown, `400` if it is not decrypted or the decrypted data is missing.
(@api/routes/backups.py#209-234)

| Param | In | Type | Default | Description |
| --- | --- | --- | --- | --- |
| `domain` | query | string | – | Filter by manifest domain (e.g. `AppDomain-com.apple.MobileSMS`). |
| `path_like` | query | string | – | SQL `LIKE` pattern for `relative_path` (use `%` wildcards). |
| `limit` | query | int | `100` | Page size. |
| `offset` | query | int | `0` | Pagination offset. |

### `GET /backups/{backup_id}/domains`

Returns `DomainListResponse` (`{ domains: [...] }`) for the unlocked/decrypted
backup. Errors: `404` if unknown, `400` if not decrypted.
(@api/routes/backups.py#237-244)

### `GET /backups/{backup_id}/file/{file_id}`

Streams the contents of a single manifest entry. The handler extracts the file
to a temp sandbox, serves it via `FileResponse`
(`media_type=application/octet-stream`), and deletes the sandbox once the
response completes (background task). Errors: `404` if the backup or file ID is
unknown, `400` if the backup is not decrypted.
(@api/routes/backups.py#247-266)

## Artifacts

Every artifact router uses the `/backups` prefix and the
`Depends(require_api_token)` dependency, and calls `get_decrypted_backup()`,
which returns `404` if the backup is unknown and `400` if it is not in the
`DECRYPTED` state. List/detail endpoints read from the indexed database and do
**not** require `X-Backup-Session`. (@api/routes/_common.py#24-31)

Attachment-download and `extract` endpoints accept an **optional**
`X-Backup-Session` header. When present, the live unlock session's filesystem is
used; when absent, the on-disk decrypted data is used (`resolve_filesystem`).
(@api/routes/_common.py#60-64)

### WhatsApp

Base path `/backups`, tag `whatsapp`. (@api/routes/artifacts_whatsapp.py#23)

| Method | Path | Response model | Notes |
| --- | --- | --- | --- |
| `GET` | `/backups/{backup_id}/artifacts/whatsapp/chats` | `WhatsAppChatListResponse` | Chats ordered by last message. (@api/routes/artifacts_whatsapp.py#120-134) |
| `GET` | `/backups/{backup_id}/artifacts/whatsapp/chats/{chat_guid}` | `WhatsAppChatDetailResponse` | Chat plus all messages (with attachments). `404` if the chat is unknown. (@api/routes/artifacts_whatsapp.py#137-160) |
| `GET` | `/backups/{backup_id}/artifacts/whatsapp/attachment` | `FileResponse` | Download an attachment by `relative_path`. Optional `X-Backup-Session`. (@api/routes/artifacts_whatsapp.py#163-181) |
| `POST` | `/backups/{backup_id}/extract/whatsapp/{chat_guid}` | `{ extracted_files, extracted_bytes }` | Copies a chat's attachments into the decrypted dir. Optional `X-Backup-Session`. (@api/routes/artifacts_whatsapp.py#184-209) |

The `attachment` endpoint takes a required `relative_path` query param and tries
`WHATSAPP_FALLBACK_DOMAINS` when the manifest lookup fails.
(@api/routes/artifacts_whatsapp.py#26-32)

### Messages (iMessage / SMS)

Base path `/backups`, tag `messages`. (@api/routes/artifacts_messages.py#23)

| Method | Path | Response model | Notes |
| --- | --- | --- | --- |
| `GET` | `/backups/{backup_id}/artifacts/messages/conversations` | `MessageConversationListResponse` | Conversations ordered by last message. (@api/routes/artifacts_messages.py#77-94) |
| `GET` | `/backups/{backup_id}/artifacts/messages/conversations/{conversation_guid}` | `MessageConversationDetailResponse` | Conversation plus all messages (with attachments). `404` if unknown. (@api/routes/artifacts_messages.py#97-132) |
| `GET` | `/backups/{backup_id}/artifacts/messages/attachment` | `FileResponse` | Download by `relative_path`. Optional `X-Backup-Session`. (@api/routes/artifacts_messages.py#135-153) |
| `POST` | `/backups/{backup_id}/extract/messages/{conversation_guid}` | `{ extracted_files, extracted_bytes }` | Copies a conversation's attachments into the decrypted dir. Optional `X-Backup-Session`. (@api/routes/artifacts_messages.py#156-181) |

Attachment resolution strips a leading `~` and falls back to
`MESSAGE_FALLBACK_DOMAINS` (`MediaDomain`, `HomeDomain`).
(@api/routes/artifacts_messages.py#25)

### Photos

Base path `/backups`, tag `photos`. (@api/routes/artifacts_photos.py#25)

| Method | Path | Response model | Notes |
| --- | --- | --- | --- |
| `GET` | `/backups/{backup_id}/artifacts/photos` | `PhotoListResponse` | Assets ordered by `taken_at`. (@api/routes/artifacts_photos.py#64-81) |
| `GET` | `/backups/{backup_id}/artifacts/photos/file` | `FileResponse` or JPEG `Response` | Download an image, or a JPEG thumbnail when `?thumb=N`. Optional `X-Backup-Session`. (@api/routes/artifacts_photos.py#84-122) |

| Param | In | Type | Default | Description |
| --- | --- | --- | --- | --- |
| `limit` | query | int | `1000` | List page size. (@api/routes/artifacts_photos.py#66) |
| `offset` | query | int | `0` | List pagination offset. (@api/routes/artifacts_photos.py#67) |
| `relative_path` | query | string | required | Photo path, for the `file` endpoint. (@api/routes/artifacts_photos.py#86) |
| `thumb` | query | int | – | When set, returns a JPEG thumbnail clamped to 32–1024 px. Non-image input yields `415`. (@api/routes/artifacts_photos.py#88,97-113) |

### Notes

| Method | Path | Response model | Notes |
| --- | --- | --- | --- |
| `GET` | `/backups/{backup_id}/artifacts/notes` | `NoteListResponse` | Notes ordered by `last_modified_at`. (@api/routes/artifacts_notes.py#28-41) |

### Calendar

| Method | Path | Response model | Notes |
| --- | --- | --- | --- |
| `GET` | `/backups/{backup_id}/artifacts/calendar/events` | `CalendarEventListResponse` | Events joined to their calendar, ordered by `starts_at`. (@api/routes/artifacts_calendar.py#17-45) |

### Contacts

| Method | Path | Response model | Notes |
| --- | --- | --- | --- |
| `GET` | `/backups/{backup_id}/artifacts/contacts` | `ContactListResponse` | Contacts ordered by last/first name. (@api/routes/artifacts_contacts.py#29-42) |

### Calls

| Method | Path | Response model | Notes |
| --- | --- | --- | --- |
| `GET` | `/backups/{backup_id}/artifacts/calls` | `CallListResponse` | Call records ordered by `occurred_at`. (@api/routes/artifacts_calls.py#30-43) |

### Safari history

| Method | Path | Response model | Notes |
| --- | --- | --- | --- |
| `GET` | `/backups/{backup_id}/artifacts/safari` | `SafariVisitListResponse` | Visits ordered by `visited_at`. `limit` default `1000`, `offset` default `0`. (@api/routes/artifacts_safari.py#27-44) |

### Locations

| Method | Path | Response model | Notes |
| --- | --- | --- | --- |
| `GET` | `/backups/{backup_id}/artifacts/locations` | `LocationListResponse` | Points ordered by `recorded_at`. `limit` default `2000`, `offset` default `0`. (@api/routes/artifacts_locations.py#29-46) |

### Voicemail

| Method | Path | Response model | Notes |
| --- | --- | --- | --- |
| `GET` | `/backups/{backup_id}/artifacts/voicemail` | `VoicemailListResponse` | Voicemails ordered by `received_at`. (@api/routes/artifacts_voicemail.py#27-40) |

## Search

Base path `/backups`, tag `search`. (@api/routes/search.py#14)

### `GET /backups/{backup_id}/search`

Cross-artifact substring search over the per-backup `ArtifactSearchIndex`
(`search_text ILIKE %q%`). Requires a `DECRYPTED` backup. Returns a
`SearchResponse` (`{ query, items: [SearchResultModel] }`); an empty/blank `q`
returns an empty `items` list without hitting the index.
(@api/routes/search.py#17-50)

| Param | In | Type | Default | Description |
| --- | --- | --- | --- | --- |
| `q` | query | string | `""` | Search term. Blank short-circuits to an empty result. |
| `limit` | query | int | `100` | Max results. |

## Timeline

Base path `/backups`, tag `timeline`. (@api/routes/timeline.py#24)

### `GET /backups/{backup_id}/timeline`

A merged, reverse-chronological view across nine timestamped artifact types
(WhatsApp messages, iMessages, calls, calendar events, photos, Safari visits,
locations, voicemails, notes). Each type contributes up to `_PER_TYPE` (400)
candidates, which are merged, sorted newest-first, then paginated. Requires a
`DECRYPTED` backup. Returns a `TimelineResponse` (`{ items: [TimelineEventModel]
}`). (@api/routes/timeline.py#26-129)

| Param | In | Type | Default | Description |
| --- | --- | --- | --- | --- |
| `limit` | query | int | `200` | Page size applied after the global merge/sort. |
| `offset` | query | int | `0` | Pagination offset. |

## Report

Base path `/backups`, tag `report`. (@api/routes/report.py#28)

### `GET /backups/{backup_id}/report.pdf`

Generates a one-page PDF summary (device metadata plus a headline count per
artifact type) via FPDF. Requires a `DECRYPTED` backup. Returns the raw PDF
(`media_type=application/pdf`) with a
`Content-Disposition: attachment; filename="report-<id>.pdf"` header.
(@api/routes/report.py#91-113)

> Note: there is currently no CSV or other export endpoint in the codebase. The
> report router exposes only the PDF endpoint above.

## Response models

Response shapes are defined in `api/schemas.py`. Selected models:

| Model | Key fields |
| --- | --- |
| `BackupSummaryModel` | `id`, `display_name`, `device_name`, `product_version`, `is_encrypted`, `status`, `decryption_status`, `last_indexed_at`, `decrypted_at`, `size_bytes`, `last_modified_at`, `indexing_progress`, `indexing_total`, `indexing_artifact`. (@api/schemas.py#12-26) |
| `DiscoverResponse` | `backups: [BackupSummaryModel]`, `base_directory`. (@api/schemas.py#29-31) |
| `UnlockResponse` | `session_token`, `ttl_seconds`. (@api/schemas.py#38-40) |
| `DecryptStatusResponse` | `backup_id`, `decryption_status`, `decrypted_at`, `error`. (@api/schemas.py#47-51) |
| `ManifestEntryModel` | `file_id`, `domain`, `relative_path`, `size`, `mtime`. (@api/schemas.py#54-59) |
| `FileListResponse` | `items: [ManifestEntryModel]`, `limit`, `offset`. (@api/schemas.py#62-65) |
| `DomainListResponse` | `domains: [str]`. (@api/schemas.py#68-69) |
| `WhatsAppChatListResponse` / `WhatsAppChatDetailResponse` | chat list / chat + messages with attachments. (@api/schemas.py#102-108) |
| `MessageConversationListResponse` / `MessageConversationDetailResponse` | conversation list / conversation + messages with attachments. (@api/schemas.py#139-145) |
| `PhotoListResponse` | `items: [PhotoAssetModel]`. (@api/schemas.py#161-162) |
| `NoteListResponse` | `items: [NoteModel]`. (@api/schemas.py#174-175) |
| `CalendarEventListResponse` | `items: [CalendarEventModel]`. (@api/schemas.py#190-191) |
| `ContactListResponse` | `items: [ContactModel]`. (@api/schemas.py#204-205) |
| `CallListResponse` | `items: [CallModel]`. (@api/schemas.py#219-220) |
| `SafariVisitListResponse` | `items: [SafariVisitModel]`. (@api/schemas.py#231-232) |
| `LocationListResponse` | `items: [LocationModel]`. (@api/schemas.py#245-246) |
| `VoicemailListResponse` | `items: [VoicemailModel]`. (@api/schemas.py#257-258) |
| `SearchResponse` | `query`, `items: [SearchResultModel]` (`artifact_type`, `artifact_ref`, `display_text`, `payload`). (@api/schemas.py#261-270) |
| `TimelineResponse` | `items: [TimelineEventModel]` (`timestamp`, `artifact_type`, `title`, `subtitle`). (@api/schemas.py#273-281) |

The `extract` endpoints and unmatched-thumbnail paths return ad-hoc JSON
(`{ extracted_files, extracted_bytes }`) rather than a declared schema.

## Authentication Headers

| Header | Required | Description |
| --- | --- | --- |
| `X-API-Token` | Always | Matches `settings.security.api_token`. Set via the env var `APPLE_JUICER_SECURITY__API_TOKEN` (prefix `APPLE_JUICER_`, nested delimiter `__`). Invalid token → `401`. (@api/security.py#8-12) (@core/config/settings.py#10-11,52-63) |
| `X-Backup-Session` | Manifest/file routes; optional on artifact attachment & extract routes | Issued by `/backups/{id}/unlock`. Enforced (required) on `/lock`, `/files`, `/domains`, `/file/{file_id}` via `require_session_token`; optional elsewhere via `Header(None, alias="X-Backup-Session")`. (@api/security.py#19-20) |

## Error Codes

- `400 Bad Request` – invalid unlock password, backup not decrypted, decrypted
  data missing, or (for delete) backup not in the `DECRYPTED` state.
- `401 Unauthorized` – missing/invalid `X-API-Token`, or an unknown session
  token when a session is supplied/required.
- `403 Forbidden` – the supplied session token belongs to a different backup.
- `404 Not Found` – missing backup, chat/conversation, manifest entry,
  attachment, or file.
- `415 Unsupported Media Type` – `?thumb=N` requested on a non-image photo.
- `500 Internal Server Error` – filesystem deletion failure or other unexpected
  worker/filesystem issues (see logs for stack traces).
