"""Tests for decrypt-status honesty: a backup is only 'decrypted' if the
Manifest database was actually produced; missing optional artifact DBs are
tolerated, not silently treated as success-with-no-data.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _make_orchestrator(monkeypatch, tmp_path, save_manifest, extract):
    import core.services.decrypt_orchestrator as do

    class FakeBackup:
        def __init__(self, backup_directory, passphrase):
            self.backup_directory = backup_directory

        def test_decryption(self):
            return None

        def save_manifest_file(self, path):
            save_manifest(Path(path))

        def extract_file(self, relative_path, domain_like, output_filename):
            extract(Path(output_filename))

    monkeypatch.setattr(do, "EncryptedBackup", FakeBackup)

    src = tmp_path / "src"
    src.mkdir(exist_ok=True)
    out = tmp_path / "out"
    orchestrator = do.DecryptOrchestrator(decrypted_base_path=str(out))

    from core.db.models import Backup

    backup = Backup(ios_identifier="DEC-1", path=str(src), display_name="x", is_encrypted=True)
    return do, orchestrator, backup


def test_missing_manifest_raises(monkeypatch, tmp_path):
    do, orchestrator, backup = _make_orchestrator(
        monkeypatch,
        tmp_path,
        save_manifest=lambda p: None,  # manifest never written
        extract=lambda p: p.write_bytes(b"db"),
    )
    with pytest.raises(do.DecryptionError):
        orchestrator.decrypt_backup(backup, "pw")


def test_success_tolerates_missing_artifacts(monkeypatch, tmp_path):
    # Manifest is produced; only Calendar.sqlite "extracts", the rest are absent.
    do, orchestrator, backup = _make_orchestrator(
        monkeypatch,
        tmp_path,
        save_manifest=lambda p: p.write_bytes(b"manifest"),
        extract=lambda p: p.write_bytes(b"db") if p.name == "Calendar.sqlite" else None,
    )
    result = orchestrator.decrypt_backup(backup, "pw")

    result_dir = Path(result)
    assert (result_dir / "Manifest.db").exists()
    assert (result_dir / "Calendar.sqlite").exists()
    assert not (result_dir / "Photos.sqlite").exists()


async def test_decrypt_job_decrypts_then_indexes(db, tmp_path, monkeypatch):
    """The background decrypt job marks DECRYPTED and runs indexing."""
    from sqlalchemy import func, select

    import worker.tasks as tasks
    from core.db.artifacts import Contact
    from core.db.models import Backup, DecryptionStatus
    from core.db.session import async_session_factory
    from fixtures import build_all

    decrypted = tmp_path / "decrypted"
    build_all(decrypted)

    class FakeOrchestrator:
        def __init__(self):
            pass

        def decrypt_backup(self, backup, password):
            return str(decrypted)

    monkeypatch.setattr(tasks, "DecryptOrchestrator", FakeOrchestrator)

    backup_id = "DEC-JOB-1"
    async with async_session_factory() as session:
        session.add(Backup(ios_identifier=backup_id, path=str(tmp_path / "src"), display_name="t", is_encrypted=True))
        await session.commit()

    await tasks._decrypt_backup_job(backup_id, "pw")

    async with async_session_factory() as session:
        backup = await session.scalar(select(Backup).where(Backup.ios_identifier == backup_id))
        contacts = await session.scalar(select(func.count()).select_from(Contact))

    assert backup.decryption_status == DecryptionStatus.DECRYPTED
    assert backup.decrypted_path == str(decrypted)
    assert contacts == 1  # indexing ran as part of the job


async def test_decrypt_job_marks_failed_on_error(db, tmp_path, monkeypatch):
    from sqlalchemy import select

    import worker.tasks as tasks
    from core.db.models import Backup, DecryptionStatus
    from core.db.session import async_session_factory
    from core.services import DecryptionError

    class FakeOrchestrator:
        def __init__(self):
            pass

        def decrypt_backup(self, backup, password):
            raise DecryptionError("Invalid password")

    monkeypatch.setattr(tasks, "DecryptOrchestrator", FakeOrchestrator)

    backup_id = "DEC-JOB-2"
    async with async_session_factory() as session:
        session.add(Backup(ios_identifier=backup_id, path=str(tmp_path), display_name="t", is_encrypted=True))
        await session.commit()

    await tasks._decrypt_backup_job(backup_id, "pw")

    async with async_session_factory() as session:
        backup = await session.scalar(select(Backup).where(Backup.ios_identifier == backup_id))

    assert backup.decryption_status == DecryptionStatus.FAILED
    assert "Invalid password" in (backup.decryption_error or "")
