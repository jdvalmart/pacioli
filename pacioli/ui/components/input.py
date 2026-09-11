"""Enhanced input component with validation.

Provides styled input fields with built-in validation feedback,
labels, and helper text.
"""

from typing import Optional, Callable, Literal
import customtkinter as ctk

from pacioli.ui.tokens import theme, Spacing, Radius, FontSize, get_font


InputVariant = Literal["default", "money", "date", "search"]


class Input(ctk.CTkFrame):
    """Styled input field with label and validation.

    Args:
        master: Parent widget
        label: Input label text
        placeholder: Placeholder text
        variant: Input variant (default, money, date, search)
        required: Whether field is required
        error: Error message (shows validation error)
        helper: Helper text (shows below input)
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        label: Optional[str] = None,
        placeholder: str = "",
        variant: InputVariant = "default",
        required: bool = False,
        error: Optional[str] = None,
        helper: Optional[str] = None,
        textvariable: Optional[ctk.StringVar] = None,
        **kwargs,
    ) -> None:
        """Initialize input component."""
        colors = theme.colors

        super().__init__(master, fg_color="transparent", **kwargs)

        self._variant = variant
        self._required = required
        self._error = error

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        row = 0

        # Label
        if label:
            label_text = label
            if required:
                label_text += " *"

            ctk.CTkLabel(
                self,
                text=label_text,
                font=get_font(FontSize.SM),
                text_color=colors.TEXT_PRIMARY,
                anchor="w",
            ).grid(row=row, column=0, sticky="w", pady=(0, Spacing.XS))
            row += 1

        # Input field
        border_color = colors.ERROR if error else colors.BORDER_DEFAULT
        self._entry = ctk.CTkEntry(
            self,
            placeholder_text=placeholder,
            font=get_font(FontSize.BASE),
            height=36,
            border_width=1,
            border_color=border_color,
            fg_color=colors.BG_TERTIARY,
            text_color=colors.TEXT_PRIMARY,
            textvariable=textvariable,
        )
        self._entry.grid(row=row, column=0, sticky="ew")
        row += 1

        # Error or helper text
        if error:
            ctk.CTkLabel(
                self,
                text=error,
                font=get_font(FontSize.SM),
                text_color=colors.ERROR,
                anchor="w",
            ).grid(row=row, column=0, sticky="w", pady=(Spacing.XS, 0))
        elif helper:
            ctk.CTkLabel(
                self,
                text=helper,
                font=get_font(FontSize.SM),
                text_color=colors.TEXT_SECONDARY,
                anchor="w",
            ).grid(row=row, column=0, sticky="w", pady=(Spacing.XS, 0))

    @property
    def entry(self) -> ctk.CTkEntry:
        """Get the underlying CTkEntry widget.

        Returns:
            The CTkEntry widget
        """
        return self._entry

    def get(self) -> str:
        """Get the input value.

        Returns:
            Current input text
        """
        return self._entry.get()

    def set(self, value: str) -> None:
        """Set the input value.

        Args:
            value: Text to set
        """
        self._entry.delete(0, "end")
        self._entry.insert(0, value)

    def clear(self) -> None:
        """Clear the input value."""
        self._entry.delete(0, "end")

    def focus(self) -> None:
        """Focus the input field."""
        self._entry.focus()

    def bind(self, sequence: str, callback: Callable, add: str = "") -> None:
        """Bind event to the input field.

        Args:
            sequence: Event sequence
            callback: Callback function
            add: Whether to add or replace binding
        """
        self._entry.bind(sequence, callback, add)


class MoneyInput(Input):
    """Specialized input for monetary values.

    Automatically formats values with thousand separators and
    validates numeric input.
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        label: str = "Amount",
        placeholder: str = "0.00",
        **kwargs,
    ) -> None:
        """Initialize money input."""
        super().__init__(
            master,
            label=label,
            placeholder=placeholder,
            variant="money",
            **kwargs,
        )

        # Bind validation
        self._entry.bind("<KeyRelease>", self._on_key_release)

    def _on_key_release(self, event: ctk.CTkEvent) -> None:
        """Handle key release for validation.

        Args:
            event: Tkinter event object
        """
        # Allow only numbers, dots, and commas
        value = self._entry.get()
        filtered = "".join(c for c in value if c.isdigit() or c in ".,")
        if filtered != value:
            self._entry.delete(0, "end")
            self._entry.insert(0, filtered)


class DateInput(Input):
    """Specialized input for date values.

    Provides date validation and formatting.
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        label: str = "Date",
        placeholder: str = "YYYY-MM-DD",
        **kwargs,
    ) -> None:
        """Initialize date input."""
        super().__init__(
            master,
            label=label,
            placeholder=placeholder,
            variant="date",
            **kwargs,
        )

        # Bind validation
        self._entry.bind("<KeyRelease>", self._on_key_release)

    def _on_key_release(self, event: ctk.CTkEvent) -> None:
        """Handle key release for validation.

        Args:
            event: Tkinter event object
        """
        # Allow only numbers and hyphens
        value = self._entry.get()
        filtered = "".join(c for c in value if c.isdigit() or c == "-")
        if filtered != value:
            self._entry.delete(0, "end")
            self._entry.insert(0, filtered)


class SearchInput(Input):
    """Specialized input for search with clear button.

    Args:
        master: Parent widget
        placeholder: Placeholder text
        on_change: Callback when search text changes
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        placeholder: str = "Search...",
        on_change: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        """Initialize search input."""
        colors = theme.colors

        # Create container for input + clear button
        super().__init__(master, placeholder=placeholder, variant="search", **kwargs)

        self._on_change = on_change

        # Add search icon
        search_icon = ctk.CTkLabel(
            self,
            text="🔍",
            font=get_font(FontSize.BASE),
            text_color=colors.TEXT_TERTIARY,
        )
        search_icon.place(relx=0.0, rely=0.5, anchor="w", x=8)

        # Add clear button (hidden initially)
        self._clear_btn = ctk.CTkLabel(
            self,
            text="✕",
            font=get_font(FontSize.SM),
            text_color=colors.TEXT_TERTIARY,
            cursor="hand2",
        )
        self._clear_btn.place(relx=1.0, rely=0.5, anchor="e", x=-8)
        self._clear_btn.bind("<Button-1>", self._on_clear)
        self._clear_btn.place_forget()  # Hidden initially

        # Bind events
        self._entry.bind("<KeyRelease>", self._on_change_event)

    def _on_change_event(self, event: ctk.CTkEvent) -> None:
        """Handle text change.

        Args:
            event: Tkinter event object
        """
        value = self.get()
        if value:
            self._clear_btn.place(relx=1.0, rely=0.5, anchor="e", x=-8)
        else:
            self._clear_btn.place_forget()

        if self._on_change:
            self._on_change(value)

    def _on_clear(self, event: ctk.CTkEvent) -> None:
        """Handle clear button click.

        Args:
            event: Tkinter event object
        """
        self.clear()
        self._clear_btn.place_forget()
        if self._on_change:
            self._on_change("")
