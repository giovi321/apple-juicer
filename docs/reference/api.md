# API Reference

All endpoints require `X-API-Token` unless noted. Manifest and file operations also require `X-Backup-Session`, returned by the unlock endpoint. The backend runs on port `8080` by default. (@api/main.py#10-34)

## Health

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/healthz` | Returns `{"status":"ok"}`. Useful for readiness probes. (@api/main.py#28-33) |

## Backups

Base path: `/backups` (router defined with `Depends(require_api_token)`). (@api/routes/backups.py#12-141)

### `GET /backups`

Returns a `DiscoverResponse` with an array of backup summaries persisted in Postgres. Each summary mirrors `schemas.BackupSummaryModel`.

### `POST /backups/refresh`

Forces a filesystem rescan using `BackupRegistry.refresh()`, updating or inserting metadata for each backup discovered under `backup_paths.base_path`.

### `POST /backups/{backup_id}/unlock`

Body: `{ "password": "<iTunes passphrase>" }`.  
Response: `{ "session_token": "...", "ttl_seconds": 3600 }`.  
Errors: `404` if backup unknown, `400` if the passphrase is incorrect. (@api/routes/backups.py#53-69)

### `POST /backups/{backup_id}/lock`

Headers: `X-Backup-Session`. Revokes the session token; idempotent even if token already expired. (@api/routes/backups.py#71-81)

### `GET /backups/{backup_id}/files`

Headers: `X-Backup-Session`. Query params:

| Param | Type | Description |
| --- | --- | --- |
| `domain` | string | Filter by manifest domain (e.g., `AppDomain-com.apple.MobileSMS`). |
| `path_like` | string | SQL `LIKE` pattern for `relative_path` (use `%` wildcards). |
| `limit` | int | Page size (default 100). |
| `offset` | int | Offset for pagination. |

Response: manifest entries as `schemas.ManifestEntryModel`. (@api/routes/backups.py#84-111)

### `GET /backups/{backup_id}/domains`

Headers: `X-Backup-Session`. Returns the list of manifest domains available for the unlocked backup. (@api/routes/backups.py#112-119)

### `GET /backups/{backup_id}/file/{file_id}`

Headers: `X-Backup-Session`. Streams the file contents for the requested manifest entry. The backend extracts to a sandbox, serves via `FileResponse`, and deletes the sandbox once the response completes. Errors:

- `404` if the file ID does not exist.
- `401` if the session token is missing/invalid.
- `403` if the token belongs to a different backup. (@api/routes/backups.py#122-151)

## Authentication Headers

| Header | Required | Description |
| --- | --- | --- |
| `X-API-Token` | Always | Matches `IOS_BACKUP_SECURITY__API_TOKEN`. (@api/security.py#8-12) |
| `X-Backup-Session` | Unlock-required routes | Issued by `/backups/{id}/unlock`, enforced by `require_session_token`. (@api/security.py#19-20) |

## Error Codes

- `400 Bad Request` – invalid unlock credentials or malformed parameters.
- `401 Unauthorized` – missing/invalid API or session tokens.
- `403 Forbidden` – session token does not belong to the requested backup.
- `404 Not Found` – missing backup, manifest entry, or file.
- `500 Internal Server Error` – unexpected worker/filesystem issues (see logs for stack traces).
