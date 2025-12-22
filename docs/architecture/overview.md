# Architecture Overview

iOS Backup Explorer is composed of five cooperating subsystems:

1. **FastAPI backend** – hosts REST endpoints for discovery, unlocking, manifest browsing, and artifact exports.
2. **Redis + RQ worker** – runs asynchronous ingestion jobs that parse SQLite artifacts and populate Postgres.
3. **PostgreSQL** – persists backups, sessions, manifest indexes, and normalized artifact tables.
4. **React + Vite frontend** – provides the investigator UI and speaks to the backend via authenticated JSON APIs.
5. **Backup filesystem layer** – mounts Finder/iTunes backups, unlocks encrypted bundles, and exposes Manifest data.

## Runtime Topology

```
Browser ──▶ Frontend (Nginx → React)
             │  ↳ fetch() w/ X-API-Token & X-Backup-Session
             ▼
        FastAPI backend ──▶ Postgres (async SQLAlchemy)
             │
             ├─▶ Redis (RQ) ──▶ Worker pods (rq worker default)
             │
             └─▶ BackupFS (iphone_backup_decrypt + local paths)
```

- The backend is stateless; it uses Redis for session caches and Postgres for durability.
- Workers share the same container image as the backend to reuse parsers and settings.
- Backups remain on disk and are mounted read-only into backend/worker containers.

## Major Data Flows

1. **Discovery** – `BackupRegistry` scans `backup_paths.base_path`, records metadata in Postgres, and exposes summaries via `/backups`.  
2. **Unlocking** – `UnlockManager` decrypts encrypted backups using `iphone_backup_decrypt`, caches a live session, and issues an `X-Backup-Session` token.  
3. **Manifest browsing** – the frontend pages through `/backups/{id}/files` and `/domains`, streaming metadata without copying payloads.  
4. **Artifact indexing** – the frontend dispatches a job that enqueues `index_backup_job` → worker parses domain-specific SQLite DBs and writes normalized rows plus a search index.  
5. **Downloads** – the backend extracts requested files into a temporary sandbox and streams them to the browser, deleting the sandbox via a Starlette `BackgroundTask`.

Each step is fully asynchronous, making it straightforward to scale backend replicas, workers, or Postgres independently as data volumes grow.
