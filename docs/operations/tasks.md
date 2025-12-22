# Tasks & Workflows

This page outlines the recurring operational workflows for iOS Backup Explorer.

## Discovering Backups

1. Ensure backups exist under `IOS_BACKUP_BACKUP_PATHS__BASE_PATH`.
2. Call `POST /backups/refresh` (or click “Refresh” in the UI) to scan the filesystem.
3. Newly discovered backups are inserted or existing rows updated in Postgres, including size bytes, device name, and encryption flags. (@api/routes/backups.py#34-51)

Tip: run refresh on a schedule (cron, GitHub Actions, etc.) if new backups arrive regularly.

## Unlocking & Session Handling

1. User supplies the encryption passphrase in the UI.
2. `POST /backups/{id}/unlock` calls `UnlockManager` → `iphone_backup_decrypt` to unlock the keybag and Manifest. (@api/routes/backups.py#53-69)
3. The response includes `session_token` and TTL which must be set as `X-Backup-Session` for subsequent manifest/file calls.
4. To revoke credentials early, call `POST /backups/{id}/lock` (idempotent). (@api/routes/backups.py#71-81)

Sessions are stored in memory, so rebooting the backend clears them automatically.

## Browsing & Downloads

1. Use `GET /backups/{id}/files` with `domain`, `path_like`, `limit`, and `offset` query params to page through Manifest entries. (@api/routes/backups.py#84-111)
2. Download files with `GET /backups/{id}/file/{file_id}` – remember to set both API and session headers. The backend deletes temp files right after the response finishes. (@api/routes/backups.py#122-141)

## Indexing Artifacts

1. Trigger a job (currently via UI button) that enqueues `index_backup_job` with artifact bundle metadata.
2. Worker pulls the job, parses SQLite DBs, and writes normalized tables. (@worker/tasks.py#40-332)
3. Once finished, `backups.status` updates to `INDEXED`, and artifact tabs in the UI become available.

To reindex, simply enqueue another job. The worker truncates previous artifacts before ingesting new data. (@worker/tasks.py#72-90)

## Purging Data

- Delete a backup via SQL (`DELETE FROM backups WHERE ios_identifier='...'`) or add API support if needed. Cascades clean the related artifacts automatically because of `ON DELETE CASCADE`.
- Clean Redis queues with `rq empty default`.
- Remove temp folders under `backup_paths.temp_path` whenever the backend or worker crashes mid-download.

## Automation Ideas

- **Cron refresh** – `docker exec backend-1 curl -s -X POST http://backend:8080/backups/refresh`.
- **Scheduled reindex** – dispatch jobs nightly for recently modified backups.
- **Webhook integration** – watch for new backups landing on the host and immediately call the refresh endpoint.
