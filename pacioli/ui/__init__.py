"""UI module for Pacioli.

Contains the application, theme, components, and views.
"""

from pacioli.ui.app import BudgetApp, main
from pacioli.ui.theme import (
    # Colors
    BG,
    SURFACE,
    CARD,
    CARD_HOVER,
    BORDER,
    ACCENT,
    GREEN,
    RED,
    ORANGE,
    PURPLE,
    TEAL,
    TEXT,
    TEXT_SEC,
    TEXT_DIM,
    # Functions
    apply_theme,
    font,
    btn_primary,
    btn_danger,
    card,
    styled_tabs,
)
from pacioli.ui.tokens import (
    # Theme manager
    theme,
    ThemeManager,
    # Token classes
    DarkColors,
    LightColors,
    Spacing,
    Radius,
    FontSize,
    Elevation,
    Animation,
    # Functions
    get_font,
    FONT_FAMILY,
)
from pacioli.ui.theme_manager import (
    theme_manager,
    get_theme_mode,
    set_theme_mode,
    toggle_theme,
    is_dark_mode,
)
from pacioli.ui.icons import (
    Icon,
    IconButton,
    get_icon,
    get_emoji_icon,
    ICON_SIZES,
)
from pacioli.ui.components import (
    # Button
    Button,
    ButtonVariant,
    ButtonSize,
    primary_button,
    secondary_button,
    danger_button,
    ghost_button,
    # Card
    Card,
    CardVariant,
    StatCard,
    # Modal
    Modal,
    ModalSize,
    ConfirmModal,
    AlertModal,
    # Toast
    Toast,
    ToastVariant,
    ToastManager,
    toasts,
    # Empty State
    EmptyState,
    SearchEmptyState,
    DataEmptyState,
    ErrorEmptyState,
    # Input
    Input,
    InputVariant,
    MoneyInput,
    DateInput,
    SearchInput,
)

__all__ = [
    # App
    "BudgetApp",
    "main",
    # Legacy theme (backward compatibility)
    "BG",
    "SURFACE",
    "CARD",
    "CARD_HOVER",
    "BORDER",
    "ACCENT",
    "GREEN",
    "RED",
    "ORANGE",
    "PURPLE",
    "TEAL",
    "TEXT",
    "TEXT_SEC",
    "TEXT_DIM",
    "apply_theme",
    "font",
    "btn_primary",
    "btn_danger",
    "card",
    "styled_tabs",
    # Tokens
    "theme",
    "ThemeManager",
    "DarkColors",
    "LightColors",
    "Spacing",
    "Radius",
    "FontSize",
    "Elevation",
    "Animation",
    "get_font",
    "FONT_FAMILY",
    # Theme manager
    "theme_manager",
    "get_theme_mode",
    "set_theme_mode",
    "toggle_theme",
    "is_dark_mode",
    # Icons
    "Icon",
    "IconButton",
    "get_icon",
    "get_emoji_icon",
    "ICON_SIZES",
    # Components - Button
    "Button",
    "ButtonVariant",
    "ButtonSize",
    "primary_button",
    "secondary_button",
    "danger_button",
    "ghost_button",
    # Components - Card
    "Card",
    "CardVariant",
    "StatCard",
    # Components - Modal
    "Modal",
    "ModalSize",
    "ConfirmModal",
    "AlertModal",
    # Components - Toast
    "Toast",
    "ToastVariant",
    "ToastManager",
    "toasts",
    # Components - Empty State
    "EmptyState",
    "SearchEmptyState",
    "DataEmptyState",
    "ErrorEmptyState",
    # Components - Input
    "Input",
    "InputVariant",
    "MoneyInput",
    "DateInput",
    "SearchInput",
]
