---
title: "Docker Compose"
description: "The bundled multi-service stack: Postgres, Redis, backend, worker, and the nginx-served frontend."
---

`docker compose up -d` is the supported way to run Apple Juicer. It starts five services — Postgres, Redis, the FastAPI backend, the RQ worker, and the React frontend behind nginx — wired together and reading the same `APPLE_JUICER_*` configuration.

## Before you start

- Docker Engine 24+ with the Compose v2 plugin (`docker compose`, not `docker-compose`).
- Roughly 4 CPU cores and 4 GB RAM for comfortable indexing runs.
- Your Finder/iTunes backups under `./data`, or another host path you bind-mount.

## What's in the box

- `docker-compose.yml` orchestrates the stack.
- `Dockerfile.backend` builds the shared backend + worker image (Python slim).
- `Dockerfile.frontend` builds the React app and serves it with `nginx:alpine`.
- `data/` is the default host directory mounted read-only into the backend and worker at `/data/ios_backups`.

## Configuration

Compose maps a handful of friendly host variables onto the nested settings the app reads. Set them in your shell or a `.env` file next to `docker-compose.yml`:

```bash
APPLE_JUICER_API_TOKEN=your-token              # → APPLE_JUICER_SECURITY__API_TOKEN
APPLE_JUICER_BACKUP_HOST_PATH=/path/to/backups # mounted at /data/ios_backups
APPLE_JUICER_DECRYPTED_HOST_PATH=/path/to/out  # where decrypted data lands
```

The Postgres and Redis DSNs are constructed inside `docker-compose.yml` from `POSTGRES_*` and `REDIS_PASSWORD`, so you rarely set them by hand. Every value has a sensible default; the only one worth changing before anything real is the token.

## Run it

```bash
docker compose up -d --build
```

These ports are published:

| Service | Port | Purpose |
|---------|------|---------|
| Frontend (nginx) | 5173 | React UI |
| Backend (uvicorn) | 8080 | REST API |
| Postgres | 5432 | Database (optional external access) |
| Redis | 6379 | Queue (optional external access) |

Confirm it came up: open [http://localhost:5173](http://localhost:5173), check `curl http://localhost:8080/healthz`, and look for `Listening on default...` in the worker logs.

## Pointing at backups elsewhere

Set `APPLE_JUICER_BACKUP_HOST_PATH` and Compose mounts it for both the backend and the worker. To hard-code a path instead, edit the volume in `docker-compose.yml`:

```yaml
  backend:
    volumes:
      - /mnt/backups:/data/ios_backups:ro
```

Keep the mount read-only, and apply the same change to the worker so both services can read payloads.

## Rebuilding just the frontend

When you change React code, rebuild that one image and leave the rest running:

```bash
docker compose build frontend
docker compose up -d frontend
```

## Tearing down

```bash
docker compose down       # stop and remove containers
docker compose down -v     # also drop the Postgres volume
```

Your backups are never touched by any of this — they stay on the host directory you mounted.
