"""AI service integration with Ollama.

Provides AI-powered features for financial analysis and assistance.
"""

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from app.config import config_manager
from app.logging_config import logger

# Correction detection keywords
CORRECTION_KEYWORDS = [
    "no",
    "incorrecto",
    "mal",
    "error",
    "equivocado",
    "cambiar",
    "corregir",
    "mejor",
    "otra vez",
]

# Topic extraction keywords
TOPIC_KEYWORDS = {
    "gasto": "expenses",
    "ingreso": "income",
    "presupuesto": "budget",
    "ahorro": "savings",
    "categoría": "categories",
    "reporte": "reports",
}


def detect_correction(message: str) -> bool:
    """Detect if a user message is a correction.

    Args:
        message: User message.

    Returns:
        True if the message appears to be a correction.
    """
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in CORRECTION_KEYWORDS)


def extract_correction_topic(message: str) -> str:
    """Extract the topic from a correction message.

    Args:
        message: User message.

    Returns:
        Extracted topic or "general".
    """
    message_lower = message.lower()
    for keyword, topic in TOPIC_KEYWORDS.items():
        if keyword in message_lower:
            return topic
    return "general"


@dataclass
class AIResponse:
    """Response from the AI service."""

    success: bool
    text: str
    error: str | None = None


class AIService:
    """Service for AI interactions with Ollama."""

    def __init__(self) -> None:
        """Initialize the service with the current configuration."""
        self.config = config_manager.get_ai_config()

    def reload_config(self) -> None:
        """Refresh the configuration from disk (after user changes)."""
        self.config = config_manager.get_ai_config()

    def _make_request(self, prompt: str, system: str = "") -> AIResponse:
        """Make a request to the Ollama API.

        Args:
            prompt: User prompt.
            system: System prompt (optional).

        Returns:
            AIResponse with success status and text/error.
        """
        url = self.config.url
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "think": self.config.think,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                text = result.get("response", "").strip()

                if not text:
                    return AIResponse(success=False, text="", error="Empty response from AI")

                return AIResponse(success=True, text=text)

        except urllib.error.URLError:
            logger.exception("AI service connection error")
            return AIResponse(
                success=False,
                text="",
                error=f"Cannot connect to Ollama at {url}. Is it running?",
            )
        except urllib.error.HTTPError as e:
            logger.error("AI service HTTP error: %s %s", e.code, e.reason)
            return AIResponse(
                success=False,
                text="",
                error=f"HTTP error {e.code}: {e.reason}",
            )
        except TimeoutError:
            logger.error("AI service timeout after %ss", self.config.timeout)
            return AIResponse(
                success=False,
                text="",
                error=f"Request timeout after {self.config.timeout} seconds",
            )
        except json.JSONDecodeError:
            logger.exception("AI service returned invalid JSON")
            return AIResponse(
                success=False,
                text="",
                error="Invalid response format from AI service",
            )
        except Exception:  # noqa: BLE001 — the service must never crash the API
            logger.exception("AI service unexpected error")
            return AIResponse(success=False, text="", error="Unexpected error from AI service")

    def check_connection(self) -> tuple[bool, str]:
        """Check whether the AI service is reachable.

        Returns:
            Tuple of (success, message).
        """
        response = self._make_request("Hello", "You are a helpful assistant.")

        if response.success:
            return True, f"Connected to {self.config.model}"
        return False, response.error or "Unknown error"

    def generate_description(self, category: str, amount: float, context: str = "") -> AIResponse:
        """Generate a transaction description.

        Args:
            category: Transaction category.
            amount: Transaction amount.
            context: Additional context (optional).

        Returns:
            AIResponse with the generated description.
        """
        system = (
            "You are a financial assistant. Generate a brief, clear description "
            "for a transaction. Respond only with the description, nothing else. "
            "Keep it under 10 words."
        )

        prompt = f"Category: {category}\nAmount: ${amount:.2f}"
        if context:
            prompt += f"\nContext: {context}"

        prompt += "\n\nGenerate a description:"

        return self._make_request(prompt, system)

    def analyze_spending(self, transactions: list[dict], period: str) -> AIResponse:
        """Analyze spending patterns.

        Args:
            transactions: List of transaction dicts.
            period: Time period (e.g. "September 2026").

        Returns:
            AIResponse with the analysis.
        """
        system = (
            "You are a financial analyst. Analyze the provided transactions "
            "and give actionable insights. Be concise and practical. "
            "Focus on patterns, unusual spending, and suggestions."
        )

        tx_lines = []
        for tx in transactions[:20]:  # Cap input to avoid token limits
            tx_lines.append(f"- {tx['date']}: {tx['category']} - ${tx['amount']:.2f}")

        transactions_text = "\n".join(tx_lines)

        prompt = (
            f"Period: {period}\n\n"
            f"Transactions:\n{transactions_text}\n\n"
            "Analyze spending patterns and provide insights:"
        )

        return self._make_request(prompt, system)

    def ask_question(self, question: str, context: str = "") -> AIResponse:
        """Ask a question to the AI assistant.

        Args:
            question: User question.
            context: Financial context (optional).

        Returns:
            AIResponse with the answer.
        """
        system = (
            "You are a helpful financial assistant for a personal budget app. "
            "Answer questions clearly and concisely. If you don't know, say so."
        )

        prompt = question
        if context:
            prompt = f"Context:\n{context}\n\nQuestion: {question}"

        return self._make_request(prompt, system)


ai_service = AIService()
