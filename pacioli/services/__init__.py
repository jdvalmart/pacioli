"""Services module for external integrations."""

from pacioli.services.ai import (
    AIService,
    AIResponse,
    ai_service,
    detect_correction,
    extract_correction_topic,
)

__all__ = [
    "AIService",
    "AIResponse",
    "ai_service",
    "detect_correction",
    "extract_correction_topic",
]
