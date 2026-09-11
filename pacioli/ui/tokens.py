"""Design tokens for Pacioli UI.

Centralized design system constants: colors, spacing, typography, and elevation.
All UI components should use these tokens for consistency.
"""

from typing import Literal
import customtkinter as ctk


# ── Color Palette ─────────────────────────────────────────────
# Semantic color names for dark mode
class DarkColors:
    """Dark mode color palette."""

    # Backgrounds
    BG_PRIMARY = "#0D1117"  # Main background
    BG_SECONDARY = "#161B22"  # Sidebar, panels
    BG_TERTIARY = "#1C2128"  # Cards, inputs
    BG_HOVER = "#252D38"  # Hover states

    # Borders
    BORDER_SUBTLE = "#30363D"  # Subtle borders
    BORDER_DEFAULT = "#484F58"  # Default borders
    BORDER_STRONG = "#6E7681"  # Strong borders

    # Text
    TEXT_PRIMARY = "#E6EDF3"  # Main text
    TEXT_SECONDARY = "#8B949E"  # Secondary text
    TEXT_TERTIARY = "#6E7681"  # Tertiary text
    TEXT_DISABLED = "#484F58"  # Disabled text

    # Brand colors
    PRIMARY = "#58A6FF"  # Blue - primary actions
    PRIMARY_HOVER = "#4C9AFF"
    SECONDARY = "#BC8CFF"  # Purple - AI features
    SECONDARY_HOVER = "#A371F7"

    # Semantic colors
    SUCCESS = "#3FB950"  # Green - income, success
    SUCCESS_HOVER = "#2EA043"
    ERROR = "#F85149"  # Red - expenses, delete
    ERROR_HOVER = "#DA3633"
    WARNING = "#D29922"  # Orange - warnings
    WARNING_HOVER = "#B08800"
    INFO = "#58A6FF"  # Blue - information

    # Category colors (expense categories)
    CAT_HOUSING = "#EF4444"
    CAT_FOOD = "#F97316"
    CAT_TRANSPORT = "#EAB308"
    CAT_UTILITIES = "#8B5CF6"
    CAT_ENTERTAINMENT = "#EC4899"
    CAT_HEALTH = "#14B8A6"
    CAT_EDUCATION = "#6366F1"
    CAT_SHOPPING = "#F43F5E"
    CAT_OTHER_EXPENSE = "#64748B"

    # Category colors (income categories)
    CAT_SALARY = "#10B981"
    CAT_FREELANCE = "#059669"
    CAT_INVESTMENTS = "#047857"
    CAT_OTHER_INCOME = "#065F46"


class LightColors:
    """Light mode color palette."""

    # Backgrounds
    BG_PRIMARY = "#FFFFFF"
    BG_SECONDARY = "#F6F8FA"
    BG_TERTIARY = "#EAEFF2"
    BG_HOVER = "#D0D7DE"

    # Borders
    BORDER_SUBTLE = "#D0D7DE"
    BORDER_DEFAULT = "#AFBAC4"
    BORDER_STRONG = "#818B98"

    # Text
    TEXT_PRIMARY = "#1F2328"
    TEXT_SECONDARY = "#59636E"
    TEXT_TERTIARY = "#6E7781"
    TEXT_DISABLED = "#AFBAC4"

    # Brand colors
    PRIMARY = "#0969DA"
    PRIMARY_HOVER = "#0860CA"
    SECONDARY = "#8250DF"
    SECONDARY_HOVER = "#6E40C9"

    # Semantic colors
    SUCCESS = "#1A7F37"
    SUCCESS_HOVER = "#116329"
    ERROR = "#CF222E"
    ERROR_HOVER = "#A40E26"
    WARNING = "#9A6700"
    WARNING_HOVER = "#7D4E00"
    INFO = "#0969DA"

    # Category colors (expense categories)
    CAT_HOUSING = "#CF222E"
    CAT_FOOD = "#BC4C00"
    CAT_TRANSPORT = "#9A6700"
    CAT_UTILITIES = "#6639BA"
    CAT_ENTERTAINMENT = "#BF3989"
    CAT_HEALTH = "#0969DA"
    CAT_EDUCATION = "#0550AE"
    CAT_SHOPPING = "#CF222E"
    CAT_OTHER_EXPENSE = "#57606A"

    # Category colors (income categories)
    CAT_SALARY = "#1A7F37"
    CAT_FREELANCE = "#116329"
    CAT_INVESTMENTS = "#0550AE"
    CAT_OTHER_INCOME = "#0969DA"


# ── Spacing Scale ─────────────────────────────────────────────
# Based on 4px grid
class Spacing:
    """Spacing scale based on 4px grid."""

    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32
    XXXL = 48


# ── Border Radius ─────────────────────────────────────────────
class Radius:
    """Border radius scale."""

    SM = 4
    MD = 8
    LG = 12
    XL = 16
    FULL = 9999


# ── Typography ────────────────────────────────────────────────
FONT_FAMILY = "Inter"  # Modern, clean sans-serif

# Font cache to avoid creating multiple CTkFont instances
_font_cache: dict[tuple[int, str], ctk.CTkFont] = {}


def get_font(size: int, weight: Literal["normal", "bold"] = "normal") -> ctk.CTkFont:
    """Get a cached CTkFont instance.

    Args:
        size: Font size in pixels
        weight: Font weight ("normal" or "bold")

    Returns:
        Cached CTkFont instance
    """
    key = (size, weight)
    if key not in _font_cache:
        _font_cache[key] = ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)
    return _font_cache[key]


class FontSize:
    """Font size scale."""

    XS = 11
    SM = 12
    BASE = 13
    MD = 14
    LG = 16
    XL = 18
    XXL = 20
    XXXL = 24


# ── Elevation / Shadows ──────────────────────────────────────
# CustomTkinter doesn't support shadows natively, but we can simulate
# elevation with border colors and background contrasts
class Elevation:
    """Elevation levels (simulated with borders/backgrounds)."""

    LEVEL_0 = 0  # Flat (no elevation)
    LEVEL_1 = 1  # Subtle (cards)
    LEVEL_2 = 2  # Medium (dropdowns)
    LEVEL_3 = 3  # High (modals)


# ── Animation Durations ───────────────────────────────────────
class Animation:
    """Animation durations in milliseconds."""

    FAST = 150
    NORMAL = 250
    SLOW = 400


# ── Theme Manager ─────────────────────────────────────────────
class ThemeManager:
    """Manages current theme and provides color access."""

    _instance = None
    _current_mode: Literal["dark", "light"] = "dark"

    def __new__(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def colors(self) -> type[DarkColors] | type[LightColors]:
        """Get current color palette."""
        return DarkColors if self._current_mode == "dark" else LightColors

    @property
    def mode(self) -> Literal["dark", "light"]:
        """Get current theme mode."""
        return self._current_mode

    def set_mode(self, mode: Literal["dark", "light"]) -> None:
        """Set theme mode.

        Args:
            mode: "dark" or "light"
        """
        self._current_mode = mode
        ctk.set_appearance_mode(mode)

    def toggle(self) -> None:
        """Toggle between dark and light mode."""
        new_mode = "light" if self._current_mode == "dark" else "dark"
        self.set_mode(new_mode)


# Global theme manager instance
theme = ThemeManager()
