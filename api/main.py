from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import (
    artifacts_calendar,
    artifacts_calls,
    artifacts_contacts,
    artifacts_locations,
    artifacts_map,
    artifacts_messages,
    artifacts_notes,
    artifacts_photos,
    artifacts_safari,
    artifacts_voicemail,
    artifacts_whatsapp,
    backups,
    people,
    report,
    search,
    timeline,
)
from core.config import get_settings

logger = logging.getLogger(__name__)


def _run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config("alembic.ini"), "head")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="apple-juicer",
        version="0.1.0",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.trusted_hosts,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Backup-Session"],
    )

    @app.get("/healthz", tags=["system"])
    async def health_check():
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    async def root():
        return {"name": "apple-juicer", "status": "ok"}

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return None

    @app.on_event("startup")
    async def ensure_schema() -> None:
        # Apply migrations on boot. Run in a thread because Alembic's command
        # API starts its own event loop, which cannot nest in this one.
        await asyncio.to_thread(_run_migrations)
        logger.info("Database schema migrated to head")

    app.include_router(backups.router)
    app.include_router(artifacts_whatsapp.router)
    app.include_router(artifacts_messages.router)
    app.include_router(artifacts_photos.router)
    app.include_router(artifacts_notes.router)
    app.include_router(artifacts_calendar.router)
    app.include_router(artifacts_contacts.router)
    app.include_router(artifacts_calls.router)
    app.include_router(artifacts_safari.router)
    app.include_router(artifacts_locations.router)
    app.include_router(artifacts_map.router)
    app.include_router(artifacts_voicemail.router)
    app.include_router(people.router)
    app.include_router(report.router)
    app.include_router(search.router)
    app.include_router(timeline.router)

    return app


def run() -> None:  # pragma: no cover
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8080)
