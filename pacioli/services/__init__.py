"""Módulo services: servicios externos e integraciones.

Contiene la integración con IA (Ollama) y otros servicios externos.
"""

from .ai import (
    MODEL,
    OLLAMA_URL,
    ask_budget_question,
    analyze_spending,
    detect_correction,
    extract_correction_topic,
    generate_description,
)

__all__ = [
    'MODEL',
    'OLLAMA_URL',
    'ask_budget_question',
    'analyze_spending',
    'detect_correction',
    'extract_correction_topic',
    'generate_description',
]
