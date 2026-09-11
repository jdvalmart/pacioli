"""Empty state component.

Provides consistent empty state displays with icon, message, and optional CTA.
Used when lists, searches, or data views have no content to show.
"""

from typing import Optional, Callable
import customtkinter as ctk

from pacioli.ui.tokens import theme, Spacing, FontSize, get_font
from pacioli.ui.components.button import Button


class EmptyState(ctk.CTkFrame):
    """Empty state display with icon, message, and optional action.

    Args:
        master: Parent widget
        icon: Icon emoji or text (e.g., "📊", "🔍", "No data")
        title: Main title text
        message: Optional descriptive message
        action_text: Optional action button text
        action_command: Optional action button callback
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        icon: str,
        title: str,
        message: Optional[str] = None,
        action_text: Optional[str] = None,
        action_command: Optional[Callable] = None,
        **kwargs,
    ) -> None:
        """Initialize empty state component."""
        colors = theme.colors

        super().__init__(master, fg_color="transparent", **kwargs)

        # Center content
        self.grid_columnconfigure(0, weight=1)

        # Icon
        icon_label = ctk.CTkLabel(
            self,
            text=icon,
            font=get_font(64),
            text_color=colors.TEXT_TERTIARY,
        )
        icon_label.grid(row=0, column=0, pady=(0, Spacing.LG))

        # Title
        title_label = ctk.CTkLabel(
            self,
            text=title,
            font=get_font(FontSize.LG, "bold"),
            text_color=colors.TEXT_PRIMARY,
        )
        title_label.grid(row=1, column=0, pady=(0, Spacing.SM))

        # Message (if provided)
        if message:
            msg_label = ctk.CTkLabel(
                self,
                text=message,
                font=get_font(FontSize.BASE),
                text_color=colors.TEXT_SECONDARY,
                wraplength=400,
                justify="center",
            )
            msg_label.grid(row=2, column=0, pady=(0, Spacing.LG))

        # Action button (if provided)
        if action_text and action_command:
            btn = Button(
                self,
                text=action_text,
                command=action_command,
                variant="primary",
                size="md",
            )
            btn.grid(row=3, column=0, pady=(Spacing.SM, 0))


class SearchEmptyState(EmptyState):
    """Specialized empty state for search results.

    Args:
        master: Parent widget
        query: Search query that returned no results
        on_clear: Optional callback to clear search
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        query: str,
        on_clear: Optional[Callable] = None,
        **kwargs,
    ) -> None:
        """Initialize search empty state."""
        super().__init__(
            master,
            icon="🔍",
            title="No results found",
            message=f'No matches for "{query}"',
            action_text="Clear search" if on_clear else None,
            action_command=on_clear,
            **kwargs,
        )


class DataEmptyState(EmptyState):
    """Specialized empty state for data lists.

    Args:
        master: Parent widget
        data_type: Type of data (e.g., "transactions", "budgets")
        on_add: Optional callback to add new item
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        data_type: str,
        on_add: Optional[Callable] = None,
        **kwargs,
    ) -> None:
        """Initialize data empty state."""
        # Icon based on data type
        icons = {
            "transactions": "💸",
            "budgets": "🎯",
            "categories": "📁",
            "reports": "📊",
        }
        icon = icons.get(data_type, "📋")

        # Action text based on data type
        action_texts = {
            "transactions": "Add transaction",
            "budgets": "Create budget",
            "categories": "Add category",
        }
        action_text = action_texts.get(data_type, "Add new")

        super().__init__(
            master,
            icon=icon,
            title=f"No {data_type} yet",
            message=f"Get started by adding your first {data_type}",
            action_text=action_text if on_add else None,
            action_command=on_add,
            **kwargs,
        )


class ErrorEmptyState(EmptyState):
    """Specialized empty state for error states.

    Args:
        master: Parent widget
        message: Error message
        on_retry: Optional callback to retry operation
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        message: str,
        on_retry: Optional[Callable] = None,
        **kwargs,
    ) -> None:
        """Initialize error empty state."""
        super().__init__(
            master,
            icon="⚠",
            title="Something went wrong",
            message=message,
            action_text="Try again" if on_retry else None,
            action_command=on_retry,
            **kwargs,
        )
