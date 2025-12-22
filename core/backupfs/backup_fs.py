from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Sequence

from iphone_backup_decrypt import utils as ib_utils
from iphone_backup_decrypt.iphone_backup import EncryptedBackup

from .types import ManifestFileEntry


class ManifestQueryError(RuntimeError):
    """Raised when manifest queries fail."""


class BackupFS:
    """Abstraction around iphone-backup-decrypt for manifest browsing and file extraction."""

    def __init__(self, handle: EncryptedBackup | None, sandbox_root: Path | str, backup_root: str | None = None):
        self.handle = handle
        self.backup_root = Path(backup_root) if backup_root else None
        self.sandbox_root = Path(sandbox_root).expanduser()
        self.sandbox_root.mkdir(parents=True, exist_ok=True)

    def list_domains(self) -> List[str]:
        def _query(cursor: sqlite3.Cursor) -> List[str]:
            cursor.execute("SELECT DISTINCT domain FROM Files WHERE flags=1 ORDER BY domain;")
            return [row[0] for row in cursor.fetchall()]

        return self._with_manifest_cursor(_query)

    def list_files(
        self,
        *,
        domain: str | None = None,
        path_like: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[ManifestFileEntry]:
        def _query(cursor: sqlite3.Cursor) -> List[ManifestFileEntry]:
            clauses = ["flags=1"]
            params: list[str] = []
            if domain:
                clauses.append("domain = ?")
                params.append(domain)
            if path_like:
                clauses.append("relativePath LIKE ?")
                params.append(path_like)
            where_sql = " AND ".join(clauses)
            sql = f"""
                SELECT fileID, domain, relativePath, flags, file
                FROM Files
                WHERE {where_sql}
                ORDER BY domain, relativePath
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [self._row_to_entry(row) for row in rows]

        return self._with_manifest_cursor(_query)

    def search_paths(self, query: str, limit: int = 200) -> List[ManifestFileEntry]:
        pattern = f"%{query}%"

        def _query(cursor: sqlite3.Cursor) -> List[ManifestFileEntry]:
            cursor.execute(
                """
                SELECT fileID, domain, relativePath, flags, file
                FROM Files
                WHERE flags=1 AND (relativePath LIKE ? OR domain LIKE ?)
                ORDER BY relativePath
                LIMIT ?
                """,
                (pattern, pattern, limit),
            )
            rows = cursor.fetchall()
            return [self._row_to_entry(row) for row in rows]

        return self._with_manifest_cursor(_query)

    def extract_to_temp(self, *, domain: str, relative_path: str) -> tuple[Path, Path]:
        """Extract the requested file into a sandbox directory."""
        sandbox_dir = Path(tempfile.mkdtemp(prefix="iosfs_", dir=self.sandbox_root))
        filename = Path(relative_path).name or "payload.bin"
        payload_path = sandbox_dir / filename
        payload_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.handle:
            self.handle.extract_file(
                relative_path=relative_path,
                domain_like=domain,
                output_filename=str(payload_path),
            )
        elif self.backup_root:
            file_hash_path = self.backup_root / domain / relative_path
            if not file_hash_path.exists():
                raise FileNotFoundError(f"File not found: {domain}/{relative_path}")
            shutil.copy2(file_hash_path, payload_path)
        else:
            raise RuntimeError("No backup handle or backup root provided")
        
        return payload_path, sandbox_dir

    @contextmanager
    def stream_file(self, *, domain: str, relative_path: str):
        """Context manager yielding a readable file object and cleaning up afterward."""
        temp_path, sandbox_dir = self.extract_to_temp(domain=domain, relative_path=relative_path)
        try:
            with temp_path.open("rb") as fp:
                yield fp
        finally:
            shutil.rmtree(sandbox_dir, ignore_errors=True)

    def get_entry_by_file_id(self, file_id: str) -> ManifestFileEntry | None:
        def _query(cursor: sqlite3.Cursor) -> ManifestFileEntry | None:
            cursor.execute(
                """
                SELECT fileID, domain, relativePath, flags, file
                FROM Files
                WHERE fileID = ?
                LIMIT 1
                """,
                (file_id,),
            )
            row = cursor.fetchone()
            return self._row_to_entry(row) if row else None

        return self._with_manifest_cursor(_query)

    @contextmanager
    def stream_file_by_id(self, file_id: str):
        entry = self.get_entry_by_file_id(file_id)
        if not entry:
            raise FileNotFoundError(file_id)
        with self.stream_file(domain=entry.domain, relative_path=entry.relative_path) as fp:
            yield entry, fp

    def _row_to_entry(self, row: Sequence) -> ManifestFileEntry:
        file_id, domain, relative_path, flags, file_blob = row
        size = None
        mtime = None
        if file_blob:
            try:
                plist = ib_utils.FilePlist(file_blob)
                size = plist.filesize
                mtime = plist.mtime
            except Exception:
                pass
        return ManifestFileEntry(
            file_id=file_id,
            domain=domain,
            relative_path=relative_path,
            flags=flags,
            size=size,
            mtime=mtime,
        )

    def _with_manifest_cursor(self, fn):
        try:
            if self.handle:
                with self.handle.manifest_db_cursor() as cursor:
                    return fn(cursor)
            elif self.backup_root:
                manifest_db = self.backup_root / "Manifest.db"
                if not manifest_db.exists():
                    raise ManifestQueryError(f"Manifest.db not found at {manifest_db}")
                conn = sqlite3.connect(str(manifest_db))
                conn.row_factory = sqlite3.Row
                try:
                    return fn(conn.cursor())
                finally:
                    conn.close()
            else:
                raise ManifestQueryError("No backup handle or backup root provided")
        except sqlite3.Error as exc:
            raise ManifestQueryError(str(exc)) from exc
