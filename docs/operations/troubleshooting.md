# Troubleshooting

Use this checklist to diagnose the most common operational issues.

## Backend fails to start

- **Symptom:** Uvicorn exits with `ValidationError` referencing `trusted_hosts` or other nested settings.  
  **Fix:** Ensure nested environment variables use `__` delimiters (e.g., `IOS_BACKUP_SECURITY__TRUSTED_HOSTS__0`). The validators in `SecuritySettings` coerce dicts/CSV strings automatically, so malformed names usually cause the crash. (@core/config/settings.py#10-35)

- **Symptom:** `sqlalchemy.exc.OperationalError` connecting to Postgres.  
  **Fix:** Verify `IOS_BACKUP_POSTGRES__DSN` points at a reachable host. When running inside Docker Compose, use `postgres` as hostname; for local dev use `localhost`.

## Worker immediately exits (`Error 111 connecting to localhost:6379`)

- Ensure the worker command uses the Compose service name:  
  `["rq", "worker", "default", "--url", "redis://redis:6379/0"]`. (@docker-compose.yml#39-55)
- Confirm Redis is healthy: `docker compose logs redis`.
- If Redis logs `WARNING Memory overcommit must be enabled`, run `sudo sysctl vm.overcommit_memory=1` on the host (optional but recommended).

## Frontend “Connection was reset”

- Make sure port mapping matches Nginx (`5173:80`). If you see a blank page or reset, the host might still map to 4173 from an older compose file—rebuild after updating `docker-compose.yml`. (@docker-compose.yml#56-65)
- Check `frontend` container logs for Nginx errors.

## 404 spam for `/rest/system/*`

- These originate from browser extensions or security scanners hitting legacy endpoints. They’re harmless because our API only serves `/backups/*` and `/healthz`. Ignore unless you actually need to implement those endpoints.

## Unlock failures

- **Symptom:** `UnlockError` with “Failed to decrypt Manifest”.  
  - Verify the passphrase matches the one used when creating the iTunes backup.  
  - Check that the backup files are not read-only for the container; ensure mount options omit `:ro` temporarily if write access is required for temp decrypts (default flow uses temp dir, so read-only is fine).

## Manifest queries return zero results

- Confirm the backup was successfully unlocked; otherwise `X-Backup-Session` is missing and the backend returns 401/403. (@api/routes/backups.py#84-152)
- Use the `domain` and `path_like` filters carefully: `path_like` performs a SQL `LIKE`, so `%` wildcards may be necessary.

## Artifact views are empty

- The worker only populates tables after `index_backup_job` finishes. Check worker logs for ingestion progress.  
- If jobs fail mid-way, re-run indexing; the worker truncates artifact tables before ingesting so you always get consistent data. (@worker/tasks.py#72-90)

## Cleaning up temp directories

- If the backend crashes during downloads, decrypted files might linger under `backup_paths.temp_path`. Safest remediation: restart containers (startup hooks clear directories) or manually delete the stale folders.

## Getting more logs

- Backend: `uvicorn ... --log-level debug` or set `LOG_LEVEL=debug`.  
- Worker: `rq worker default --log-level DEBUG`.  
- Redis/Postgres: `docker compose logs redis --follow`.
