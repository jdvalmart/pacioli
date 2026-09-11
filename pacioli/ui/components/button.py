"""Button component with multiple variants.

Provides consistent button styling across the application with support for
different visual variants (primary, secondary, danger, ghost) and sizes.
"""

from typing import Callable, Optional, Literal
import customtkinter as ctk

from pacioli.ui.tokens import theme, Spacing, Radius, FontSize


ButtonVariant = Literal["primary", "secondary", "danger", "ghost", "success"]
ButtonSize = Literal["sm", "md", "lg"]


class Button(ctk.CTkButton):
    """Styled button with variant support.

    Args:
        master: Parent widget
        text: Button label
        command: Callback function
        variant: Visual style variant
        size: Button size
        icon: Optional icon image
        width: Custom width (overrides size)
        height: Custom height (overrides size)
    """

    # Size presets
    SIZES = {
        "sm": {"height": 28, "font_size": FontSize.SM, "padding": Spacing.SM},
        "md": {"height": 36, "font_size": FontSize.BASE, "padding": Spacing.MD},
        "lg": {"height": 44, "font_size": FontSize.MD, "padding": Spacing.LG},
    }

    def __init__(
        self,
        master: ctk.CTkFrame,
        text: str = "",
        command: Optional[Callable] = None,
        variant: ButtonVariant = "primary",
        size: ButtonSize = "md",
        icon: Optional[ctk.CTkImage] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        **kwargs,
    ) -> None:
        """Initialize button with variant styling."""
        colors = theme.colors
        size_config = self.SIZES[size]

        # Variant-specific colors
        variant_colors = self._get_variant_colors(variant, colors)

        # Calculate dimensions
        btn_width = width or self._calculate_width(text, size)
        btn_height = height or size_config["height"]

        super().__init__(
            master,
            text=text,
            command=command,
            width=btn_width,
            height=btn_height,
            corner_radius=Radius.MD,
            font=self._get_font(size_config["font_size"]),
            fg_color=variant_colors["fg"],
            hover_color=variant_colors["hover"],
            text_color=variant_colors["text"],
            border_width=variant_colors.get("border_width", 0),
            border_color=variant_colors.get("border_color", None),
            image=icon,
            compound="left" if icon else "center",
            **kwargs,
        )

    def _get_variant_colors(
        self, variant: ButtonVariant, colors: type
    ) -> dict[str, str | int]:
        """Get colors for button variant.

        Args:
            variant: Button variant name
            colors: Current theme colors

        Returns:
            Dictionary with fg, hover, text colors
        """
        variants = {
            "primary": {
                "fg": colors.PRIMARY,
                "hover": colors.PRIMARY_HOVER,
                "text": "#FFFFFF",
            },
            "secondary": {
                "fg": colors.BG_TERTIARY,
                "hover": colors.BG_HOVER,
                "text": colors.TEXT_PRIMARY,
                "border_width": 1,
                "border_color": colors.BORDER_DEFAULT,
            },
            "danger": {
                "fg": colors.ERROR,
                "hover": colors.ERROR_HOVER,
                "text": "#FFFFFF",
            },
            "success": {
                "fg": colors.SUCCESS,
                "hover": colors.SUCCESS_HOVER,
                "text": "#FFFFFF",
            },
            "ghost": {
                "fg": "transparent",
                "hover": colors.BG_HOVER,
                "text": colors.TEXT_PRIMARY,
            },
        }
        return variants.get(variant, variants["primary"])

    def _calculate_width(self, text: str, size: ButtonSize) -> int:
        """Calculate button width based on text length.

        Args:
            text: Button label text
            size: Button size preset

        Returns:
            Calculated width in pixels
        """
        # Base width + character width
        base_widths = {"sm": 60, "md": 80, "lg": 100}
        char_widths = {"sm": 7, "md": 8, "lg": 9}

        base = base_widths[size]
        char_width = char_widths[size]
        text_width = len(text) * char_width

        return max(base, text_width + Spacing.XL)

    def _get_font(self, size: int) -> ctk.CTkFont:
        """Get font for button.

        Args:
            size: Font size

        Returns:
            CTkFont instance
        """
        from pacioli.ui.tokens import get_font, FONT_FAMILY
        return ctk.CTkFont(family=FONT_FAMILY, size=size, weight="bold")


# ── Convenience Functions ─────────────────────────────────────


def primary_button(
    master: ctk.CTkFrame,
    text: str,
    command: Optional[Callable] = None,
    **kwargs,
) -> Button:
    """Create a primary button.

    Args:
        master: Parent widget
        text: Button label
        command: Callback function

    Returns:
        Primary button instance
    """
    return Button(master, text=text, command=command, variant="primary", **kwargs)


def secondary_button(
    master: ctk.CTkFrame,
    text: str,
    command: Optional[Callable] = None,
    **kwargs,
) -> Button:
    """Create a secondary button.

    Args:
        master: Parent widget
        text: Button label
        command: Callback function

    Returns:
        Secondary button instance
    """
    return Button(master, text=text, command=command, variant="secondary", **kwargs)


def danger_button(
    master: ctk.CTkFrame,
    text: str,
    command: Optional[Callable] = None,
    **kwargs,
) -> Button:
    """Create a danger button.

    Args:
        master: Parent widget
        text: Button label
        command: Callback function

    Returns:
        Danger button instance
    """
    return Button(master, text=text, command=command, variant="danger", **kwargs)


def ghost_button(
    master: ctk.CTkFrame,
    text: str,
    command: Optional[Callable] = None,
    **kwargs,
) -> Button:
    """Create a ghost button.

    Args:
        master: Parent widget
        text: Button label
        command: Callback function

    Returns:
        Ghost button instance
    """
    return Button(master, text=text, command=command, variant="ghost", **kwargs)
