---
title: "Troubleshooting"
description: "The common failures and what fixes them — startup errors, worker crashes, empty views."
---

Most problems come down to one of three things: a malformed environment variable, a service that can't reach Redis or Postgres, or a backup that hasn't finished indexing. Work down the list below; each entry pairs the symptom you'll see with the fix.

## The backend won't start

**`ValidationError` mentioning `trusted_hosts` or another nested setting.** A nested variable is misspelled. They use `__` as the delimiter, for example `APPLE_JUICER_SECURITY__TRUSTED_HOSTS__0`. The validators coerce both CSV strings and indexed lists, so a malformed name is usually the cause.

**`OperationalError` connecting to Postgres.** Check that `APPLE_JUICER_POSTGRES__DSN` points somewhere reachable. Inside Docker Compose the host is `postgres`; for local development it's `localhost`.

## The worker exits immediately (`Error 111 connecting to localhost:6379`)

It can't reach Redis. In Compose, the worker command must use the service name:

```yaml
command: ["rq", "worker", "default", "--url", "redis://redis:6379/0"]
```

Confirm Redis is healthy with `docker compose logs redis`. If Redis warns `Memory overcommit must be enabled`, run `sudo sysctl vm.overcommit_memory=1` on the host.

## The frontend shows "Connection was reset"

The port mapping is off. nginx serves on 80 inside the container, mapped to 5173 on the host (`5173:80`). If you upgraded from an older Compose file that mapped 4173, rebuild after fixing `docker-compose.yml`. Check the `frontend` container logs for nginx errors.

## Unlock fails with "Failed to decrypt Manifest"

The passphrase is wrong, or the files aren't readable. Confirm it matches the one used to encrypt the backup in iTunes/Finder, and that the mount lets the container read the backup files. The default flow extracts to a temp directory, so a read-only mount is fine.

## Manifest queries return nothing

The session header is missing or the filter is too tight. Without a valid `X-Backup-Session` the backend returns 401/403, so make sure the backup is unlocked. Remember that `path_like` is a SQL `LIKE`, so you usually need `%` wildcards.

## Artifact views are empty

Indexing hasn't run or didn't finish. The worker only populates the tables once `index_backup_job` completes, so check its logs for progress. If a job died partway, re-run it — the worker truncates before ingesting, so you always get a clean result. A couple of artifact types are empty by design when their source isn't in the backup: significant locations (the `routined` cache is often excluded) and sometimes Safari history (its database domain varies by iOS version).

## Stray temp directories

If the backend crashed during a download, decrypted files can linger under `backup_paths.temp_path`. Restart the containers (startup clears the directories) or delete the stale folders by hand.

## Getting more detail

- Backend: `uvicorn ... --log-level debug`, or set `LOG_LEVEL=debug`.
- Worker: `rq worker default --log-level DEBUG`.
- Services: `docker compose logs redis --follow` (or `postgres`).
