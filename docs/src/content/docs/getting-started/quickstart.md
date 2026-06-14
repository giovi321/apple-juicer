---
title: "Quick Start"
description: "Get the full stack running with Docker Compose, or run the services directly for development."
---

The fastest way in is Docker Compose: clone, mount your backups, bring up the stack, paste the token. Running the services by hand takes a few more steps but gives you reload-on-save for development. Both are below.

## Before you start

You need one of these:

- **Docker** — Docker Engine 24+ and Docker Compose v2.
- **The toolchain** — Python 3.11+, Node.js 20+, Redis 7, and PostgreSQL 16.

Either way, have a Finder/iTunes backup directory ready. Read-only access is fine; Apple Juicer never writes to your backups.

## Option A — Docker Compose

```bash
git clone https://github.com/giovi321/apple-juicer.git
cd apple-juicer
```

Put your backups under `./data`, or point `docker-compose.yml` at a different host folder. Then set the token and backup path (a `.env` file next to `docker-compose.yml` works too):

```bash
export APPLE_JUICER_API_TOKEN="dev-token"
export APPLE_JUICER_BACKUP_HOST_PATH="/path/to/your/backups"
```

Bring up the stack:

```bash
docker compose up -d
```

Open [http://localhost:5173](http://localhost:5173), paste the API token, and refresh to discover your backups. Two quick health checks:

- `curl http://localhost:8080/healthz` returns `{"status":"ok"}`.
- The worker logs show `Listening on default...`.

Stop everything with `docker compose down`. Add `-v` to also drop the Postgres volume.

## Option B — Run the services directly

Prefer to debug with live reload? Set up a virtualenv first:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -e ".[dev]"
```

Bring up Postgres and Redis (containers or local services), then point the app at them:

```bash
export APPLE_JUICER_POSTGRES__DSN="postgresql+asyncpg://postgres:postgres@localhost:5432/apple_juicer"
export APPLE_JUICER_REDIS__URL="redis://localhost:6379/0"
```

Start the three processes in their own terminals:

```bash
# backend
uvicorn api.main:create_app --factory --reload --host 0.0.0.0 --port 8080

# worker
rq worker default          # or: apple-juicer-worker

# frontend
cd frontend && npm install && npm run dev
```

Open [http://localhost:5173](http://localhost:5173), paste the token, and load backups from `APPLE_JUICER_BACKUP_PATHS__BASE_PATH`. The [Local Development](../local-development/) guide goes deeper.

## Next steps

- Tune the runtime in [Configuration](../../operations/configuration/).
- See how the pieces fit in the [Architecture Overview](../../architecture/overview/).
- Run the tests: `pytest` for the backend and worker, `npm run test` inside `frontend/`.
