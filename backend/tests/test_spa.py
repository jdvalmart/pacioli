"""Tests for the SPA serving in production mode."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def spa_dist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a minimal built frontend and point the app at it."""
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>Pacioli</html>")
    (dist / "assets" / "app.js").write_text("console.log('pacioli')")
    monkeypatch.setenv("PACIOLI_FRONTEND_DIST", str(dist))
    return dist


class TestSpaServing:
    """Tests for the frontend static serving."""

    def test_root_serves_index(self, client: TestClient, spa_dist: Path) -> None:
        response = client.get("/")
        assert response.status_code == 200
        assert "Pacioli" in response.text

    def test_client_route_falls_back_to_index(self, client: TestClient, spa_dist: Path) -> None:
        response = client.get("/transactions")
        assert response.status_code == 200
        assert "Pacioli" in response.text

    def test_static_asset_served(self, client: TestClient, spa_dist: Path) -> None:
        response = client.get("/assets/app.js")
        assert response.status_code == 200
        assert "console.log" in response.text

    def test_api_routes_take_precedence(self, client: TestClient, spa_dist: Path) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_path_traversal_blocked(self, client: TestClient, spa_dist: Path) -> None:
        secret = spa_dist.parent / "secret.txt"
        secret.write_text("top secret")
        response = client.get("/../secret.txt")
        assert "top secret" not in response.text

    def test_404_when_frontend_not_built(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PACIOLI_FRONTEND_DIST", "/nonexistent/dist")
        response = client.get("/")
        assert response.status_code == 404
