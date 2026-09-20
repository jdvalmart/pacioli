"""Shared fixtures for API tests."""

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
