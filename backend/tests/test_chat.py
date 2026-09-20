"""Integration tests for the chat and AI configuration endpoints."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.services.ai import AIResponse


class TestChat:
    """Tests for the chat endpoints."""

    def test_history_starts_empty(self, client: TestClient) -> None:
        response = client.get("/api/chat?month=9&year=2026")
        assert response.status_code == 200
        assert response.json() == []

    def test_ask_persists_conversation(self, client: TestClient) -> None:
        with patch(
            "app.routers.chat.ai_service.ask_question",
            return_value=AIResponse(success=True, text="Tu gasto más alto es Vivienda."),
        ):
            response = client.post(
                "/api/chat", json={"question": "¿En qué gasto más?", "month": 9, "year": 2026}
            )

        assert response.status_code == 200
        assert response.json() == {"answer": "Tu gasto más alto es Vivienda.", "error": None}

        history = client.get("/api/chat?month=9&year=2026").json()
        assert [m["role"] for m in history] == ["user", "ai"]
        assert history[0]["message"] == "¿En qué gasto más?"

    def test_ask_saves_question_when_ai_fails(self, client: TestClient) -> None:
        with patch(
            "app.routers.chat.ai_service.ask_question",
            return_value=AIResponse(success=False, text="", error="Cannot connect to Ollama"),
        ):
            response = client.post("/api/chat", json={"question": "Hola", "month": 9, "year": 2026})

        assert response.status_code == 200
        assert response.json()["answer"] == ""
        assert "Cannot connect" in response.json()["error"]

        history = client.get("/api/chat?month=9&year=2026").json()
        assert [m["role"] for m in history] == ["user"]

    def test_clear_history(self, client: TestClient) -> None:
        with patch(
            "app.routers.chat.ai_service.ask_question",
            return_value=AIResponse(success=True, text="Ok."),
        ):
            client.post("/api/chat", json={"question": "Hola", "month": 9, "year": 2026})

        response = client.delete("/api/chat?month=9&year=2026")
        assert response.status_code == 200
        assert client.get("/api/chat?month=9&year=2026").json() == []

    def test_history_is_isolated_per_month(self, client: TestClient) -> None:
        with patch(
            "app.routers.chat.ai_service.ask_question",
            return_value=AIResponse(success=True, text="Ok."),
        ):
            client.post("/api/chat", json={"question": "Septiembre", "month": 9, "year": 2026})

        assert client.get("/api/chat?month=10&year=2026").json() == []
        assert len(client.get("/api/chat?month=9&year=2026").json()) == 2


class TestAIConfig:
    """Tests for the AI configuration endpoints."""

    def test_get_default_config(self, client: TestClient) -> None:
        response = client.get("/api/ai/config")
        assert response.status_code == 200
        config = response.json()
        assert config["model"] == "qwen2.5:3b"
        assert config["timeout"] == 120
        assert config["think"] == "low"

    def test_update_config_persists(self, client: TestClient) -> None:
        payload = {
            "model": "qwen3:8b",
            "url": "http://localhost:11434/api/generate",
            "timeout": 60,
            "temperature": 0.3,
            "max_tokens": 512,
        }
        response = client.put("/api/ai/config", json=payload)
        assert response.status_code == 200

        config = client.get("/api/ai/config").json()
        assert config["model"] == "qwen3:8b"
        assert config["temperature"] == 0.3
        assert config["max_tokens"] == 512

    def test_test_connection_success(self, client: TestClient) -> None:
        with patch(
            "app.routers.ai.ai_service.check_connection",
            return_value=(True, "Connected to test-model"),
        ):
            response = client.post("/api/ai/test-connection")

        assert response.status_code == 200
        assert response.json() == {"success": True, "message": "Connected to test-model"}

    def test_test_connection_failure(self, client: TestClient) -> None:
        with patch(
            "app.routers.ai.ai_service.check_connection",
            return_value=(False, "Cannot connect to Ollama"),
        ):
            response = client.post("/api/ai/test-connection")

        assert response.json() == {"success": False, "message": "Cannot connect to Ollama"}
