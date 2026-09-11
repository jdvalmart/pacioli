"""AI settings view for configuring AI service."""

import customtkinter as ctk
from tkinter import messagebox

from pacioli.core.config import config_manager, AIConfig
from pacioli.services.ai import ai_service
from pacioli.ui.tokens import theme, Spacing, FontSize, get_font
from pacioli.ui.components import Button, Card, Modal, AlertModal, toasts


class AISettingsView(ctk.CTkToplevel):
    """Modal view for AI settings configuration."""

    def __init__(self, parent):
        """Initialize AI settings view.

        Args:
            parent: Parent window
        """
        super().__init__(parent)
        self.title("AI Settings")
        self.geometry("500x600")
        self.transient(parent)
        self.grab_set()

        self.parent = parent
        self.config = config_manager.get_ai_config()

        self._build_ui()

    def _build_ui(self):
        """Build the settings UI."""
        colors = theme.colors

        # Main container
        container = ctk.CTkFrame(self, fg_color=colors.BG_PRIMARY)
        container.pack(fill="both", expand=True, padx=Spacing.XL, pady=Spacing.XL)

        # Title
        title = ctk.CTkLabel(
            container,
            text="🤖 AI Configuration",
            font=get_font(FontSize.XL, "bold"),
            text_color=colors.TEXT_PRIMARY
        )
        title.pack(pady=(0, Spacing.LG))

        # Connection status card
        self.status_card = Card(container, title="Connection Status", variant="elevated")
        self.status_card.pack(fill="x", pady=(0, Spacing.LG))

        self.status_label = ctk.CTkLabel(
            self.status_card.content,
            text="Checking connection...",
            font=get_font(FontSize.BASE),
            text_color=colors.TEXT_SECONDARY
        )
        self.status_label.pack(pady=Spacing.MD)

        self.check_btn = Button(
            self.status_card.content,
            text="Test Connection",
            variant="secondary",
            size="sm",
            command=self._test_connection
        )
        self.check_btn.pack(pady=(0, Spacing.MD))

        # Configuration form
        form_card = Card(container, title="Configuration", variant="elevated")
        form_card.pack(fill="x", pady=(0, Spacing.LG))

        form = form_card.content

        # Model
        ctk.CTkLabel(
            form,
            text="Model:",
            font=get_font(FontSize.BASE),
            text_color=colors.TEXT_PRIMARY
        ).pack(anchor="w", pady=(Spacing.MD, Spacing.XS))

        self.model_var = ctk.StringVar(value=self.config.model)
        self.model_entry = ctk.CTkEntry(
            form,
            textvariable=self.model_var,
            font=get_font(FontSize.BASE),
            fg_color=colors.BG_TERTIARY,
            text_color=colors.TEXT_PRIMARY,
            border_color=colors.BORDER_DEFAULT
        )
        self.model_entry.pack(fill="x")

        # URL
        ctk.CTkLabel(
            form,
            text="Ollama URL:",
            font=get_font(FontSize.BASE),
            text_color=colors.TEXT_PRIMARY
        ).pack(anchor="w", pady=(Spacing.MD, Spacing.XS))

        self.url_var = ctk.StringVar(value=self.config.url)
        self.url_entry = ctk.CTkEntry(
            form,
            textvariable=self.url_var,
            font=get_font(FontSize.BASE),
            fg_color=colors.BG_TERTIARY,
            text_color=colors.TEXT_PRIMARY,
            border_color=colors.BORDER_DEFAULT
        )
        self.url_entry.pack(fill="x")

        # Timeout
        ctk.CTkLabel(
            form,
            text="Timeout (seconds):",
            font=get_font(FontSize.BASE),
            text_color=colors.TEXT_PRIMARY
        ).pack(anchor="w", pady=(Spacing.MD, Spacing.XS))

        self.timeout_var = ctk.StringVar(value=str(self.config.timeout))
        self.timeout_entry = ctk.CTkEntry(
            form,
            textvariable=self.timeout_var,
            font=get_font(FontSize.BASE),
            fg_color=colors.BG_TERTIARY,
            text_color=colors.TEXT_PRIMARY,
            border_color=colors.BORDER_DEFAULT
        )
        self.timeout_entry.pack(fill="x")

        # Temperature
        ctk.CTkLabel(
            form,
            text="Temperature (0.0 - 1.0):",
            font=get_font(FontSize.BASE),
            text_color=colors.TEXT_PRIMARY
        ).pack(anchor="w", pady=(Spacing.MD, Spacing.XS))

        self.temp_var = ctk.StringVar(value=str(self.config.temperature))
        self.temp_entry = ctk.CTkEntry(
            form,
            textvariable=self.temp_var,
            font=get_font(FontSize.BASE),
            fg_color=colors.BG_TERTIARY,
            text_color=colors.TEXT_PRIMARY,
            border_color=colors.BORDER_DEFAULT
        )
        self.temp_entry.pack(fill="x")

        # Max tokens
        ctk.CTkLabel(
            form,
            text="Max Tokens:",
            font=get_font(FontSize.BASE),
            text_color=colors.TEXT_PRIMARY
        ).pack(anchor="w", pady=(Spacing.MD, Spacing.XS))

        self.tokens_var = ctk.StringVar(value=str(self.config.max_tokens))
        self.tokens_entry = ctk.CTkEntry(
            form,
            textvariable=self.tokens_var,
            font=get_font(FontSize.BASE),
            fg_color=colors.BG_TERTIARY,
            text_color=colors.TEXT_PRIMARY,
            border_color=colors.BORDER_DEFAULT
        )
        self.tokens_entry.pack(fill="x")

        # Buttons
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(Spacing.LG, 0))

        cancel_btn = Button(
            btn_frame,
            text="Cancel",
            variant="secondary",
            size="md",
            command=self.destroy
        )
        cancel_btn.pack(side="left", padx=(0, Spacing.SM))

        save_btn = Button(
            btn_frame,
            text="Save",
            variant="primary",
            size="md",
            command=self._save_config
        )
        save_btn.pack(side="left")

    def _test_connection(self):
        """Test connection to AI service."""
        colors = theme.colors

        self.status_label.configure(
            text="Testing connection...",
            text_color=colors.TEXT_SECONDARY
        )
        self.update()

        # Update service config temporarily for test
        test_config = AIConfig(
            model=self.model_var.get(),
            url=self.url_var.get(),
            timeout=int(self.timeout_var.get() or 30),
            temperature=float(self.temp_var.get() or 0.7),
            max_tokens=int(self.tokens_var.get() or 400)
        )

        # Create temporary service with test config
        from pacioli.services.ai import AIService
        temp_service = AIService()
        temp_service.config = test_config

        success, message = temp_service.check_connection()

        if success:
            self.status_label.configure(
                text=f"✓ {message}",
                text_color=colors.SUCCESS
            )
        else:
            self.status_label.configure(
                text=f"✗ {message}",
                text_color=colors.ERROR
            )

    def _save_config(self):
        """Save configuration and close."""
        try:
            # Validate inputs
            timeout = int(self.timeout_var.get())
            if timeout < 1:
                raise ValueError("Timeout must be at least 1 second")

            temperature = float(self.temp_var.get())
            if not 0.0 <= temperature <= 1.0:
                raise ValueError("Temperature must be between 0.0 and 1.0")

            max_tokens = int(self.tokens_var.get())
            if max_tokens < 1:
                raise ValueError("Max tokens must be at least 1")

            # Create new config
            new_config = AIConfig(
                model=self.model_var.get(),
                url=self.url_var.get(),
                timeout=timeout,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Save to config manager
            config_manager.set_ai_config(new_config)

            # Update global service
            ai_service.config = new_config

            toasts.success(self.parent, "AI settings saved")
            self.destroy()

        except ValueError as e:
            AlertModal(
                self,
                title="Invalid Input",
                message=str(e),
                variant="error"
            )
        except Exception as e:
            AlertModal(
                self,
                title="Error",
                message=f"Failed to save settings: {str(e)}",
                variant="error"
            )


def open_ai_settings(parent):
    """Open AI settings modal.

    Args:
        parent: Parent window
    """
    AISettingsView(parent)
