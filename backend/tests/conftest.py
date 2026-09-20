"""Shared fixtures for API tests."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.database import set_db_path
from app.main import app


@pytest.fixture
def client(tmp_path):
    """Provide a TestClient wired to a temporary database.

    The app lifespan runs init_db() against the overridden path, so
    every test starts from a fresh migrated database.
    """
    set_db_path(tmp_path / "test.db")
    with TestClient(app) as c:
        yield c
    set_db_path(None)


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
