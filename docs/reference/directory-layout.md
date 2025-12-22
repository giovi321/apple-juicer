# Directory Layout

Use this map to orient yourself inside the repository.

```
.
├── api/                   # FastAPI app, routers, dependencies, schemas
│   ├── main.py            # create_app factory + uvicorn entrypoint
│   ├── routes/            # REST routers (backups, future APIs)
│   ├── schemas/           # Pydantic response/request models
│   └── security.py        # Header-based auth dependencies
├── core/                  # Shared domain logic
│   ├── backupfs/          # Filesystem & session cache helpers
│   ├── config/            # Pydantic settings + env wiring
│   ├── db/                # SQLAlchemy models, sessions, migrations
│   ├── queue.py           # Redis/RQ helpers
│   └── services/          # Backup registry, unlock manager, etc.
├── worker/                # RQ worker tasks + CLI entrypoints
├── parsers/               # SQLite artifact parsers (photos, messages, etc.)
├── frontend/              # React + Vite SPA served via Nginx
│   ├── src/App.tsx        # Main UI component
│   ├── src/lib/api.ts     # Typed fetch client
│   └── src/lib/types.ts   # Shared TypeScript types
├── Dockerfile.backend     # Multi-stage build for backend + worker
├── Dockerfile.frontend    # Vite build + Nginx runtime
├── docker-compose.yml     # Orchestrates Postgres, Redis, backend, worker, frontend
├── mkdocs.yml             # Material for MkDocs configuration
├── docs/                  # Documentation sources (this site)
└── README.md              # Quick summary + developer commands
```

## Notable Supporting Files

- `pyproject.toml` – Poetry-style metadata using `setuptools`; defines console scripts (backend, worker) and dependency groups.
- `alembic/` + `alembic.ini` – Database migration scaffolding if you decide to track schema changes formally.
- `.dockerignore` – Keeps build contexts small; ensures `node_modules`, `.venv`, etc. stay out of Docker layers.

## Adding New Modules

1. Place shared business logic under `core/` and expose it via FastAPI routers.
2. Update `mkdocs.yml` navigation when adding new documentation pages so the site reflects the latest structure.
3. Keep parser-specific logic in `parsers/` to avoid bloating worker tasks or backend services.
