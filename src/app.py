#!/usr/bin/env python3
"""App principal - Controlador delgado que orquesta las vistas."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk
from datetime import date

from database import init_db, auto_backup
from theme import apply_theme, font, BG, SURFACE, CARD, CARD_HOVER, BORDER, ACCENT, TEXT
from utils import S, MONTHS
from views import show_dashboard, show_transactions, show_budgets, show_reports, show_categories


class BudgetApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Mi Presupuesto Mensual")
        self.geometry(f"{S(1280)}x{S(800)}")
        self.minsize(S(900), S(600))
        ctk.set_appearance_mode("dark")

        self.current_month = date.today().month
        self.current_year = date.today().year

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
        """Backup automático al iniciar."""
        try:
            auto_backup()
        except Exception:
            pass

    def _bind_shortcuts(self):
        """Atajos de teclado."""
        self.bind("<Control-n>", lambda e: self.show_transactions())
        self.bind("<Control-t>", lambda e: self.show_transactions())
        self.bind("<Control-b>", lambda e: self.show_budgets())
        self.bind("<Control-r>", lambda e: self.show_reports())
        self.bind("<Control-d>", lambda e: self.show_dashboard())
        self.bind("<Control-c>", lambda e: self.show_categories())

    def _maximize(self):
        try:
            self.attributes('-zoomed', True)
        except Exception:
            self.state('zoomed')

    def _on_resize(self, event):
        if event.widget == self and hasattr(self, '_view'):
            new_size = (event.width, event.height)
            if hasattr(self, '_last_render_size') and self._last_render_size == new_size:
                return
            if hasattr(self, '_resize_after'):
                self.after_cancel(self._resize_after)
            self._resize_after = self.after(300, self._do_resize)

    def _do_resize(self):
        if hasattr(self, '_view'):
            self._last_render_size = (self.winfo_width(), self.winfo_height())
            self._view()

    # ── Sidebar ──────────────────────────────────────────────
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=S(220), corner_radius=0, fg_color=SURFACE)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(8, weight=1)

        ctk.CTkLabel(self.sidebar, text="💰 Presupuesto",
                     font=font(S(20), "bold")).grid(
            row=0, column=0, pady=(S(24), S(24)), padx=S(16))

        self._nav = []
        nav_items = [
            ("📊  Dashboard", self.show_dashboard),
            ("💸  Transacciones", self.show_transactions),
            ("🎯  Presupuestos", self.show_budgets),
            ("📈  Reportes", self.show_reports),
            ("⚙️  Categorías", self.show_categories),
        ]
        for i, (text, cmd) in enumerate(nav_items):
            b = ctk.CTkButton(
                self.sidebar, text=text, anchor="w", height=S(40),
                corner_radius=S(8), font=font(S(14)),
                fg_color="transparent", hover_color=CARD_HOVER,
                command=cmd
            )
            b.grid(row=i + 1, column=0, sticky="ew", padx=S(12), pady=S(2))
            self._nav.append(b)

        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).grid(
            row=6, column=0, sticky="ew", padx=S(16), pady=S(16))

        ctk.CTkLabel(self.sidebar, text="Período:", font=font(S(12))).grid(
            row=7, column=0, pady=(S(4), S(2)))

        self.month_var = ctk.StringVar(value=f"{MONTHS[self.current_month]} {self.current_year}")
        months = []
        for y in range(date.today().year + 1, 2024, -1):
            for m in range(12, 0, -1):
                months.append(f"{MONTHS[m]} {y}")
        ctk.CTkOptionMenu(
            self.sidebar, variable=self.month_var, values=months,
            command=self._on_month_change, width=S(180), height=S(34),
            font=font(S(12)), dropdown_font=font(S(12)),
            fg_color=CARD, button_color=ACCENT, button_hover_color="#4C9AFF"
        ).grid(row=8, column=0, pady=S(4), padx=S(16), sticky="n")

    def _on_month_change(self, value):
        parts = value.split()
        self.current_month = list(MONTHS.keys())[list(MONTHS.values()).index(parts[0])]
        self.current_year = int(parts[1])
        if hasattr(self, '_view'):
            self._view()

    def _hl(self, idx):
        for i, b in enumerate(self._nav):
            b.configure(fg_color=ACCENT if i == idx else "transparent")

    def _clear(self):
        for w in self.main.winfo_children():
            w.destroy()

    def _mh(self):
        return f"{MONTHS[self.current_month]} {self.current_year}"

    def _build_main(self):
        self.main = ctk.CTkFrame(self, corner_radius=0, fg_color=BG)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(2, weight=1)

    def _title(self, text):
        ctk.CTkLabel(self.main, text=text,
                     font=font(S(22), "bold"),
                     text_color=TEXT).grid(
            row=0, column=0, sticky="w", padx=S(24), pady=(S(16), S(12)))

    # ── Vistas (delegación) ──────────────────────────────────
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
    apply_theme()
    app = BudgetApp()
    app.mainloop()


if __name__ == '__main__':
    main()
