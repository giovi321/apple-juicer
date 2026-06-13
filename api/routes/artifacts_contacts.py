from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api import schemas
from api.dependencies import get_backup_registry, get_db_session
from api.routes._common import get_backup_or_404, get_decrypted_backup
from api.security import require_api_token
from core.db.artifacts import Contact
from core.services import BackupRegistry

router = APIRouter(prefix="/backups", tags=["contacts"], dependencies=[Depends(require_api_token)])


def _serialize(contact: Contact) -> schemas.ContactModel:
    return schemas.ContactModel(
        contact_identifier=contact.contact_identifier,
        first_name=contact.first_name,
        last_name=contact.last_name,
        company=contact.company,
        emails=contact.emails or [],
        phones=contact.phones or [],
        avatar_file_id=contact.avatar_file_id,
    )


@router.get("/{backup_id}/artifacts/contacts", response_model=schemas.ContactListResponse)
async def list_contacts(
    backup_id: str,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    await get_decrypted_backup(backup_id, registry)
    db_backup = await get_backup_or_404(backup_id, session)
    result = await session.scalars(
        select(Contact)
        .where(Contact.backup_id == db_backup.id)
        .order_by(Contact.last_name.nullslast(), Contact.first_name.nullslast())
    )
    return schemas.ContactListResponse(items=[_serialize(contact) for contact in result])
