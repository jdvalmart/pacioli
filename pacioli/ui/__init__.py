"""Módulo ui: interfaz gráfica de usuario.

Contiene la aplicación principal, tema visual, gráficos y todas las vistas.
"""

from .app import BudgetApp, main
from .theme import (
    ACCENT,
    BG,
    BORDER,
    CARD,
    CARD_HOVER,
    FONT,
    GREEN,
    ORANGE,
    PURPLE,
    RED,
    SURFACE,
    TEAL,
    TEXT,
    TEXT_DIM,
    TEXT_SEC,
    apply_theme,
    btn_danger,
    btn_primary,
    card,
    font,
    styled_tabs,
)

__all__ = [
    'ACCENT',
    'BG',
    'BORDER',
    'BudgetApp',
    'CARD',
    'CARD_HOVER',
    'FONT',
    'GREEN',
    'ORANGE',
    'PURPLE',
    'RED',
    'SURFACE',
    'TEAL',
    'TEXT',
    'TEXT_DIM',
    'TEXT_SEC',
    'apply_theme',
    'btn_danger',
    'btn_primary',
    'card',
    'font',
    'main',
    'styled_tabs',
]
