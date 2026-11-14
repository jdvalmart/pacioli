"""Connections, SQL dialect adaptation (SQLite/Postgres), paths and money helpers."""

import os
import sqlite3
from contextlib import contextmanager
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.errors import IntegrityViolation


def _default_data_dir() -> str:
    override = os.environ.get("PACIOLI_DATA_DIR")
    if override:
        return override
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share"
    )
    return os.path.join(base, "pacioli")


DEFAULT_DB_PATH = os.path.join(_default_data_dir(), "pacioli.db")


_db_path: str | None = None


def _is_postgres() -> bool:
    # Tests isolate on temp SQLite files via set_db_path(); never use Postgres there.
    if _db_path is not None:
        return False
    return os.getenv("DATABASE_URL", "").startswith("postgres")


def _has_column(conn, table: str, column: str) -> bool:  # type: ignore[no-untyped-def]
    """Check whether a column exists (SQLite and Postgres)."""
    cursor = conn.cursor()
    if _is_postgres():
        cursor.execute(
            _adapt_sql(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_name = ? AND column_name = ?"
            ),
            (table, column),
        )
    else:
        cursor.execute(f"SELECT COUNT(*) FROM pragma_table_info('{table}') WHERE name = '{column}'")
    row = cursor.fetchone()
    if isinstance(row, dict):
        return int(next(iter(row.values()))) > 0
    return int(row[0]) > 0


def _adapt_sql(sql: str) -> str:
    return sql.replace("?", "%s") if _is_postgres() else sql


def _ddl(sql: str) -> str:
    if _is_postgres():
        sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        # Money columns hold cents: a 39M CDT is 3.9B cents, over int4 range.
        for col in (
            "amount_cents",
            "target_cents",
            "current_value_cents",
            "dividends_cents",
            "opening_cents",
            "scheduled_amount_cents",
            "starting_cents",
            "limit_cents",
            "total_cents",
            "balance_cents",
            "installment_cents",
        ):
            sql = sql.replace(f"{col} INTEGER", f"{col} BIGINT")
        return sql
    return sql


def _get_version(conn) -> int:  # type: ignore[no-untyped-def]
    if _is_postgres():
        # No blanket except: a connection or permission error must abort
        # startup, not be mistaken for an empty database (version 0) and
        # trigger schema creation and seeding.
        conn.execute(
            "CREATE TABLE IF NOT EXISTS pacioli_schema_version "
            "(id INT PRIMARY KEY, version INT NOT NULL)"
        )
        row = conn.execute("SELECT version FROM pacioli_schema_version WHERE id = 1").fetchone()
        return 0 if row is None else int(row["version"])
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def _set_version(conn, version: int) -> None:  # type: ignore[no-untyped-def]
    if _is_postgres():
        conn.execute(
            _adapt_sql(
                "INSERT INTO pacioli_schema_version (id, version) VALUES (1, ?) ON CONFLICT (id) DO UPDATE SET version = ?"
            ),
            (version, version),
        )
    else:
        conn.execute(f"PRAGMA user_version = {version}")


def _insert_get_id(cursor, sql: str, params) -> int:  # type: ignore[no-untyped-def]
    if _is_postgres():
        sql = sql.rstrip().rstrip(";") + " RETURNING id"
        cursor.execute(_adapt_sql(sql), params)
        row = cursor.fetchone()
        if isinstance(row, dict):
            return int(row["id"])
        return int(row[0])
    cursor.execute(sql, params)
    return int(cursor.lastrowid)


def set_db_path(path: str | Path | None) -> None:
    """Override the database location.

    Pass None to restore the default XDG path. Tests use this to
    isolate each suite on a temporary database.

    Args:
        path: New database path, or None for the default.
    """
    global _db_path
    _db_path = str(path) if path is not None else None


def get_db_path() -> str:
    """Return the active database path, creating its directory."""
    if _db_path is not None:
        return _db_path
    os.makedirs(os.path.dirname(DEFAULT_DB_PATH), exist_ok=True)
    return DEFAULT_DB_PATH


def get_backup_dir() -> str:
    """Return the backups directory, creating it if needed."""
    d = os.path.join(os.path.dirname(os.path.abspath(get_db_path())), "backups")
    os.makedirs(d, exist_ok=True)
    return d


class _PGCursorWrapper:  # type: ignore[no-redef]
    def __init__(self, cur: Any) -> None:  # type: ignore[no-untyped-def]
        self._cur = cur

    def execute(self, sql: str, params: Any = ()) -> Any:  # type: ignore[no-untyped-def]
        return self._cur.execute(_adapt_sql(sql), params)

    def __getattr__(self, name: str) -> Any:  # type: ignore[no-untyped-def]
        return getattr(self._cur, name)


class _PGConnWrapper:  # type: ignore[no-redef]
    def __init__(self, conn: Any) -> None:  # type: ignore[no-untyped-def]
        self._conn = conn

    def cursor(self, *args: Any, **kwargs: Any) -> Any:  # type: ignore[no-untyped-def]
        return _PGCursorWrapper(self._conn.cursor(*args, **kwargs))

    def execute(self, sql: str, params: Any = ()) -> Any:  # type: ignore[no-untyped-def]
        return self._conn.execute(_adapt_sql(sql), params)

    def commit(self) -> None:
        self._conn.commit()  # type: ignore[no-untyped-call]

    def close(self) -> None:
        self._conn.close()  # type: ignore[no-untyped-call]

    def __getattr__(self, name: str) -> Any:  # type: ignore[no-untyped-def]
        return getattr(self._conn, name)


# Constraint errors of every supported driver, normalised to IntegrityViolation.
_DRIVER_INTEGRITY_ERRORS: tuple[type[Exception], ...] = (
    sqlite3.IntegrityError,
    psycopg.IntegrityError,
)


@contextmanager
def get_connection():  # type: ignore[no-untyped-def]
    """Yield a configured connection (SQLite or Postgres via DATABASE_URL).

    Constraint violations from either driver are re-raised as
    ``IntegrityViolation`` so callers stay driver-agnostic.
    """
    if _is_postgres():
        database_url = os.getenv("DATABASE_URL")
        assert database_url is not None
        conn: Any = psycopg.connect(database_url, row_factory=dict_row)
        wrapped = _PGConnWrapper(conn)
        try:
            yield wrapped  # type: ignore[misc]
            wrapped.commit()
        except _DRIVER_INTEGRITY_ERRORS as exc:
            raise IntegrityViolation(str(exc)) from exc
        finally:
            wrapped.close()
    else:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        except _DRIVER_INTEGRITY_ERRORS as exc:
            raise IntegrityViolation(str(exc)) from exc
        finally:
            conn.close()


def _to_cents(amount: Decimal | float | int | str) -> int:
    return int((Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _to_dec(cents: int | None) -> Decimal:
    return (Decimal(cents or 0) / 100).quantize(Decimal("0.01"))


def _q(value: Decimal) -> Decimal:
    """Round a money value to two decimals."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
