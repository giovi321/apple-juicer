# Data Storage

Apple Juicer persists its state across three layers: the filesystem, PostgreSQL, and Redis. Understanding how each layer is used helps with operations, scaling, and recovery.

## Filesystem Mounts

- **Backup data** – Finder/iTunes backups remain on disk and are mounted read-only into backend + worker containers (default `./data:/data/ios_backups`). No payloads are copied unless a user downloads a file.
- **Temporary sandbox** – Decrypted files extracted for download or parsing are staged under `backup_paths.temp_path` (default `/tmp/apple_juicer`). A Starlette `BackgroundTask` cleans up these folders after streaming. (@api/routes/backups.py#122-141)

## PostgreSQL Schema

### Core Tables

- `backups` – canonical list of discovered backups, including device metadata, size, encryption state, and status lifecycle from `DISCOVERED` → `INDEXING` → `INDEXED`. (@core/db/models.py#14-37)
- Artifact tables (`photo_assets`, `whatsapp_*`, `messages`, `notes`, `calendar_*`, `contacts`) – normalized views of SQLite artifacts parsed by the worker. Each row links back to `backups.id` with `ON DELETE CASCADE`. (@core/db/artifacts.py#13-197)
- `artifact_search_index` – denormalized text search surface combining display text + structured payload per artifact. Useful for global queries. (@core/db/artifacts.py#186-197)

### Sessions & Unlock Metadata

Session state is maintained by `UnlockManager` in memory, but the `BackupRegistry` tracks last unlock/index operations in Postgres. When you rescan (`POST /backups/refresh`), new entries are upserted via SQLAlchemy. (@worker/tasks.py#40-90)

### Engine Configuration

The async SQLAlchemy engine connects via `APPLE_JUICER_POSTGRES__DSN`, defaulting to `sqlite+aiosqlite:///./temp_data/apple_juicer.db` out of the box. Development builds can call `core.db.session.init_models()` to bootstrap tables without Alembic. (@core/db/session.py#1-24)

## Redis

Redis serves two roles:

1. **RQ Queue** – `core.queue.get_queue()` creates a cached Redis connection and defines the default queue with a 10-minute timeout. (@core/queue.py#11-24)
2. **Worker coordination** – RQ stores job metadata, heartbeats, and result payloads here. Set `APPLE_JUICER_REDIS__URL` to point at your Redis deployment.

Redis does **not** store session tokens or decrypted data; those remain in-memory within the backend/worker processes.

## Backup & Restore Strategy

1. **Filesystem** – treat the mounted backup directory as authoritative; snapshot or rsync from there.
2. **Postgres** – use native tools (`pg_dump`, `pg_basebackup`) to preserve registry + artifact indexes.
3. **Redis** – optional to persist; you can rebuild queues by re-triggering indexing runs if Redis data is lost.

Because decrypted payloads are never persisted in the database, a restore requires only re-pointing to the backup directory and optionally re-indexing artifacts.
