"""Modal dialog component.

Provides consistent modal dialogs with header, content, and action buttons.
Replaces native messagebox for better styling integration.
"""

from typing import Callable, Optional, Literal
import customtkinter as ctk

from pacioli.ui.tokens import theme, Spacing, Radius, FontSize, get_font
from pacioli.ui.components.button import Button


ModalSize = Literal["sm", "md", "lg", "xl"]


class Modal(ctk.CTkToplevel):
    """Styled modal dialog.

    Args:
        master: Parent window
        title: Modal title
        size: Modal size preset
        show_close: Whether to show close button
    """

    # Size presets (width x height)
    SIZES = {
        "sm": (400, 300),
        "md": (500, 400),
        "lg": (600, 500),
        "xl": (800, 600),
    }

    def __init__(
        self,
        master: ctk.CTk,
        title: str,
        size: ModalSize = "md",
        show_close: bool = True,
        **kwargs,
    ) -> None:
        """Initialize modal dialog."""
        super().__init__(master, **kwargs)

        colors = theme.colors
        width, height = self.SIZES[size]

        # Window setup
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        # Configure appearance
        self.configure(fg_color=colors.BG_SECONDARY)

        # Main container
        self._container = ctk.CTkFrame(
            self,
            fg_color=colors.BG_SECONDARY,
            corner_radius=0,
        )
        self._container.pack(fill="both", expand=True, padx=Spacing.XL, pady=Spacing.XL)
        self._container.grid_columnconfigure(0, weight=1)

        # Header
        self._row = 0
        self._add_header(title, show_close)

        # Content area
        self._content_frame = ctk.CTkFrame(
            self._container,
            fg_color="transparent",
            corner_radius=0,
        )
        self._content_frame.grid(
            row=self._row,
            column=0,
            sticky="nsew",
            pady=Spacing.LG,
        )
        self._content_frame.grid_columnconfigure(0, weight=1)
        self._container.grid_rowconfigure(self._row, weight=1)
        self._row += 1

        # Footer (actions)
        self._footer_frame = ctk.CTkFrame(
            self._container,
            fg_color="transparent",
            corner_radius=0,
        )
        self._footer_frame.grid(
            row=self._row,
            column=0,
            sticky="ew",
            pady=(Spacing.LG, 0),
        )
        self._footer_frame.grid_columnconfigure(0, weight=1)

    def _add_header(self, title: str, show_close: bool) -> None:
        """Add header section with title and optional close button.

        Args:
            title: Header title text
            show_close: Whether to show close button
        """
        colors = theme.colors

        header = ctk.CTkFrame(self._container, fg_color="transparent", corner_radius=0)
        header.grid(row=self._row, column=0, sticky="ew", pady=(0, Spacing.LG))
        header.grid_columnconfigure(0, weight=1)

        # Title
        ctk.CTkLabel(
            header,
            text=title,
            font=get_font(FontSize.LG, "bold"),
            text_color=colors.TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        # Close button
        if show_close:
            close_btn = Button(
                header,
                text="✕",
                variant="ghost",
                size="sm",
                width=32,
                height=32,
                command=self.close,
            )
            close_btn.grid(row=0, column=1, sticky="e")

        self._row += 1

    @property
    def content(self) -> ctk.CTkFrame:
        """Get the content frame for adding widgets.

        Returns:
            Content frame where child widgets should be added
        """
        return self._content_frame

    def add_action(
        self,
        text: str,
        command: Callable,
        variant: str = "primary",
        position: Literal["left", "right"] = "right",
    ) -> Button:
        """Add an action button to the footer.

        Args:
            text: Button label
            command: Button callback
            variant: Button variant
            position: Button position (left or right)

        Returns:
            Created button instance
        """
        btn = Button(
            self._footer_frame,
            text=text,
            command=command,
            variant=variant,
            size="md",
        )

        if position == "right":
            # Pack right-aligned
            existing_buttons = self._footer_frame.grid_slaves()
            col = len([b for b in existing_buttons if "right" in str(b.grid_info())])
            btn.grid(row=0, column=10 - col, sticky="e", padx=(Spacing.SM, 0))
        else:
            btn.grid(row=0, column=0, sticky="w")

        return btn

    def close(self) -> None:
        """Close the modal dialog."""
        self.grab_release()
        self.destroy()


class ConfirmModal(Modal):
    """Confirmation dialog with OK/Cancel buttons.

    Args:
        master: Parent window
        title: Dialog title
        message: Confirmation message
        on_confirm: Callback when confirmed
        on_cancel: Callback when cancelled
        confirm_text: Confirm button text
        cancel_text: Cancel button text
        danger: Whether confirm action is destructive
    """

    def __init__(
        self,
        master: ctk.CTk,
        title: str,
        message: str,
        on_confirm: Optional[Callable] = None,
        on_cancel: Optional[Callable] = None,
        confirm_text: str = "Confirm",
        cancel_text: str = "Cancel",
        danger: bool = False,
        **kwargs,
    ) -> None:
        """Initialize confirmation modal."""
        super().__init__(master, title, size="sm", **kwargs)

        colors = theme.colors

        # Message
        ctk.CTkLabel(
            self.content,
            text=message,
            font=get_font(FontSize.BASE),
            text_color=colors.TEXT_PRIMARY,
            wraplength=400,
            justify="left",
        ).pack(fill="x", pady=Spacing.LG)

        # Actions
        self.add_action(
            cancel_text,
            command=lambda: self._handle_cancel(on_cancel),
            variant="secondary",
            position="right",
        )
        self.add_action(
            confirm_text,
            command=lambda: self._handle_confirm(on_confirm),
            variant="danger" if danger else "primary",
            position="right",
        )

    def _handle_confirm(self, callback: Optional[Callable]) -> None:
        """Handle confirm action.

        Args:
            callback: Optional callback to execute
        """
        if callback:
            callback()
        self.close()

    def _handle_cancel(self, callback: Optional[Callable]) -> None:
        """Handle cancel action.

        Args:
            callback: Optional callback to execute
        """
        if callback:
            callback()
        self.close()


class AlertModal(Modal):
    """Alert dialog with single OK button.

    Args:
        master: Parent window
        title: Dialog title
        message: Alert message
        on_ok: Callback when OK is clicked
        variant: Alert variant (info, success, warning, error)
    """

    def __init__(
        self,
        master: ctk.CTk,
        title: str,
        message: str,
        on_ok: Optional[Callable] = None,
        variant: Literal["info", "success", "warning", "error"] = "info",
        **kwargs,
    ) -> None:
        """Initialize alert modal."""
        super().__init__(master, title, size="sm", **kwargs)

        colors = theme.colors

        # Variant-specific icon and color
        variant_config = {
            "info": {"icon": "ℹ", "color": colors.INFO},
            "success": {"icon": "✓", "color": colors.SUCCESS},
            "warning": {"icon": "⚠", "color": colors.WARNING},
            "error": {"icon": "✕", "color": colors.ERROR},
        }
        config = variant_config.get(variant, variant_config["info"])

        # Icon
        ctk.CTkLabel(
            self.content,
            text=config["icon"],
            font=get_font(48),
            text_color=config["color"],
        ).pack(pady=(Spacing.LG, Spacing.SM))

        # Message
        ctk.CTkLabel(
            self.content,
            text=message,
            font=get_font(FontSize.BASE),
            text_color=colors.TEXT_PRIMARY,
            wraplength=400,
            justify="center",
        ).pack(fill="x", pady=Spacing.LG)

        # OK button
        self.add_action(
            "OK",
            command=lambda: self._handle_ok(on_ok),
            variant="primary",
            position="right",
        )

    def _handle_ok(self, callback: Optional[Callable]) -> None:
        """Handle OK action.

        Args:
            callback: Optional callback to execute
        """
        if callback:
            callback()
        self.close()
