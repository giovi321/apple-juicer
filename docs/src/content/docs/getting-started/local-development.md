---
title: "Local Development"
description: "Run the backend, worker, and frontend directly on your machine for fast iteration."
---

Running the services by hand gives you reload-on-save and a debugger. You need Postgres and Redis somewhere reachable, a Python virtualenv for the backend and worker, and Node for the frontend. The whole loop is below.

## Prerequisites

- Python 3.11+
- Node.js 20+ and npm
- PostgreSQL 16 (local or remote)
- Redis 7

## Set up the Python side

```bash
git clone https://github.com/giovi321/apple-juicer.git
cd apple-juicer
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
```

## Bring up the datastores

Create the database and point the app at it:

```bash
createdb apple_juicer
export APPLE_JUICER_POSTGRES__DSN="postgresql+asyncpg://postgres:postgres@localhost:5432/apple_juicer"
```

The schema is applied automatically — Alembic runs `upgrade head` when the backend starts, so there is no manual migration step. Start Redis any way you like:

```bash
redis-server   # or: brew services start redis / systemctl start redis
```

## Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Vite serves on [http://localhost:5173](http://localhost:5173) and proxies API calls to the backend on 8080.

## Start the backend

From the repository root:

```bash
uvicorn api.main:create_app --factory --reload --host 0.0.0.0 --port 8080
```

The settings you will reach for most:

| Variable | What it does | Default |
|----------|--------------|---------|
| `APPLE_JUICER_SECURITY__API_TOKEN` | The token the frontend sends as `X-API-Token` | `dev-token` |
| `APPLE_JUICER_BACKUP_PATHS__BASE_PATH` | Where backups are mounted | `/data/ios_backups` |
| `APPLE_JUICER_REDIS__URL` | Redis DSN | `redis://localhost:6379/0` |

The full list is in [Configuration](../../operations/configuration/).

## Start the worker

The worker runs the decrypt and index jobs. Keep the same virtualenv active so the parsers and models resolve:

```bash
APPLE_JUICER_REDIS__URL=redis://localhost:6379/0 rq worker default
# or the console script:
apple-juicer-worker
```

## Try the flow

1. Drop a Finder/iTunes backup under `APPLE_JUICER_BACKUP_PATHS__BASE_PATH`.
2. Open the UI, paste the API token, and refresh to discover it.
3. Decrypt an encrypted backup, watch the status reach `indexed`, then browse its artifacts.

## Useful while developing

- `pytest` runs the backend and worker tests. They use SQLite, so you don't need Postgres for the suite.
- `npm run test` runs the frontend Vitest suites.
- `LOG_LEVEL=debug` on the backend surfaces the discovery and unlock internals when something misbehaves.
