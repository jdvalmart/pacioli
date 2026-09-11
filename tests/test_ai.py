"""Tests for AI service."""

import pytest
from unittest.mock import patch, MagicMock
import json

from pacioli.services.ai import AIService, AIResponse
from pacioli.core.config import AIConfig


class TestAIService:
    """Test suite for AI service."""

    @pytest.fixture
    def ai_service(self):
        """Create AI service instance for testing."""
        service = AIService()
        service.config = AIConfig(
            model="test-model",
            url="http://localhost:11434/api/generate",
            timeout=5,
            temperature=0.7,
            max_tokens=100
        )
        return service

    def test_check_connection_success(self, ai_service):
        """Test successful connection check."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "response": "Hello!"
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            success, message = ai_service.check_connection()
            assert success is True
            assert "Connected" in message

    def test_check_connection_failure(self, ai_service):
        """Test failed connection check."""
        import urllib.error

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
            success, message = ai_service.check_connection()
            assert success is False
            assert "Cannot connect" in message

    def test_generate_description_success(self, ai_service):
        """Test successful description generation."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "response": "Grocery shopping at supermarket"
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            response = ai_service.generate_description("Food", 50.0)
            assert response.success is True
            assert response.text == "Grocery shopping at supermarket"

    def test_generate_description_timeout(self, ai_service):
        """Test description generation with timeout."""
        with patch("urllib.request.urlopen", side_effect=TimeoutError()):
            response = ai_service.generate_description("Food", 50.0)
            assert response.success is False
            assert "timeout" in response.error.lower()

    def test_analyze_spending_success(self, ai_service):
        """Test successful spending analysis."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "response": "Your spending shows a pattern of high food expenses."
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        transactions = [
            {"date": "2026-01-15", "category": "Food", "amount": 50.0},
            {"date": "2026-01-20", "category": "Food", "amount": 75.0},
        ]

        with patch("urllib.request.urlopen", return_value=mock_response):
            response = ai_service.analyze_spending(transactions, "January 2026")
            assert response.success is True
            assert "pattern" in response.text.lower()

    def test_ask_question_success(self, ai_service):
        """Test successful question answering."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "response": "Your total income this month is $5000."
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            response = ai_service.ask_question("What is my total income?")
            assert response.success is True
            assert "$5000" in response.text

    def test_ai_response_dataclass(self):
        """Test AIResponse dataclass."""
        response = AIResponse(success=True, text="Test response")
        assert response.success is True
        assert response.text == "Test response"
        assert response.error is None

        response_with_error = AIResponse(
            success=False,
            text="",
            error="Connection failed"
        )
        assert response_with_error.success is False
        assert response_with_error.error == "Connection failed"
