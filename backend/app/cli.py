"""Command-line maintenance tasks for Pacioli.

Usage::

    python -m app.cli backup [--keep N]

``backup`` writes today's snapshot of the SQLite database (once per day)
and rotates old ones. It is what the ``pacioli-backup`` systemd timer
runs, so a long-running server still gets a fresh backup every day.
"""

import argparse
import sys

from app.database import BACKUP_KEEP, auto_backup


def main(argv: list[str] | None = None) -> int:
    """Run a maintenance command and return the process exit code."""
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    backup = commands.add_parser("backup", help="snapshot the database and rotate old backups")
    backup.add_argument(
        "--keep", type=int, default=BACKUP_KEEP, help="backups to keep (default: %(default)s)"
    )
    args = parser.parse_args(argv)

    if args.command == "backup":
        created = auto_backup(keep=args.keep)
        print(created or "No backup needed (already done today, or no SQLite database).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
