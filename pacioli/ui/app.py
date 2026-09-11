#!/usr/bin/env python3
"""Main application - Thin controller that orchestrates views."""

import customtkinter as ctk
from datetime import date

from pacioli.data import init_db, auto_backup, ensure_recurring
from pacioli.ui.tokens import theme, Spacing, FontSize, get_font
from pacioli.ui.theme_manager import theme_manager
from pacioli.ui.components import Button
from pacioli.ui.icons import IconButton
from pacioli.ui.utils import S, MONTHS
from pacioli.ui.views import show_dashboard, show_transactions, show_budgets, show_reports, show_categories, open_ai_settings
from pacioli.core.logging_config import logger


class BudgetApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Pacioli")
        self.geometry(f"{S(1280)}x{S(800)}")
        self.minsize(S(900), S(600))

        # Apply theme
        theme_manager.set_mode(theme_manager.mode)

        self.current_month = date.today().month
        self.current_year = date.today().year
        self._materialize_recurring()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()

        self.after(200, self._maximize)
        self.bind("<Configure>", self._on_resize)
        self._bind_shortcuts()
        self.show_dashboard()
        self.after(1000, self._auto_backup)

    def _auto_backup(self):
        """Automatic backup on startup."""
        try:
            auto_backup()
        except Exception as e:
            logger.warning(f"Error in automatic backup: {e}")

    def _materialize_recurring(self):
        """Generate recurring transactions for current month."""
        try:
            ensure_recurring(self.current_month, self.current_year)
        except Exception as e:
            logger.warning(f"Error materializing recurring transactions: {e}")

    def _bind_shortcuts(self):
        """Keyboard shortcuts."""
        self.bind("<Control-n>", lambda e: self.show_transactions())
        self.bind("<Control-t>", lambda e: self.show_transactions())
        self.bind("<Control-b>", lambda e: self.show_budgets())
        self.bind("<Control-r>", lambda e: self.show_reports())
        self.bind("<Control-d>", lambda e: self.show_dashboard())
        self.bind("<Control-c>", lambda e: self.show_categories())

    def _maximize(self):
        try:
            self.attributes('-zoomed', True)
        except Exception as e:
            logger.debug(f"Could not maximize window: {e}")
            try:
                self.state('zoomed')
            except Exception as e2:
                logger.debug(f"Could not maximize window (attempt 2): {e2}")

    def _on_resize(self, event):
        if event.widget == self and hasattr(self, '_view'):
            new_size = (event.width, event.height)
            if hasattr(self, '_last_render_size') and self._last_render_size == new_size:
                return
            if hasattr(self, '_resize_after'):
                self.after_cancel(self._resize_after)
            self._resize_after = self.after(300, self._do_resize)

    def _do_resize(self):
        if not hasattr(self, '_view'):
            return
        if getattr(self, '_rerender_on_resize', True):
            self._last_render_size = (self.winfo_width(), self.winfo_height())
            self._view()

    # ── Sidebar ──────────────────────────────────────────────
    def _build_sidebar(self):
        colors = theme.colors

        self.sidebar = ctk.CTkFrame(
            self,
            width=S(220),
            corner_radius=0,
            fg_color=colors.BG_SECONDARY
        )
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(9, weight=1)

        # App title
        ctk.CTkLabel(
            self.sidebar,
            text="💰 Pacioli",
            font=get_font(S(20), "bold"),
            text_color=colors.TEXT_PRIMARY
        ).grid(row=0, column=0, pady=(S(24), S(24)), padx=S(16))

        # Navigation buttons
        self._nav = []
        nav_items = [
            ("📊  Dashboard", self.show_dashboard),
            ("💸  Transacciones", self.show_transactions),
            ("🎯  Presupuestos", self.show_budgets),
            ("📈  Reportes", self.show_reports),
            ("⚙️  Categorías", self.show_categories),
        ]

        for i, (text, cmd) in enumerate(nav_items):
            btn = Button(
                self.sidebar,
                text=text,
                command=cmd,
                variant="ghost",
                size="md",
                width=S(196),
                height=S(40),
            )
            btn.grid(row=i + 1, column=0, sticky="ew", padx=S(12), pady=S(2))
            self._nav.append(btn)

        # Separator
        ctk.CTkFrame(
            self.sidebar,
            height=1,
            fg_color=colors.BORDER_SUBTLE
        ).grid(row=6, column=0, sticky="ew", padx=S(16), pady=S(16))

        # Period label
        ctk.CTkLabel(
            self.sidebar,
            text="Período:",
            font=get_font(FontSize.SM),
            text_color=colors.TEXT_SECONDARY
        ).grid(row=7, column=0, pady=(S(4), S(2)))

        # Month selector
        self.month_var = ctk.StringVar(value=f"{MONTHS[self.current_month]} {self.current_year}")
        months = []
        for y in range(date.today().year + 1, 2024, -1):
            for m in range(12, 0, -1):
                months.append(f"{MONTHS[m]} {y}")

        ctk.CTkOptionMenu(
            self.sidebar,
            variable=self.month_var,
            values=months,
            command=self._on_month_change,
            width=S(180),
            height=S(34),
            font=get_font(FontSize.SM),
            dropdown_font=get_font(FontSize.SM),
            fg_color=colors.BG_TERTIARY,
            button_color=colors.PRIMARY,
            button_hover_color=colors.PRIMARY_HOVER
        ).grid(row=8, column=0, pady=S(4), padx=S(16), sticky="n")

        # Bottom buttons frame
        bottom_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom_frame.grid(row=9, column=0, sticky="s", pady=S(16), padx=S(16))
        bottom_frame.grid_columnconfigure(0, weight=1)
        bottom_frame.grid_columnconfigure(1, weight=1)

        # Theme toggle button
        theme_icon = "🌙" if theme_manager.is_dark else "☀️"
        self.theme_btn = IconButton(
            bottom_frame,
            icon="settings",
            command=self._toggle_theme,
            size="md",
            tooltip="Toggle theme",
        )
        self.theme_btn.grid(row=0, column=0, padx=(0, S(8)))

        # AI settings button
        ai_btn = IconButton(
            bottom_frame,
            icon="chat",
            command=lambda: open_ai_settings(self),
            size="md",
            tooltip="AI Settings",
        )
        ai_btn.grid(row=0, column=1, padx=(S(8), 0))

    def _toggle_theme(self):
        """Toggle between dark and light theme."""
        theme_manager.toggle()
        # Update button icon
        theme_icon = "🌙" if theme_manager.is_dark else "☀️"
        self.theme_btn.configure(text=theme_icon)
        # Rebuild UI with new theme
        self._build_sidebar()
        if hasattr(self, '_view'):
            self._view()

    def _on_month_change(self, value):
        parts = value.split()
        self.current_month = list(MONTHS.keys())[list(MONTHS.values()).index(parts[0])]
        self.current_year = int(parts[1])
        self._materialize_recurring()
        if hasattr(self, '_view'):
            self._view()

    def _hl(self, idx):
        """Highlight active navigation button."""
        colors = theme.colors
        for i, btn in enumerate(self._nav):
            if i == idx:
                btn.configure(fg_color=colors.PRIMARY)
            else:
                btn.configure(fg_color="transparent")

    def _clear(self):
        """Clear main content area."""
        for w in self.main.winfo_children():
            w.destroy()

    def _mh(self):
        """Get current month/year as string."""
        return f"{MONTHS[self.current_month]} {self.current_year}"

    def _build_main(self):
        colors = theme.colors
        self.main = ctk.CTkFrame(self, corner_radius=0, fg_color=colors.BG_PRIMARY)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(2, weight=1)

    def _title(self, text):
        """Add title to main content area."""
        colors = theme.colors
        ctk.CTkLabel(
            self.main,
            text=text,
            font=get_font(S(22), "bold"),
            text_color=colors.TEXT_PRIMARY
        ).grid(row=0, column=0, sticky="w", padx=S(24), pady=(S(16), S(12)))

    # ── Views (delegation) ──────────────────────────────────
    def show_dashboard(self):
        show_dashboard(self)

    def show_transactions(self):
        show_transactions(self)

    def show_budgets(self):
        show_budgets(self)

    def show_reports(self):
        show_reports(self)

    def show_categories(self):
        show_categories(self)


def main():
    init_db()
    app = BudgetApp()
    app.mainloop()


if __name__ == '__main__':
    main()
