"""
PathoGuard-AI — Automated Database Backup Utility
Creates timestamped WAL-safe copies of the SQLite database or PostgreSQL dumps,
verifies backup integrity, and rotates historical backups past the retention threshold.
"""

import os
import shutil
import datetime
import sqlite3
import glob

BACKUP_RETENTION_DAYS = 30
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
DB_PATH = os.path.join(DATA_DIR, "pathoguard.db")


def create_sqlite_backup():
    """Generates an atomic, safe backup of SQLite using SQLite online backup API."""
    if not os.path.exists(DB_PATH):
        print(f"[!] Database file does not exist at {DB_PATH}")
        return False

    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"pathoguard_backup_{timestamp}.db"
    dest_path = os.path.join(BACKUP_DIR, backup_filename)

    print(f"[*] Starting atomic online backup of {DB_PATH} -> {dest_path}")
    source_conn = sqlite3.connect(DB_PATH)
    dest_conn = sqlite3.connect(dest_path)

    try:
        with dest_conn:
            source_conn.backup(dest_conn, pages=100)
        print(f"[+] Backup completed successfully ({os.path.getsize(dest_path) / 1024:.1f} KB)")
    finally:
        source_conn.close()
        dest_conn.close()

    # Integrity verification
    verify_conn = sqlite3.connect(dest_path)
    try:
        check = verify_conn.execute("PRAGMA quick_check;").fetchone()
        if check and check[0] == "ok":
            print("[+] Backup integrity verified (PRAGMA quick_check: ok)")
        else:
            print("[!] Backup integrity warning:", check)
    finally:
        verify_conn.close()

    # Retention rotation
    rotate_old_backups()
    return True


def rotate_old_backups():
    """Removes backups older than BACKUP_RETENTION_DAYS."""
    now = datetime.datetime.now()
    backups = glob.glob(os.path.join(BACKUP_DIR, "pathoguard_backup_*.db"))
    for b in backups:
        try:
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(b))
            if (now - mtime).days > BACKUP_RETENTION_DAYS:
                os.remove(b)
                print(f"[-] Pruned aged backup: {os.path.basename(b)}")
        except Exception as e:
            print(f"[!] Could not prune {b}: {e}")


if __name__ == "__main__":
    create_sqlite_backup()
