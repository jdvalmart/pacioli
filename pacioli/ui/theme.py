"""Legacy theme module - now uses tokens.

This module provides backward compatibility for existing code.
New code should import from tokens.py and components/ directly.
"""

import customtkinter as ctk

from pacioli.ui.tokens import (
    theme,
    DarkColors,
    LightColors,
    Spacing,
    Radius,
    FontSize,
    get_font,
    FONT_FAMILY,
)


# ── Backward Compatibility ────────────────────────────────────
# These aliases maintain compatibility with existing code

# Colors (from DarkColors by default)
BG = DarkColors.BG_PRIMARY
SURFACE = DarkColors.BG_SECONDARY
CARD = DarkColors.BG_TERTIARY
CARD_HOVER = DarkColors.BG_HOVER
BORDER = DarkColors.BORDER_SUBTLE
ACCENT = DarkColors.PRIMARY
GREEN = DarkColors.SUCCESS
RED = DarkColors.ERROR
ORANGE = DarkColors.WARNING
PURPLE = DarkColors.SECONDARY
TEAL = "#39D353"  # Not in tokens, keep for compatibility
TEXT = DarkColors.TEXT_PRIMARY
TEXT_SEC = DarkColors.TEXT_SECONDARY
TEXT_DIM = DarkColors.TEXT_TERTIARY

# Font family
FONT = FONT_FAMILY


# ── Theme Application ─────────────────────────────────────────


def apply_theme() -> None:
    """Apply the current theme to CustomTkinter."""
    from pacioli.ui.theme_manager import theme_manager

    # Set appearance mode
    if theme_manager.mode == "system":
        ctk.set_appearance_mode("system")
    else:
        ctk.set_appearance_mode(theme_manager.mode)

    # Set color theme
    ctk.set_default_color_theme("dark-blue")


def font(size: int = 14, weight: str = "normal") -> ctk.CTkFont:
    """Get a font with specified size and weight.

    Args:
        size: Font size in pixels
        weight: Font weight ("normal" or "bold")

    Returns:
        CTkFont instance
    """
    return get_font(size, weight)  # type: ignore


# ── Helper Functions ──────────────────────────────────────────
# These are kept for backward compatibility but new code should
# use the components module directly


def btn_primary(
    parent: ctk.CTkFrame,
    text: str,
    command=None,
    width: int = 200,
    height: int = 42,
) -> ctk.CTkButton:
    """Create a primary button.

    Args:
        parent: Parent widget
        text: Button label
        command: Button callback
        width: Button width
        height: Button height

    Returns:
        CTkButton instance
    """
    from pacioli.ui.components import Button
    return Button(parent, text=text, command=command, variant="primary", width=width, height=height)


def btn_danger(
    parent: ctk.CTkFrame,
    text: str,
    command=None,
    width: int = 80,
    height: int = 32,
) -> ctk.CTkButton:
    """Create a danger button.

    Args:
        parent: Parent widget
        text: Button label
        command: Button callback
        width: Button width
        height: Button height

    Returns:
        CTkButton instance
    """
    from pacioli.ui.components import Button
    return Button(parent, text=text, command=command, variant="danger", width=width, height=height)


def card(parent: ctk.CTkFrame, **kwargs) -> ctk.CTkFrame:
    """Create a card frame.

    Args:
        parent: Parent widget
        **kwargs: Additional frame arguments

    Returns:
        CTkFrame instance styled as a card
    """
    return ctk.CTkFrame(parent, corner_radius=Radius.LG, fg_color=CARD, **kwargs)


def styled_tabs(parent: ctk.CTkFrame, **kwargs) -> ctk.CTkTabview:
    """Create styled tabs.

    Args:
        parent: Parent widget
        **kwargs: Additional tabview arguments

    Returns:
        CTkTabview instance
    """
    tabs = ctk.CTkTabview(parent, **kwargs)
    try:
        tabs._segmented_button.configure(
            font=(FONT, FontSize.LG, "bold"),
            height=50,
            selected_color=ACCENT,
            selected_hover_color=DarkColors.PRIMARY_HOVER,
            unselected_color=CARD,
            unselected_hover_color=CARD_HOVER,
            text_color=TEXT,
            text_color_disabled=TEXT_DIM,
            corner_radius=Radius.LG,
            padding=(20, 8),
        )
    except Exception:
        pass
    return tabs
