---
title: "Tasks & Workflows"
description: "The recurring operations: discovering backups, unlocking, browsing, indexing, and purging."
---

Day to day, you do five things with Apple Juicer: discover new backups, unlock encrypted ones, browse and download, index artifacts, and occasionally purge data. Each maps to an endpoint you can also drive from a script.

## Discovering backups

1. Make sure backups exist under `APPLE_JUICER_BACKUP_PATHS__BASE_PATH`.
2. Call `POST /backups/refresh` (or click Refresh in the UI) to rescan.
3. New backups are inserted and existing ones updated in Postgres, with size, device name, and encryption flag.

If backups arrive regularly, run the refresh on a schedule.

## Unlocking and sessions

1. Enter the encryption passphrase in the UI.
2. `POST /backups/{id}/unlock` hands it to `UnlockManager`, which uses `iphone-backup-decrypt` to open the keybag and Manifest.
3. The response carries a `session_token` and a TTL. Send it as `X-Backup-Session` on the manifest and file routes.
4. To revoke early, call `POST /backups/{id}/lock`. It is idempotent.

Sessions live in memory, so restarting the backend clears them.

## Browsing and downloading

1. Page through manifest entries with `GET /backups/{id}/files`, filtering by `domain` and `path_like` and paging with `limit` and `offset`.
2. Stream a file with `GET /backups/{id}/file/{file_id}`, sending both the API and session headers. The backend deletes the temporary copy as soon as the response finishes.

## Indexing artifacts

1. Decrypting a backup enqueues `index_backup_job` for it.
2. The worker parses the artifact databases and writes the normalized tables and the search index.
3. When it finishes, the backup's status becomes `INDEXED` and the artifact tabs light up.

To re-index, enqueue another job. The worker truncates the previous rows first, so you always end up with consistent data.

## Purging data

- **Drop the decrypted copy** with `DELETE /backups/{id}/decrypted`. The encrypted backup stays put.
- **Remove a backup's rows** by deleting it in Postgres; `ON DELETE CASCADE` cleans up every related artifact automatically.
- **Empty the queue** with `rq empty default`.
- **Clear stale temp folders** under `backup_paths.temp_path` if the backend ever crashed mid-download.

## Automating it

A few endpoints lend themselves to a cron job or a watcher:

- **Scheduled refresh** — `curl -s -X POST http://localhost:8080/backups/refresh -H "X-API-Token: $TOKEN"` on a timer.
- **Re-index on change** — dispatch jobs for recently modified backups overnight.
- **Watch for new backups** — trigger the refresh the moment a new backup lands on the host.
