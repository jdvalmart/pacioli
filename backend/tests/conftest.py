"""Shared fixtures for API tests.

The database backend is chosen with ``PACIOLI_TEST_DATABASE_URL``:

- unset (default): every test runs on a fresh temporary SQLite file;
- ``postgresql://...``: every test runs on that database after its
  ``public`` schema is dropped and recreated. Point it at a throwaway
  database: its contents are destroyed.

Legacy-migration tests pin their own SQLite file with ``set_db_path``,
so they keep exercising SQLite on either run.
"""

import os
from collections.abc import Callable, Iterator
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.database import set_db_path
from app.main import app

TEST_PG_URL = os.environ.get("PACIOLI_TEST_DATABASE_URL", "")
ON_POSTGRES = TEST_PG_URL.startswith("postgres")


def _reset_postgres_schema(url: str) -> None:
    import psycopg

    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")


@pytest.fixture
def test_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Point the data layer at an empty database (not yet migrated)."""
    if ON_POSTGRES:
        _reset_postgres_schema(TEST_PG_URL)
        monkeypatch.setenv("DATABASE_URL", TEST_PG_URL)
        set_db_path(None)
    else:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        set_db_path(tmp_path / "test.db")
    yield
    set_db_path(None)


@pytest.fixture
def client(test_database: None) -> Iterator[TestClient]:
    """Provide a TestClient wired to a fresh database.

    The app lifespan runs init_db(), so every test starts from a
    freshly migrated and seeded database.
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture
def freeze_today(monkeypatch: pytest.MonkeyPatch) -> Callable[[date], None]:
    """Return a setter that pins ``app.clock.today()`` to a fixed date.

    Card cycles and savings maturity depend on the current date, so any
    test asserting on them must freeze it or it turns into a time bomb.
    """

    def _freeze(day: date) -> None:
        monkeypatch.setattr("app.clock.today", lambda: day)

    return _freeze


@pytest.fixture(autouse=True)
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Isolate the global config manager so tests never touch the real config.

    config_manager is a module-level singleton; this fixture repoints
    it to a temp directory and resets it to defaults before each test.
    """
    from app.config import AppConfig, config_manager

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_manager.config_dir = tmp_path / "pacioli"
    config_manager.config_file = config_manager.config_dir / "config.json"
    config_manager.config = AppConfig()
    yield
