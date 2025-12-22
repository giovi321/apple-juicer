from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from iphone_backup_decrypt.iphone_backup import EncryptedBackup

from core.backupfs.types import BackupStatus
from core.config import get_settings
from core.db.models import Backup, DecryptionStatus


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

            # Use save_manifest_file to save the decrypted Manifest.db
            handle.save_manifest_file(str(manifest_db_path))

            # Extract artifact database files with their correct domains
            artifact_databases = [
                ("AppDomainGroup-group.net.whatsapp.WhatsApp.shared", "ChatStorage.sqlite", "ChatStorage.sqlite"),
                ("HomeDomain", "Library/SMS/sms.db", "chat.db"),
                ("AppDomain-com.apple.mobilenotes", "Library/Notes/notes.sqlite", "notes.sqlite"),
                ("HomeDomain", "Library/Calendar/Calendar.sqlitedb", "Calendar.sqlite"),
                ("HomeDomain", "Library/AddressBook/AddressBook.sqlitedb", "AddressBook.sqlitedb"),
                ("CameraRollDomain", "Media/PhotoData/Photos.sqlite", "Photos.sqlite"),
            ]
            
            import logging
            logger = logging.getLogger(__name__)
            
            for entry in artifact_databases:
                try:
                    domain_like, relative_path, output_name = entry
                    db_path = decrypted_backup_dir / output_name
                    if db_path.exists():
                        db_path.unlink()
                    
                    logger.info(f"Extracting {output_name} from domain {domain_like}, path {relative_path}")
                    handle.extract_file(
                        relative_path=relative_path,
                        domain_like=domain_like,
                        output_filename=str(db_path)
                    )
                    
                    if db_path.exists():
                        logger.info(f"Successfully extracted {output_name}")
                    else:
                        logger.warning(f"File {output_name} was not created after extraction")
                        
                except Exception as e:
                    logger.warning(f"Failed to extract {output_name}: {type(e).__name__}: {e}")
                    # Continue with other files

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
