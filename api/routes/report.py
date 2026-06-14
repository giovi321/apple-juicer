from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_backup_registry, get_db_session
from api.routes._common import get_backup_or_404, get_decrypted_backup
from api.security import require_api_token
from core.db.artifacts import (
    CalendarEvent,
    CallRecord,
    Contact,
    LocationPoint,
    Message,
    Note,
    PhotoAsset,
    SafariVisit,
    Voicemail,
    WhatsAppMessage,
)
from core.db.models import Backup
from core.services import BackupRegistry

router = APIRouter(prefix="/backups", tags=["report"], dependencies=[Depends(require_api_token)])

# (label, model) for the headline count of each artifact type.
ARTIFACT_COUNTS = [
    ("WhatsApp messages", WhatsAppMessage),
    ("iMessage / SMS", Message),
    ("Photos", PhotoAsset),
    ("Notes", Note),
    ("Calendar events", CalendarEvent),
    ("Contacts", Contact),
    ("Calls", CallRecord),
    ("Safari visits", SafariVisit),
    ("Locations", LocationPoint),
    ("Voicemails", Voicemail),
]


def _latin1(value: object) -> str:
    """Helvetica is latin-1 only; drop characters it can't render."""
    text = "-" if value is None else str(value)
    return text.encode("latin-1", "replace").decode("latin-1")


def _build_pdf(backup: Backup, counts: list[tuple[str, int]], generated_at: datetime) -> bytes:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Apple Juicer - Backup Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, f"Generated {generated_at:%Y-%m-%d %H:%M UTC}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    def field(label: str, value: object) -> None:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(45, 7, f"{label}:")
        pdf.set_font("Helvetica", size=11)
        pdf.cell(0, 7, _latin1(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    field("Display name", backup.display_name)
    field("Device", backup.device_name)
    field("iOS version", backup.product_version)
    field("Identifier", backup.ios_identifier)
    field("Size (GB)", f"{backup.size_bytes / 1024**3:.2f}" if backup.size_bytes else "-")
    field("Decrypted at", backup.decrypted_at)
    field("Last indexed", backup.last_indexed_at)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Indexed artifacts", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", size=11)
    for label, count in counts:
        pdf.cell(90, 7, _latin1(label))
        pdf.cell(0, 7, str(count), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    return bytes(pdf.output())


@router.get("/{backup_id}/report.pdf")
async def backup_report(
    backup_id: str,
    registry: BackupRegistry = Depends(get_backup_registry),
    session: AsyncSession = Depends(get_db_session),
):
    """Generate a one-page PDF summary of the backup and its indexed artifacts."""
    backup = await get_decrypted_backup(backup_id, registry)
    db_backup = await get_backup_or_404(backup_id, session)

    counts: list[tuple[str, int]] = []
    for label, model in ARTIFACT_COUNTS:
        total = await session.scalar(
            select(func.count()).select_from(model).where(model.backup_id == db_backup.id)
        )
        counts.append((label, int(total or 0)))

    pdf_bytes = _build_pdf(db_backup, counts, datetime.utcnow())
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report-{backup.ios_identifier}.pdf"'},
    )
