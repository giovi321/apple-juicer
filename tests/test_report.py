"""The backup report endpoint returns a valid PDF for an indexed backup."""

from __future__ import annotations

from sqlalchemy import select

from fixtures import build_all


class _Registry:
    def __init__(self, session):
        self.session = session

    async def get_backup(self, identifier: str):
        from core.db.models import Backup

        return await self.session.scalar(select(Backup).where(Backup.ios_identifier == identifier))


async def test_report_returns_pdf(db, tmp_path):
    from core.db.models import Backup, DecryptionStatus
    from core.db.session import async_session_factory
    from worker.tasks import _index_backup_job

    from api.routes import report

    decrypted = tmp_path / "decrypted"
    artifact_files = build_all(decrypted)
    backup_id = "REPORT-1"

    async with async_session_factory() as session:
        session.add(
            Backup(ios_identifier=backup_id, path=str(tmp_path / "src"), display_name="Test", is_encrypted=True)
        )
        await session.commit()

    await _index_backup_job(backup_id, str(decrypted), artifact_files)

    async with async_session_factory() as session:
        backup = await session.scalar(select(Backup).where(Backup.ios_identifier == backup_id))
        backup.decryption_status = DecryptionStatus.DECRYPTED
        backup.decrypted_path = str(decrypted)
        await session.commit()

    async with async_session_factory() as session:
        registry = _Registry(session)
        response = await report.backup_report(backup_id, registry=registry, session=session)

    assert response.media_type == "application/pdf"
    assert response.body.startswith(b"%PDF")
    assert len(response.body) > 500  # a non-trivial document
