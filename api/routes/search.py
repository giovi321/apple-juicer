from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api import schemas
from api.dependencies import get_backup_registry, get_db_session
from api.routes._common import get_backup_or_404, get_decrypted_backup
from api.security import require_api_token
from core.db.artifacts import ArtifactSearchIndex
from core.services import BackupRegistry

router = APIRouter(prefix="/backups", tags=["search"], dependencies=[Depends(require_api_token)])


@router.get("/{backup_id}/search", response_model=schemas.SearchResponse)
async def search_artifacts(
    backup_id: str,
    q: str = "",
    limit: int = 100,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    """Cross-artifact search over the per-backup search index."""
    await get_decrypted_backup(backup_id, registry)
    db_backup = await get_backup_or_404(backup_id, session)

    query = q.strip()
    if not query:
        return schemas.SearchResponse(query=q, items=[])

    pattern = f"%{query}%"
    result = await session.scalars(
        select(ArtifactSearchIndex)
        .where(ArtifactSearchIndex.backup_id == db_backup.id)
        .where(ArtifactSearchIndex.search_text.ilike(pattern))
        .order_by(ArtifactSearchIndex.artifact_type)
        .limit(limit)
    )
    items = [
        schemas.SearchResultModel(
            artifact_type=row.artifact_type,
            artifact_ref=row.artifact_ref,
            display_text=row.display_text,
            payload=row.payload,
        )
        for row in result
    ]
    return schemas.SearchResponse(query=q, items=items)
