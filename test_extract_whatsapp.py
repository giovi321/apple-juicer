#!/usr/bin/env python3
"""Test script to extract WhatsApp ChatStorage.sqlite"""
import sys
from pathlib import Path
from iphone_backup_decrypt.iphone_backup import EncryptedBackup

if len(sys.argv) < 2:
    print("Usage: python test_extract_whatsapp.py <password>")
    sys.exit(1)

password = sys.argv[1]
backup_path = '/data/backups/00008110-001A0D942EEA401E'
output_path = '/data/decrypted_backups/00008110-001A0D942EEA401E/ChatStorage.sqlite'

try:
    print(f"Opening backup: {backup_path}")
    handle = EncryptedBackup(backup_directory=backup_path, passphrase=password)
    
    print("Testing decryption...")
    handle.test_decryption()
    print("✓ Decryption successful")
    
    print(f"\nExtracting ChatStorage.sqlite...")
    handle.extract_file(
        relative_path='ChatStorage.sqlite',
        domain_like='group.net.whatsapp.WhatsApp.shared',
        output_filename=output_path
    )
    
    if Path(output_path).exists():
        size_mb = Path(output_path).stat().st_size / (1024*1024)
        print(f"✓ Successfully extracted ChatStorage.sqlite ({size_mb:.2f} MB)")
    else:
        print("✗ File was not created")
        
except ValueError as e:
    print(f"✗ Invalid password: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
