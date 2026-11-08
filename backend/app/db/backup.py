"""SQLite snapshots with rotation."""

import os
import sqlite3
from contextlib import suppress

from app import clock
from app.db.connection import _is_postgres, get_backup_dir, get_db_path

BACKUP_KEEP = 10


def backup_database(dest_path: str) -> None:
    """Hot-copy the database safely using the sqlite3 backup API.

    Unlike shutil.copy, this is consistent even with WAL active or
    concurrent writes.
    """
    src = sqlite3.connect(get_db_path())
    try:
        dst = sqlite3.connect(dest_path)
        try:
            with dst:
                src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def auto_backup(keep: int = BACKUP_KEEP) -> str | None:
    """Run the daily automatic backup with rotation.

    Returns:
        The path of the created backup, or None if one already exists.
    """
    if _is_postgres():
        return None
    if not os.path.exists(get_db_path()):
        return None
    today = clock.today()
    dest = os.path.join(get_backup_dir(), f"pacioli_{today.isoformat()}.db")
    created = None
    if not os.path.exists(dest):
        backup_database(dest)
        created = dest
    if keep > 0:
        backups = sorted(
            f
            for f in os.listdir(get_backup_dir())
            if f.startswith("pacioli_") and f.endswith(".db")
        )
        for old in backups[: max(0, len(backups) - keep)]:
            with suppress(OSError):
                os.remove(os.path.join(get_backup_dir(), old))
    return created
