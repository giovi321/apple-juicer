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
    ("GET", "/backups/{backup_id}/artifacts/notes"),
    ("GET", "/backups/{backup_id}/artifacts/calendar/events"),
    ("GET", "/backups/{backup_id}/artifacts/contacts"),
    ("GET", "/backups/{backup_id}/artifacts/calls"),
    ("GET", "/backups/{backup_id}/artifacts/safari"),
    ("GET", "/backups/{backup_id}/search"),
}


def _backup_routes() -> set[tuple[str, str]]:
    from api.main import create_app

    app = create_app()
    routes: set[tuple[str, str]] = set()
    for route in app.routes:
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", "")
        if not methods or not path.startswith("/backups"):
            continue
        for method in methods:
            if method in ("HEAD", "OPTIONS"):
                continue
            routes.add((method, path))
    return routes


def test_backup_route_surface_unchanged():
    assert _backup_routes() == EXPECTED_BACKUP_ROUTES
