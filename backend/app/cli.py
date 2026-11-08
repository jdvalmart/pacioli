"""Command-line maintenance tasks for Pacioli.

Usage::

    python -m app.cli backup [--keep N]
    python -m app.cli openapi [--output FILE]

``backup`` writes today's snapshot of the SQLite database (once per day)
and rotates old ones. It is what the ``pacioli-backup`` systemd timer
runs, so a long-running server still gets a fresh backup every day.

``openapi`` prints the API contract (OpenAPI JSON) without starting the
server; the frontend generates its TypeScript types from it.
"""

import argparse
import json
import sys
from pathlib import Path

from app.db.backup import BACKUP_KEEP, auto_backup


def main(argv: list[str] | None = None) -> int:
    """Run a maintenance command and return the process exit code."""
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    backup = commands.add_parser("backup", help="snapshot the database and rotate old backups")
    backup.add_argument(
        "--keep", type=int, default=BACKUP_KEEP, help="backups to keep (default: %(default)s)"
    )
    openapi = commands.add_parser("openapi", help="print the OpenAPI contract as JSON")
    openapi.add_argument("--output", type=Path, help="write to this file instead of stdout")
    args = parser.parse_args(argv)

    if args.command == "backup":
        created = auto_backup(keep=args.keep)
        print(created or "No backup needed (already done today, or no SQLite database).")
    elif args.command == "openapi":
        from app.main import app  # deferred: only this command needs the web app

        spec = json.dumps(app.openapi(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        if args.output:
            args.output.write_text(spec, encoding="utf-8")
        else:
            sys.stdout.write(spec)
    return 0


if __name__ == "__main__":
    sys.exit(main())
