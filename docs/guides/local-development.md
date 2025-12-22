# Local Development

This guide walks through setting up iOS Backup Explorer directly on your host machine for rapid iteration.

## Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- PostgreSQL 16 (local or remote)
- Redis 7
- `libsqlite3` headers (parsers link against SQLite)

## 1. Clone & Create Virtual Environment

```bash
git clone https://github.com/giovi321/ios-backup-explorer.git
cd ios-backup-explorer
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
```

## 2. Provision Datastores

1. Start Postgres and create the database:

   ```bash
   createdb ios_backup_explorer
   psql -d ios_backup_explorer -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
   ```

2. Export connection details (or update `.env`):

   ```bash
   export IOS_BACKUP_POSTGRES__DSN="postgresql+asyncpg://postgres:postgres@localhost:5432/ios_backup_explorer"
   ```

3. Start Redis:

   ```bash
   redis-server
   # or brew services start redis / systemctl start redis
   ```

## 3. Frontend Tooling

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server listens on `http://localhost:5173` and proxies API calls to `http://localhost:8080`.

## 4. Backend API

From the repository root:

```bash
uvicorn api.main:create_app --factory --reload --host 0.0.0.0 --port 8080
```

### Environment helpers

| Variable | Description | Default |
| --- | --- | --- |
| `IOS_BACKUP_SECURITY__API_TOKEN` | Shared secret the frontend sends via `X-API-Token`. | `dev-token` |
| `IOS_BACKUP_BACKUP_PATHS__BASE_PATH` | Root directory where backups are mounted. | `/data/ios_backups` |
| `IOS_BACKUP_REDIS__URL` | Redis DSN. | `redis://localhost:6379/0` |

The full list is documented in [Configuration](../operations/configuration.md).

## 5. Worker

The worker consumes jobs from Redis and performs long-running parsing.

```bash
IOS_BACKUP_REDIS__URL=redis://localhost:6379/0 rq worker default
# or use the console script:
ios-backup-worker
```

Ensure the same virtualenv is active so the parsers and SQLAlchemy models resolve correctly.

## 6. Test the Flow

1. Place Finder/iTunes backups under `IOS_BACKUP_BACKUP_PATHS__BASE_PATH`.
2. Hit `http://localhost:5173/`, set the API token in the unlock modal, and start discovering backups.
3. Unlock an encrypted backup, browse manifest entries, and kick off artifact indexing.

## Tips

- Run `pytest` to execute unit tests (most reside under `core/` and `worker/`).
- Use `npm run test` for frontend Vitest suites.
- Enable `LOG_LEVEL=DEBUG` on the backend to troubleshoot discovery or unlock flows.
