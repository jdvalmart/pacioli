"""Toast notification component.

Provides non-intrusive notifications that appear temporarily and auto-dismiss.
Replaces messagebox for better UX in most cases.
"""

from typing import Literal, Optional
import customtkinter as ctk

from pacioli.ui.tokens import theme, Spacing, Radius, FontSize, get_font, Animation


ToastVariant = Literal["info", "success", "warning", "error"]


class Toast(ctk.CTkFrame):
    """Temporary notification toast.

    Args:
        master: Parent window
        message: Toast message
        variant: Toast variant (info, success, warning, error)
        duration: Auto-dismiss duration in milliseconds (0 = manual dismiss)
    """

    def __init__(
        self,
        master: ctk.CTk,
        message: str,
        variant: ToastVariant = "info",
        duration: int = 3000,
    ) -> None:
        """Initialize toast notification."""
        colors = theme.colors

        # Variant-specific colors
        variant_colors = {
            "info": {"bg": colors.INFO, "text": "#FFFFFF"},
            "success": {"bg": colors.SUCCESS, "text": "#FFFFFF"},
            "warning": {"bg": colors.WARNING, "text": "#FFFFFF"},
            "error": {"bg": colors.ERROR, "text": "#FFFFFF"},
        }
        config = variant_colors.get(variant, variant_colors["info"])

        super().__init__(
            master,
            fg_color=config["bg"],
            corner_radius=Radius.MD,
            height=48,
        )

        self._duration = duration
        self._message = message

        # Content
        content_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        content_frame.pack(fill="both", expand=True, padx=Spacing.MD, pady=Spacing.SM)
        content_frame.pack_propagate(False)

        # Icon
        icons = {
            "info": "ℹ",
            "success": "✓",
            "warning": "⚠",
            "error": "✕",
        }
        icon_label = ctk.CTkLabel(
            content_frame,
            text=icons.get(variant, "ℹ"),
            font=get_font(FontSize.LG, "bold"),
            text_color=config["text"],
            width=24,
        )
        icon_label.pack(side="left", padx=(0, Spacing.SM))

        # Message
        msg_label = ctk.CTkLabel(
            content_frame,
            text=message,
            font=get_font(FontSize.BASE),
            text_color=config["text"],
            anchor="w",
        )
        msg_label.pack(side="left", fill="x", expand=True)

        # Close button (for manual dismiss)
        if duration == 0:
            close_btn = ctk.CTkLabel(
                content_frame,
                text="✕",
                font=get_font(FontSize.SM),
                text_color=config["text"],
                cursor="hand2",
            )
            close_btn.pack(side="right", padx=(Spacing.SM, 0))
            close_btn.bind("<Button-1>", lambda e: self.dismiss())

    def show(self, position: Literal["top", "bottom"] = "top") -> None:
        """Show the toast notification.

        Args:
            position: Where to show the toast (top or bottom)
        """
        # Position at top or bottom of parent
        if position == "top":
            self.place(relx=0.5, rely=0.05, anchor="n")
        else:
            self.place(relx=0.5, rely=0.95, anchor="s")

        # Auto-dismiss if duration > 0
        if self._duration > 0:
            self.after(self._duration, self.dismiss)

    def dismiss(self) -> None:
        """Dismiss the toast notification."""
        self.destroy()


class ToastManager:
    """Manages toast notifications to prevent overlap.

    Singleton that tracks active toasts and positions them appropriately.
    """

    _instance: Optional["ToastManager"] = None
    _active_toasts: list[Toast] = []

    def __new__(cls) -> "ToastManager":
        """Create or return singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def show(
        self,
        master: ctk.CTk,
        message: str,
        variant: ToastVariant = "info",
        duration: int = 3000,
    ) -> Toast:
        """Show a toast notification.

        Args:
            master: Parent window
            message: Toast message
            variant: Toast variant
            duration: Auto-dismiss duration in ms

        Returns:
            Created toast instance
        """
        # Clean up dismissed toasts
        self._active_toasts = [t for t in self._active_toasts if t.winfo_exists()]

        # Create new toast
        toast = Toast(master, message, variant, duration)

        # Position below existing toasts
        offset = len(self._active_toasts) * 60
        toast.place(relx=0.5, rely=0.05 + (offset / master.winfo_height()), anchor="n")

        self._active_toasts.append(toast)

        # Show toast
        toast.show()

        # Remove from active list when dismissed
        toast.bind("<Destroy>", lambda e: self._on_toast_destroyed(toast))

        return toast

    def _on_toast_destroyed(self, toast: Toast) -> None:
        """Handle toast destruction.

        Args:
            toast: Destroyed toast instance
        """
        if toast in self._active_toasts:
            self._active_toasts.remove(toast)

    def info(self, master: ctk.CTk, message: str, duration: int = 3000) -> Toast:
        """Show info toast.

        Args:
            master: Parent window
            message: Toast message
            duration: Auto-dismiss duration

        Returns:
            Created toast instance
        """
        return self.show(master, message, "info", duration)

    def success(self, master: ctk.CTk, message: str, duration: int = 3000) -> Toast:
        """Show success toast.

        Args:
            master: Parent window
            message: Toast message
            duration: Auto-dismiss duration

        Returns:
            Created toast instance
        """
        return self.show(master, message, "success", duration)

    def warning(self, master: ctk.CTk, message: str, duration: int = 4000) -> Toast:
        """Show warning toast.

        Args:
            master: Parent window
            message: Toast message
            duration: Auto-dismiss duration

        Returns:
            Created toast instance
        """
        return self.show(master, message, "warning", duration)

    def error(self, master: ctk.CTk, message: str, duration: int = 5000) -> Toast:
        """Show error toast.

        Args:
            master: Parent window
            message: Toast message
            duration: Auto-dismiss duration

        Returns:
            Created toast instance
        """
        return self.show(master, message, "error", duration)


# Global toast manager instance
toasts = ToastManager()
