"""Shared helpers for the backup and per-artifact route modules."""

from __future__ import annotations

import logging
import mimetypes
import shutil
from pathlib import Path

from fastapi import HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from core.config import get_settings
from core.db.models import Backup, DecryptionStatus
from core.services import BackupRegistry, SessionNotFoundError, UnlockManager

logger = logging.getLogger(__name__)
settings = get_settings()


async def get_decrypted_backup(backup_id: str, registry: BackupRegistry) -> Backup:
    """Fetch a backup, 404 if missing and 400 if it is not decrypted."""
    backup = await registry.get_backup(backup_id)
    if not backup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found.")
    if backup.decryption_status != DecryptionStatus.DECRYPTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Backup not decrypted.")
    return backup


async def get_backup_or_404(backup_id: str, session: AsyncSession) -> Backup:
    backup = await session.scalar(select(Backup).where(Backup.ios_identifier == backup_id))
    if not backup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found.")
    return backup


def get_filesystem_from_decrypted(backup: Backup):
    from core.backupfs import BackupFS

    decrypted_path = Path(backup.decrypted_path)
    if not decrypted_path.exists():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Decrypted backup data missing.")
    return BackupFS(handle=None, sandbox_root=settings.backup_paths.temp_path, backup_root=str(decrypted_path))


def ensure_session(backup_id: str, session_token: str, unlock_mgr: UnlockManager):
    try:
        session_backup_id, fs = unlock_mgr.get_filesystem(session_token)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    if session_backup_id != backup_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session does not match backup.")
    return fs


def resolve_filesystem(backup: Backup, backup_id: str, session_token: str | None, unlock_mgr: UnlockManager):
    """Use the live unlock session when available, else the on-disk decrypted data."""
    if session_token:
        return ensure_session(backup_id, session_token, unlock_mgr)
    return get_filesystem_from_decrypted(backup)


def _pick_candidate(entries, wanted: str) -> tuple[str, str] | None:
    for entry in entries:
        if entry.relative_path == wanted:
            return entry.domain, entry.relative_path
    for entry in entries:
        if entry.relative_path.endswith("/" + wanted) or entry.relative_path.endswith(wanted):
            return entry.domain, entry.relative_path
    return None


def extract_attachment(
    fs,
    relative_path: str,
    *,
    fallback_domains: list[str],
    strip_tilde: bool,
    session_present: bool,
    label: str,
) -> tuple[Path, Path]:
    """Resolve an attachment via the manifest (then fallback domains) and extract
    it. Returns (payload_path, sandbox_dir); the caller owns the sandbox cleanup.
    Raises HTTPException on failure."""
    requested_path = (relative_path or "").lstrip("/")
    if not requested_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="relative_path is required")
    if strip_tilde and requested_path.startswith("~"):
        requested_path = requested_path[1:].lstrip("/")

    resolved_domain: str | None = None
    resolved_relative_path: str | None = None

    try:
        candidates = fs.search_paths(requested_path, limit=50)
        picked = _pick_candidate(candidates, requested_path)
        if picked:
            resolved_domain, resolved_relative_path = picked
    except Exception as e:
        logger.warning(f"Manifest search failed for {label} attachment {requested_path}: {e}")

    if not resolved_domain or not resolved_relative_path:
        filename_only = Path(requested_path).name
        if filename_only:
            try:
                candidates = fs.search_paths(filename_only, limit=50)
                picked = _pick_candidate(candidates, filename_only)
                if picked:
                    resolved_domain, resolved_relative_path = picked
            except Exception as e:
                logger.warning(f"Filename manifest search failed for {label} attachment {filename_only}: {e}")

    if not resolved_domain or not resolved_relative_path:
        for domain in fallback_domains:
            try:
                fs.extract_to_temp(domain=domain, relative_path=requested_path)
                resolved_domain, resolved_relative_path = domain, requested_path
                break
            except Exception:
                continue
        else:
            logger.error(f"Failed to resolve {label} attachment in manifest: {requested_path}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment file not found.")

    try:
        return fs.extract_to_temp(domain=resolved_domain, relative_path=resolved_relative_path)
    except Exception as e:
        logger.error(
            f"Failed to extract {label} attachment domain={resolved_domain} relative_path={resolved_relative_path}: {e}"
        )
        if not session_present:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attachment not present in decrypted data. Unlock the backup and retry.",
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment file not found.")


def download_attachment_response(
    fs,
    relative_path: str,
    *,
    fallback_domains: list[str],
    strip_tilde: bool,
    session_present: bool,
    label: str,
) -> FileResponse:
    """Resolve an attachment and stream the original file."""
    payload_path, sandbox_dir = extract_attachment(
        fs,
        relative_path,
        fallback_domains=fallback_domains,
        strip_tilde=strip_tilde,
        session_present=session_present,
        label=label,
    )
    filename = payload_path.name or "attachment"
    background = BackgroundTask(shutil.rmtree, sandbox_dir, True)
    mime_type, _ = mimetypes.guess_type(filename)
    return FileResponse(
        path=str(payload_path),
        media_type=mime_type or "application/octet-stream",
        filename=filename,
        background=background,
    )


def extract_files(fs, decrypted_path: Path, attachment_rows, *, strip_tilde: bool) -> dict:
    """Copy a conversation's attachments out of the backup into the decrypted dir."""
    total = len(attachment_rows)
    file_ids = [file_id for _, file_id in attachment_rows if file_id]
    manifest_entries = fs.get_entries_by_file_ids(file_ids)

    extracted_files = 0
    extracted_bytes = 0
    skipped_exists = 0
    skipped_not_found = 0

    for idx, (relative_path, file_id) in enumerate(attachment_rows):
        if idx > 0 and idx % 500 == 0:
            logger.info(
                f"Extraction progress: {idx}/{total} processed, {extracted_files} extracted, "
                f"{skipped_exists} already exist"
            )

        manifest_entry = None
        if file_id:
            manifest_entry = manifest_entries.get(file_id)
        if not manifest_entry and relative_path:
            search_path = relative_path
            if strip_tilde and search_path.startswith("~"):
                search_path = search_path[1:].lstrip("/")
            try:
                manifest_candidates = fs.search_paths(search_path, limit=5)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(f"Manifest search failed for attachment path {relative_path}: {exc}")
                manifest_candidates = []
            if manifest_candidates:
                manifest_entry = manifest_candidates[0]

        if not manifest_entry:
            skipped_not_found += 1
            continue

        mf = manifest_entry
        target_path = decrypted_path / mf.domain / mf.relative_path
        if target_path.exists():
            skipped_exists += 1
            continue

        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            payload_path, sandbox_dir = fs.extract_to_temp(domain=mf.domain, relative_path=mf.relative_path)
            shutil.copy2(payload_path, target_path)
            shutil.rmtree(sandbox_dir, ignore_errors=True)
            extracted_files += 1
            if mf.size:
                extracted_bytes += int(mf.size)
        except Exception as e:
            logger.warning(f"Failed to extract {mf.domain}/{mf.relative_path}: {e}")
            continue

    logger.info(
        f"Extraction complete: {extracted_files} extracted, {skipped_exists} already existed, "
        f"{skipped_not_found} not found"
    )
    return {"extracted_files": extracted_files, "extracted_bytes": extracted_bytes}
