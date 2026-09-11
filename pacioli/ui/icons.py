"""Icon system for Pacioli.

Provides icon loading and management. Uses emoji as fallback until SVG icons
are added to assets/icons/.
"""

from typing import Optional, Literal
from pathlib import Path
import customtkinter as ctk
from PIL import Image

from pacioli.ui.tokens import theme


IconSize = Literal["sm", "md", "lg", "xl"]
IconVariant = Literal["primary", "secondary", "success", "error", "warning", "info"]


# Icon size mapping
ICON_SIZES = {
    "sm": 16,
    "md": 20,
    "lg": 24,
    "xl": 32,
}


# Icon cache
_icon_cache: dict[tuple[str, int, str], ctk.CTkImage] = {}


# Assets directory
ASSETS_DIR = Path(__file__).parent.parent / "assets" / "icons"


def get_icon(
    name: str,
    size: IconSize = "md",
    variant: IconVariant = "primary",
) -> Optional[ctk.CTkImage]:
    """Get an icon by name.

    Attempts to load SVG from assets/icons/{name}.svg. Falls back to None
    if not found (caller should use emoji fallback).

    Args:
        name: Icon name (e.g., "dashboard", "transactions")
        size: Icon size preset
        variant: Color variant

    Returns:
        CTkImage if icon found, None otherwise
    """
    pixel_size = ICON_SIZES[size]
    cache_key = (name, pixel_size, variant)

    # Check cache
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]

    # Try to load SVG
    svg_path = ASSETS_DIR / f"{name}.svg"
    if not svg_path.exists():
        return None

    try:
        # Load and convert SVG to PNG
        # Note: PIL doesn't natively support SVG, would need cairosvg or similar
        # For now, return None and use emoji fallback
        return None
    except Exception:
        return None


def get_emoji_icon(name: str) -> str:
    """Get emoji fallback for icon name.

    Args:
        name: Icon name

    Returns:
        Emoji string
    """
    # Mapping of icon names to emojis
    emoji_map = {
        # Navigation
        "dashboard": "📊",
        "transactions": "💸",
        "budgets": "🎯",
        "reports": "📈",
        "categories": "⚙️",
        "settings": "⚙️",
        "chat": "💬",

        # Actions
        "add": "➕",
        "edit": "✏️",
        "delete": "🗑️",
        "save": "💾",
        "cancel": "✕",
        "close": "✕",
        "search": "🔍",
        "filter": "🔽",
        "export": "📥",
        "import": "📤",
        "refresh": "🔄",

        # Status
        "success": "✓",
        "error": "✕",
        "warning": "⚠",
        "info": "ℹ",

        # Finance
        "income": "💰",
        "expense": "💸",
        "balance": "🏦",
        "money": "💵",
        "card": "💳",
        "bank": "🏦",

        # Categories (expense)
        "housing": "🏠",
        "food": "🍕",
        "transport": "🚌",
        "utilities": "⚡",
        "entertainment": "🎮",
        "health": "🏥",
        "education": "📚",
        "shopping": "🛍️",

        # Categories (income)
        "salary": "💰",
        "freelance": "💻",
        "investments": "📈",

        # Misc
        "recurring": "🔁",
        "ai": "🤖",
        "calendar": "📅",
        "chart": "📊",
        "user": "👤",
        "notification": "🔔",
    }

    return emoji_map.get(name, "📁")


class Icon(ctk.CTkLabel):
    """Icon widget that displays either SVG or emoji.

    Args:
        master: Parent widget
        name: Icon name
        size: Icon size preset
        variant: Color variant
        fallback_emoji: Optional custom emoji fallback
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        name: str,
        size: IconSize = "md",
        variant: IconVariant = "primary",
        fallback_emoji: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Initialize icon widget."""
        colors = theme.colors
        pixel_size = ICON_SIZES[size]

        # Try to load SVG icon
        icon_image = get_icon(name, size, variant)

        if icon_image:
            # Use SVG icon
            super().__init__(
                master,
                image=icon_image,
                text="",
                width=pixel_size,
                height=pixel_size,
                **kwargs,
            )
        else:
            # Use emoji fallback
            emoji = fallback_emoji or get_emoji_icon(name)

            # Get color for variant
            variant_colors = {
                "primary": colors.PRIMARY,
                "secondary": colors.SECONDARY,
                "success": colors.SUCCESS,
                "error": colors.ERROR,
                "warning": colors.WARNING,
                "info": colors.INFO,
            }
            text_color = variant_colors.get(variant, colors.TEXT_PRIMARY)

            super().__init__(
                master,
                text=emoji,
                font=ctk.CTkFont(size=pixel_size),
                text_color=text_color,
                width=pixel_size,
                height=pixel_size,
                **kwargs,
            )


# ── Icon Button ───────────────────────────────────────────────


class IconButton(ctk.CTkButton):
    """Button with icon only (no text).

    Args:
        master: Parent widget
        icon: Icon name
        command: Button callback
        size: Button/icon size
        variant: Color variant
        tooltip: Optional tooltip text
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        icon: str,
        command: Optional[callable] = None,
        size: IconSize = "md",
        variant: IconVariant = "primary",
        tooltip: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Initialize icon button."""
        colors = theme.colors
        pixel_size = ICON_SIZES[size]

        # Get emoji for icon
        emoji = get_emoji_icon(icon)

        # Button size
        btn_size = pixel_size + 12

        super().__init__(
            master,
            text=emoji,
            command=command,
            width=btn_size,
            height=btn_size,
            corner_radius=8,
            font=ctk.CTkFont(size=pixel_size),
            fg_color="transparent",
            hover_color=colors.BG_HOVER,
            text_color=colors.TEXT_PRIMARY,
            **kwargs,
        )

        # Store tooltip
        self._tooltip = tooltip
        if tooltip:
            self.bind("<Enter>", self._show_tooltip)
            self.bind("<Leave>", self._hide_tooltip)

        self._tooltip_label = None

    def _show_tooltip(self, event: ctk.CTkEvent) -> None:
        """Show tooltip on hover.

        Args:
            event: Tkinter event
        """
        if not self._tooltip:
            return

        # Create tooltip label
        colors = theme.colors
        self._tooltip_label = ctk.CTkLabel(
            self.winfo_toplevel(),
            text=self._tooltip,
            font=ctk.CTkFont(size=11),
            fg_color=colors.BG_TERTIARY,
            text_color=colors.TEXT_PRIMARY,
            corner_radius=4,
            height=24,
        )

        # Position tooltip
        x = event.x_root - self.winfo_toplevel().winfo_rootx()
        y = event.y_root - self.winfo_toplevel().winfo_rooty() + 30
        self._tooltip_label.place(x=x, y=y)

    def _hide_tooltip(self, event: ctk.CTkEvent) -> None:
        """Hide tooltip.

        Args:
            event: Tkinter event
        """
        if self._tooltip_label:
            self._tooltip_label.destroy()
            self._tooltip_label = None
