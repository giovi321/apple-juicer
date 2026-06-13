from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Optional

from iphone_backup_decrypt.iphone_backup import EncryptedBackup

from core.artifacts import decrypt_targets
from core.config import get_settings
from core.db.models import Backup

logger = logging.getLogger(__name__)


class DecryptionError(Exception):
    """Raised when backup decryption fails."""


class DecryptOrchestrator:
    """Orchestrate backup decryption and storage management."""

    def __init__(self, decrypted_base_path: Optional[str] = None):
        settings = get_settings()
        self.decrypted_base_path = Path(
            decrypted_base_path or settings.backup_paths.decrypted_path
        )
        self.decrypted_base_path.mkdir(parents=True, exist_ok=True)

    def decrypt_backup(self, backup: Backup, password: str) -> str:
        """
        Decrypt a backup and store decrypted data.

        Args:
            backup: Backup model instance
            password: Password to decrypt the backup

        Returns:
            Path to decrypted backup directory

        Raises:
            DecryptionError: If decryption fails
        """
        backup_path = Path(backup.path)
        if not backup_path.exists():
            raise DecryptionError(f"Backup path missing: {backup.path}")

        decrypted_backup_dir = self.decrypted_base_path / backup.ios_identifier
        decrypted_backup_dir.mkdir(parents=True, exist_ok=True)

        try:
            handle = EncryptedBackup(
                backup_directory=str(backup_path), passphrase=password
            )
            handle.test_decryption()

            manifest_db_path = decrypted_backup_dir / "Manifest.db"
            if manifest_db_path.exists():
                manifest_db_path.unlink()

            # Save the decrypted Manifest.db. Without it the backup is not
            # browsable, so a missing manifest is a hard failure rather than a
            # "decrypted" backup that silently yields nothing.
            handle.save_manifest_file(str(manifest_db_path))
            if not manifest_db_path.exists():
                raise DecryptionError("Decryption did not produce a Manifest database.")

            # Extract artifact database files with their correct domains.
            # Individual artifact DBs are optional (a backup may simply not
            # contain WhatsApp, Notes, etc.), so missing ones are recorded but
            # do not fail decryption. The domain/path/filename triples come from
            # the artifact registry so they cannot drift from the indexer.
            artifact_databases = decrypt_targets()

            extracted: list[str] = []
            missing: list[str] = []
            for domain_like, relative_path, output_name in artifact_databases:
                db_path = decrypted_backup_dir / output_name
                if db_path.exists():
                    db_path.unlink()
                try:
                    handle.extract_file(
                        relative_path=relative_path,
                        domain_like=domain_like,
                        output_filename=str(db_path),
                    )
                except Exception as exc:
                    logger.warning("Failed to extract %s: %s: %s", output_name, type(exc).__name__, exc)
                if db_path.exists():
                    extracted.append(output_name)
                else:
                    missing.append(output_name)

            logger.info(
                "Decrypted backup %s: extracted artifact DBs %s; absent %s",
                backup.ios_identifier,
                extracted or ["none"],
                missing or ["none"],
            )

            return str(decrypted_backup_dir)

        except ValueError as exc:
            raise DecryptionError("Invalid password") from exc
        except Exception as exc:
            raise DecryptionError(str(exc)) from exc

    def clear_decrypted_backup(self, backup: Backup) -> None:
        """
        Clear decrypted backup data.

        Args:
            backup: Backup model instance
        """
        if backup.decrypted_path:
            decrypted_path = Path(backup.decrypted_path)
            if decrypted_path.exists():
                shutil.rmtree(decrypted_path, ignore_errors=True)

    def get_decrypted_path(self, backup: Backup) -> Optional[Path]:
        """
        Get path to decrypted backup if it exists.

        Args:
            backup: Backup model instance

        Returns:
            Path to decrypted backup or None if not decrypted
        """
        if backup.decrypted_path:
            path = Path(backup.decrypted_path)
            if path.exists():
                return path
        return None
