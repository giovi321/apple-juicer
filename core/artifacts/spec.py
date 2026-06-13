from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Awaitable, Callable

if TYPE_CHECKING:
    from core.db.models import Backup
    from sqlalchemy.ext.asyncio import AsyncSession

IngestFn = Callable[["AsyncSession", "Backup", "Path | None"], Awaitable[None]]


@dataclass(frozen=True)
class ArtifactSpec:
    """One iOS artifact type, defined in a single place.

    The worker iterates the registry to ingest, the decrypt orchestrator uses
    ``source_domain``/``source_relative_path`` to extract the source DB, and the
    API maps ``db_filename`` back to ``key`` — so adding an artifact is one
    registration instead of edits scattered across four files.
    """

    key: str
    db_filename: str
    source_domain: str
    source_relative_path: str
    ingest: IngestFn
