from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import backups
from core.config import get_settings
from core.db.session import init_models

logger = logging.getLogger(__name__)


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

    if settings.environment != "production":
        # Development deployments rely on init_models() instead of Alembic.
        @app.on_event("startup")
        async def ensure_schema() -> None:
            await init_models()
            logger.info("Database schema ensured via init_models()")

    app.include_router(backups.router)

    return app


def run() -> None:  # pragma: no cover
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8080)
