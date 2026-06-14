---
title: "Directory Layout"
description: "A map of the repository — where the backend, worker, parsers, frontend, and docs live."
---

This is the lay of the land. The backend, worker, and parsers are Python; the frontend is a Vite app; the docs are this Astro Starlight site. The one structural idea worth internalizing is the `ArtifactSpec` registry in `core/artifacts/` — it's what makes a new artifact type a single registration instead of a change in four places.

```
.
├── api/                   # FastAPI app, routers, dependencies, schemas
│   ├── main.py            # create_app factory + uvicorn entrypoint
│   ├── routes/            # REST routers (backups + per-artifact + search/timeline/report)
│   ├── schemas.py         # Pydantic response/request models
│   └── security.py        # Header-based auth dependencies
├── core/                  # Shared domain logic
│   ├── artifacts/         # ArtifactSpec registry + uniform ingest (one registration per type)
│   ├── backupfs/          # Filesystem & session cache helpers
│   ├── config/            # Pydantic settings + env wiring
│   ├── db/                # SQLAlchemy models + async sessions
│   ├── queue.py           # Redis/RQ helpers
│   └── services/          # Backup registry, unlock manager, etc.
├── worker/                # RQ worker tasks + CLI entrypoints
├── parsers/               # SQLite artifact parsers (photos, messages, etc.)
├── alembic/               # Database migrations (applied on backend startup)
├── frontend/              # React + Vite SPA served via nginx
│   ├── src/main.tsx       # Entry point (mounts the app in an ErrorBoundary)
│   ├── src/AppNew.tsx     # Root component + app state machine
│   ├── src/pages/         # Screen components (BackupSelector, PasswordPrompt, Explorer)
│   ├── src/pages/modules/ # Per-artifact modules rendered inside the Explorer
│   ├── src/components/    # Cross-cutting components (ErrorBoundary)
│   └── src/lib/           # Typed fetch client (api.ts), types.ts, csv.ts
├── Dockerfile.backend     # Multi-stage build for backend + worker
├── Dockerfile.frontend    # Vite build + nginx runtime
├── docker-compose.yml     # Orchestrates Postgres, Redis, backend, worker, frontend
├── docs/                  # Astro Starlight documentation (this site)
└── README.md              # Quick summary + developer commands
```

## Supporting files worth knowing

- `pyproject.toml` defines the package metadata and the console scripts, including `apple-juicer-worker`.
- `alembic/` plus `alembic.ini` hold the migrations. They apply to `head` automatically on backend startup; add a revision whenever the models change.
- `.dockerignore` keeps `node_modules`, `.venv`, and friends out of the Docker build context.

## Adding a new artifact type

The registry is what keeps this to one place per concern:

1. Add a parser under `parsers/` that reads the source SQLite database into records.
2. Register an `ArtifactSpec` in `core/artifacts/registry.py` — parser, ORM models, schemas, ingest, and router. The worker and the API both iterate the registry, so this one registration wires up indexing, the search rows, and the extraction targets.
3. Add a frontend module under `frontend/src/pages/modules/`, a tab in `Explorer`, and a typed helper in `frontend/src/lib/api.ts`.
4. Generate an Alembic revision for any new tables, and add a sidebar entry in `docs/astro.config.mjs` if you write a new docs page.
