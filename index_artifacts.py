#!/usr/bin/env python3
import asyncio
from pathlib import Path
from core.config import get_settings
from core.db.session import async_session_factory
from worker.tasks import _index_backup_job
from sqlalchemy import select
from core.db.models import Backup

async def main():
    settings = get_settings()
    
    # Get the decrypted backup path from the database
    async with async_session_factory() as session:
        backup = await session.scalar(select(Backup).where(Backup.ios_identifier == "00008110-001A0D942EEA401E"))
        if backup and backup.decrypted_path:
            print(f"Found backup: {backup.ios_identifier}")
            print(f"Decrypted path: {backup.decrypted_path}")
            
            # Extract artifact databases
            decrypted_dir = Path(backup.decrypted_path)
            artifact_files = {}
            
            db_mappings = {
                "Photos.sqlite": "photos",
                "ChatStorage.sqlite": "whatsapp",
                "chat.db": "messages",
                "notes.sqlite": "notes",
                "Calendar.sqlite": "calendar",
                "AddressBook.sqlitedb": "contacts",
            }
            
            for db_name, artifact_type in db_mappings.items():
                db_path = decrypted_dir / db_name
                if db_path.exists():
                    artifact_files[artifact_type] = str(db_path)
                    print(f"Found {artifact_type}: {db_path}")
            
            # Run indexing
            print(f"Starting artifact indexing...")
            await _index_backup_job(backup.ios_identifier, backup.decrypted_path, artifact_files)
            print(f"Indexing complete!")
        else:
            print("Backup not found or not decrypted")

if __name__ == "__main__":
    asyncio.run(main())
