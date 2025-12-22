# Docker Compose Deployment

The repository ships with a production-like stack powered by Docker Compose. It wires Postgres, Redis, the FastAPI backend, the RQ worker, and the Vite frontend (served via Nginx).

## Prerequisites

- Docker Engine 24+
- Docker Compose v2 plugin (`docker compose` syntax)
- At least 4 CPU cores and 4 GB RAM for smooth indexing runs
- Local Finder/iTunes backups mounted under `./data` (or a different host path you bind-mount)

## File Layout

- `docker-compose.yml` – Orchestrates the multi-service stack.
- `Dockerfile.backend` – Builds the backend + worker image (Python 3.11 slim).
- `Dockerfile.frontend` – Builds the React app and ships it with `nginx:alpine`.
- `data/` – Default host directory that is mounted read-only into backend + worker at `/data/ios_backups`.

## Environment Variables

You can override any Pydantic setting by exporting `IOS_BACKUP_*` variables before running Compose. Common overrides:

```bash
export IOS_BACKUP_SECURITY__API_TOKEN="your-prod-token"
export IOS_BACKUP_BACKUP_PATHS__BASE_PATH="/data/ios_backups"
export IOS_BACKUP_REDIS__URL="redis://redis:6379/0"
```

For secrets, prefer a `.env` file placed next to `docker-compose.yml`.

## Build & Run

```bash
docker compose build
docker compose up
```

The following ports are published:

| Service | Port | Purpose |
| --- | --- | --- |
| Frontend (nginx) | `5173` | React UI |
| Backend (uvicorn) | `8080` | FastAPI REST API |
| Postgres | `5432` | Database (optional external access) |
| Redis | `6379` | Queue (optional external access) |

Stop the stack with `docker compose down` (add `-v` to drop the Postgres volume).

## Health Verification

1. Visit `http://localhost:5173/`.
2. Confirm `/healthz` on the backend: `curl http://localhost:8080/healthz`.
3. Check worker logs for `Listening on default...`.

## Changing Mount Paths

To scan backups from another host folder, edit `docker-compose.yml`:

```yaml
  backend:
    volumes:
      - /mnt/backups:/data/ios_backups:ro
```

Apply the same mount to the worker so both services can read payloads.

## Rebuilding Frontend Only

When tweaking React code, rebuild just the frontend image:

```bash
docker compose build frontend
docker compose up frontend
```

The backend/worker containers will keep their state as long as you do not recreate them.

## Cleaning Up

```bash
docker compose down -v  # removes containers + volumes (drops Postgres data)
docker image prune -f   # optional, remove dangling layers
```

Backups are never deleted—they remain on the host filesystem you mounted.
