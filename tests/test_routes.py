"""Snapshot of the public /backups route surface.

This guards the route-monolith split: moving handlers between modules must not
add, drop, or rename any endpoint. Captured from the pre-split app.
"""

from __future__ import annotations

EXPECTED_BACKUP_ROUTES = {
    ("GET", "/backups"),
    ("POST", "/backups/refresh"),
    ("POST", "/backups/{backup_id}/decrypt"),
    ("GET", "/backups/{backup_id}/decrypt-status"),
    ("DELETE", "/backups/{backup_id}/decrypted"),
    ("POST", "/backups/{backup_id}/unlock"),
    ("POST", "/backups/{backup_id}/lock"),
    ("GET", "/backups/{backup_id}/files"),
    ("GET", "/backups/{backup_id}/domains"),
    ("GET", "/backups/{backup_id}/file/{file_id}"),
    ("GET", "/backups/{backup_id}/artifacts/whatsapp/chats"),
    ("GET", "/backups/{backup_id}/artifacts/whatsapp/chats/{chat_guid}"),
    ("GET", "/backups/{backup_id}/artifacts/whatsapp/attachment"),
    ("POST", "/backups/{backup_id}/extract/whatsapp/{chat_guid}"),
    ("GET", "/backups/{backup_id}/artifacts/messages/conversations"),
    ("GET", "/backups/{backup_id}/artifacts/messages/conversations/{conversation_guid}"),
    ("GET", "/backups/{backup_id}/artifacts/messages/attachment"),
    ("POST", "/backups/{backup_id}/extract/messages/{conversation_guid}"),
    ("GET", "/backups/{backup_id}/artifacts/photos"),
    ("GET", "/backups/{backup_id}/artifacts/photos/file"),
    ("GET", "/backups/{backup_id}/artifacts/notes"),
    ("GET", "/backups/{backup_id}/artifacts/calendar/events"),
    ("GET", "/backups/{backup_id}/artifacts/contacts"),
    ("GET", "/backups/{backup_id}/artifacts/calls"),
    ("GET", "/backups/{backup_id}/artifacts/safari"),
    ("GET", "/backups/{backup_id}/artifacts/locations"),
    ("GET", "/backups/{backup_id}/artifacts/voicemail"),
    ("GET", "/backups/{backup_id}/report.pdf"),
    ("GET", "/backups/{backup_id}/search"),
    ("GET", "/backups/{backup_id}/timeline"),
    ("GET", "/backups/{backup_id}/people"),
    ("GET", "/backups/{backup_id}/people/{key}"),
}


def _iter_routes(routes):
    """Yield every (methods, path) pair, recursing into included routers.

    FastAPI 0.137 stopped flattening ``include_router`` calls into
    ``app.routes`` and instead inserts an ``_IncludedRouter`` wrapper that
    exposes the original ``APIRouter`` via ``original_router``. Recursing
    through it keeps this snapshot working on both the old and new layouts.
    """
    for route in routes:
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", "")
        if methods and path:
            yield methods, path
        original = getattr(route, "original_router", None)
        if original is not None:
            yield from _iter_routes(getattr(original, "routes", []))


def _backup_routes() -> set[tuple[str, str]]:
    from api.main import create_app

    app = create_app()
    routes: set[tuple[str, str]] = set()
    for methods, path in _iter_routes(app.routes):
        if not path.startswith("/backups"):
            continue
        for method in methods:
            if method in ("HEAD", "OPTIONS"):
                continue
            routes.add((method, path))
    return routes


def test_backup_route_surface_unchanged():
    assert _backup_routes() == EXPECTED_BACKUP_ROUTES
