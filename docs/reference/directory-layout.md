# Directory Layout

Use this map to orient yourself inside the repository.

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
├── frontend/              # React + Vite SPA served via Nginx
│   ├── src/main.tsx       # Entry point (mounts the app in an ErrorBoundary)
│   ├── src/AppNew.tsx     # Root component + app state machine
│   ├── src/pages/         # Screen components (BackupSelector, PasswordPrompt, Explorer)
│   ├── src/pages/modules/ # Per-artifact modules rendered inside the Explorer
│   ├── src/components/    # Cross-cutting components (ErrorBoundary)
│   └── src/lib/           # Typed fetch client (api.ts), types.ts, csv.ts
├── Dockerfile.backend     # Multi-stage build for backend + worker
├── Dockerfile.frontend    # Vite build + Nginx runtime
├── docker-compose.yml     # Orchestrates Postgres, Redis, backend, worker, frontend
├── mkdocs.yml             # Material for MkDocs configuration
├── docs/                  # Documentation sources (this site)
└── README.md              # Quick summary + developer commands
```

## Notable Supporting Files

- `pyproject.toml` – Poetry-style metadata using `setuptools`; defines console scripts (backend, worker) and dependency groups.
- `alembic/` + `alembic.ini` – Database migrations. They are applied to `head` automatically on backend startup; add a revision whenever the models change.
- `.dockerignore` – Keeps build contexts small; ensures `node_modules`, `.venv`, etc. stay out of Docker layers.

## Adding a New Artifact Type

1. Add a parser under `parsers/` that reads the source SQLite DB into records.
2. Register an `ArtifactSpec` in `core/artifacts/registry.py` (parser + ORM models + schemas + ingest + router). The worker and API both iterate the registry, so this single registration wires up indexing, search rows, and extraction targets.
3. Add a frontend module under `frontend/src/pages/modules/` and a tab in `Explorer`, plus a typed helper in `frontend/src/lib/api.ts`.
4. Generate an Alembic revision for any new tables, and update `mkdocs.yml` navigation when adding documentation pages.
