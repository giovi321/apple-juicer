# Quick Start

Get the full stack running in under ten minutes with Docker Compose, or jump into local development if you want maximal control.

## Prerequisites

- Git
- Docker Engine 24+ and Docker Compose v2 **or** Python 3.11+, Node.js 18+, Redis 7, PostgreSQL 16
- Finder/iTunes backup directory (read-only is fine)

## 1. Clone the Repository

```bash
git clone https://github.com/giovi321/apple-juicer.git
cd apple-juicer
```

## 2. Fast Path: Docker Compose

1. Place backups under `./data` or bind a different host path in `docker-compose.yml`.
2. Export secrets (or create a `.env` file):

   ```bash
   export APPLE_JUICER_SECURITY__API_TOKEN="dev-token"
   export APPLE_JUICER_BACKUP_PATHS__BASE_PATH="/data/ios_backups"
   ```

3. Build and launch the stack:

   ```bash
   docker compose build
   docker compose up
   ```

4. Open `http://localhost:5173/`, enter the API token, and start discovering backups. Health checks:

   - Backend: `curl http://localhost:8080/healthz`
   - Worker logs show `Listening on default...`

Stop everything with `docker compose down` (add `-v` to drop Postgres volume).

## 3. Local Development Loop

Prefer running services directly for debugging? Follow the condensed steps below, then see [Local Development](./local-development.md) for deeper context.

1. Create & activate a virtualenv, then install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install -e ".[dev]"
   ```

2. Provision Postgres + Redis (use containers or local services) and export env vars:

   ```bash
   export APPLE_JUICER_POSTGRES__DSN="postgresql+asyncpg://postgres:postgres@localhost:5432/apple_juicer"
   export APPLE_JUICER_REDIS__URL="redis://localhost:6379/0"
   ```

3. Run the backend API:

   ```bash
   uvicorn api.main:create_app --factory --reload --host 0.0.0.0 --port 8080
   ```

4. In another terminal, start the worker:

   ```bash
   rq worker default
   # or apple-juicer-worker
   ```

5. Launch the frontend:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

Visit `http://localhost:5173/`, paste the API token, and load backups from `APPLE_JUICER_BACKUP_PATHS__BASE_PATH`.

## 4. Next Steps

- Configure advanced settings in [Operations → Configuration](../operations/configuration.md).
- Explore system architecture under [Architecture](../architecture/overview.md).
- Run tests: `pytest` for backend/workers, `npm run test` inside `frontend/`.

You now have a working stack ready for investigating iOS backups.
