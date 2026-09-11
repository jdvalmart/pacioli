"""Card component for content grouping.

Provides a consistent container with optional header, footer, and hover effects.
Used for grouping related content like stats, transactions, and settings.
"""

from typing import Optional, Literal
import customtkinter as ctk

from pacioli.ui.tokens import theme, Spacing, Radius, FontSize, get_font


CardVariant = Literal["default", "elevated", "outlined", "interactive"]


class Card(ctk.CTkFrame):
    """Styled card container.

    Args:
        master: Parent widget
        variant: Visual style variant
        padding: Internal padding
        hoverable: Whether card responds to hover
        title: Optional card title (creates header)
        subtitle: Optional card subtitle
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        variant: CardVariant = "default",
        padding: int = Spacing.LG,
        hoverable: bool = False,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Initialize card with variant styling."""
        colors = theme.colors
        variant_styles = self._get_variant_styles(variant, colors)

        super().__init__(
            master,
            corner_radius=Radius.LG,
            fg_color=variant_styles["fg_color"],
            border_width=variant_styles.get("border_width", 0),
            border_color=variant_styles.get("border_color", None),
            **kwargs,
        )

        self._padding = padding
        self._hoverable = hoverable
        self._original_fg = variant_styles["fg_color"]
        self._hover_fg = colors.BG_HOVER

        # Configure internal padding
        self.grid_columnconfigure(0, weight=1)

        # Add header if title provided
        self._row = 0
        if title:
            self._add_header(title, subtitle)

        # Content area
        self._content_frame = ctk.CTkFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
        )
        self._content_frame.grid(
            row=self._row,
            column=0,
            sticky="nsew",
            padx=self._padding,
            pady=self._padding,
        )
        self._content_frame.grid_columnconfigure(0, weight=1)
        self._row += 1

        # Setup hover effects
        if hoverable:
            self._setup_hover()

    def _get_variant_styles(
        self, variant: CardVariant, colors: type
    ) -> dict[str, str | int]:
        """Get styles for card variant.

        Args:
            variant: Card variant name
            colors: Current theme colors

        Returns:
            Dictionary with styling properties
        """
        variants = {
            "default": {
                "fg_color": colors.BG_TERTIARY,
            },
            "elevated": {
                "fg_color": colors.BG_TERTIARY,
                "border_width": 1,
                "border_color": colors.BORDER_SUBTLE,
            },
            "outlined": {
                "fg_color": "transparent",
                "border_width": 1,
                "border_color": colors.BORDER_DEFAULT,
            },
            "interactive": {
                "fg_color": colors.BG_TERTIARY,
                "border_width": 1,
                "border_color": colors.BORDER_SUBTLE,
            },
        }
        return variants.get(variant, variants["default"])

    def _add_header(self, title: str, subtitle: Optional[str] = None) -> None:
        """Add header section with title and optional subtitle.

        Args:
            title: Header title text
            subtitle: Optional subtitle text
        """
        colors = theme.colors

        header = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        header.grid(
            row=self._row,
            column=0,
            sticky="ew",
            padx=self._padding,
            pady=(self._padding, 0),
        )
        header.grid_columnconfigure(0, weight=1)

        # Title
        ctk.CTkLabel(
            header,
            text=title,
            font=get_font(FontSize.MD, "bold"),
            text_color=colors.TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        # Subtitle
        if subtitle:
            ctk.CTkLabel(
                header,
                text=subtitle,
                font=get_font(FontSize.SM),
                text_color=colors.TEXT_SECONDARY,
                anchor="w",
            ).grid(row=1, column=0, sticky="w", pady=(Spacing.XS, 0))

        self._row += 1

    def _setup_hover(self) -> None:
        """Setup hover effects for interactive cards."""
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, event: ctk.CTkEvent) -> None:
        """Handle mouse enter event.

        Args:
            event: Tkinter event object
        """
        self.configure(fg_color=self._hover_fg)

    def _on_leave(self, event: ctk.CTkEvent) -> None:
        """Handle mouse leave event.

        Args:
            event: Tkinter event object
        """
        self.configure(fg_color=self._original_fg)

    @property
    def content(self) -> ctk.CTkFrame:
        """Get the content frame for adding widgets.

        Returns:
            Content frame where child widgets should be added
        """
        return self._content_frame

    def add_footer(self, text: str) -> ctk.CTkLabel:
        """Add a footer section to the card.

        Args:
            text: Footer text

        Returns:
            Footer label widget
        """
        colors = theme.colors

        # Separator
        separator = ctk.CTkFrame(
            self,
            height=1,
            fg_color=colors.BORDER_SUBTLE,
            corner_radius=0,
        )
        separator.grid(
            row=self._row,
            column=0,
            sticky="ew",
            padx=self._padding,
            pady=(self._padding, Spacing.SM),
        )
        self._row += 1

        # Footer text
        footer = ctk.CTkLabel(
            self,
            text=text,
            font=get_font(FontSize.SM),
            text_color=colors.TEXT_SECONDARY,
            anchor="w",
        )
        footer.grid(
            row=self._row,
            column=0,
            sticky="ew",
            padx=self._padding,
            pady=(0, self._padding),
        )
        self._row += 1

        return footer


class StatCard(Card):
    """Specialized card for displaying statistics.

    Shows a label, value, and optional trend indicator.
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        label: str,
        value: str,
        trend: Optional[str] = None,
        trend_color: Optional[str] = None,
        icon: Optional[ctk.CTkImage] = None,
        **kwargs,
    ) -> None:
        """Initialize stat card.

        Args:
            master: Parent widget
            label: Statistic label (e.g., "Income")
            value: Statistic value (e.g., "$1,234,567")
            trend: Optional trend text (e.g., "+12%")
            trend_color: Color for trend text
            icon: Optional icon image
        """
        super().__init__(master, variant="elevated", **kwargs)

        colors = theme.colors
        content = self.content

        # Top row with icon (if provided)
        row = 0
        if icon:
            icon_label = ctk.CTkLabel(content, image=icon, text="")
            icon_label.grid(row=row, column=0, sticky="w", pady=(0, Spacing.SM))
            row += 1

        # Label
        ctk.CTkLabel(
            content,
            text=label,
            font=get_font(FontSize.SM),
            text_color=colors.TEXT_SECONDARY,
            anchor="w",
        ).grid(row=row, column=0, sticky="w")
        row += 1

        # Value
        ctk.CTkLabel(
            content,
            text=value,
            font=get_font(FontSize.XXL, "bold"),
            text_color=colors.TEXT_PRIMARY,
            anchor="w",
        ).grid(row=row, column=0, sticky="w", pady=(Spacing.XS, 0))
        row += 1

        # Trend (if provided)
        if trend:
            trend_color = trend_color or colors.TEXT_SECONDARY
            ctk.CTkLabel(
                content,
                text=trend,
                font=get_font(FontSize.SM),
                text_color=trend_color,
                anchor="w",
            ).grid(row=row, column=0, sticky="w", pady=(Spacing.XS, 0))
