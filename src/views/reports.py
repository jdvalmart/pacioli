#!/usr/bin/env python3
"""Vista de Reportes."""

import customtkinter as ctk

from theme import (
    font, card, styled_tabs,
    BG, SURFACE, CARD, ACCENT, GREEN, RED, TEXT, TEXT_SEC
)
from charts import create_trend_chart, create_pie_chart, create_bar_chart
from database import (
    get_monthly_summary, get_monthly_summaries, get_category_spending
)
from utils import S, fmt_cop


def show_reports(app):
    """Renderiza la vista de reportes."""
    app._hl(3)
    app._view = lambda: show_reports(app)
    app._rerender_on_resize = True
    app._clear()
    app._title(f"📈 Reportes — {app._mh()}")

    tabs = styled_tabs(app.main)
    tabs.grid(row=1, column=0, sticky="nsew", padx=S(24), pady=(0, S(12)))
    app.main.grid_rowconfigure(1, weight=1)

    app._tab_t = tabs.add("Tendencia anual")
    app._tab_m = tabs.add(app._mh())
    app.after(100, lambda: _paint_reports(app))


def _paint_reports(app):
    tt = app._tab_t
    if not tt.winfo_exists():
        return
    tt.update_idletasks()
    tw = max(tt.winfo_width() - S(40), S(400))
    th = max(tt.winfo_height() - S(80), S(250))

    summaries = get_monthly_summaries(app.current_year)
    img = create_trend_chart(summaries, f"Tendencia {app.current_year}", size=(tw, th))
    ci = ctk.CTkImage(light_image=img, dark_image=img, size=(tw, th))
    lbl = ctk.CTkLabel(tt, image=ci, text="")
    lbl.image = ci
    lbl.pack(pady=S(12))

    mt = app._tab_m
    mt.update_idletasks()
    mw = max(mt.winfo_width() // 2 - S(20), S(250))
    mh = max(mt.winfo_height() - S(120), S(180))

    s = get_monthly_summary(app.current_month, app.current_year)
    sr = ctk.CTkFrame(mt, fg_color="transparent")
    sr.pack(fill="x", pady=(S(10), S(6)), padx=S(12))
    sr.grid_columnconfigure(0, weight=1)
    sr.grid_columnconfigure(1, weight=1)
    sr.grid_columnconfigure(2, weight=1)
    _stat_card(sr, "Ingresos", fmt_cop(s.total_income), GREEN)
    _stat_card(sr, "Gastos", fmt_cop(s.total_expense), RED)
    _stat_card(sr, "Balance", fmt_cop(s.balance), ACCENT)

    cr = ctk.CTkFrame(mt, fg_color="transparent")
    cr.pack(fill="x", padx=S(12), pady=(0, S(10)))

    inc = get_category_spending(app.current_month, app.current_year, 'income')
    exp = get_category_spending(app.current_month, app.current_year, 'expense')

    i1 = create_pie_chart(inc, "Ingresos por categoría", size=(mw, mh))
    c1 = ctk.CTkImage(light_image=i1, dark_image=i1, size=(mw, mh))
    l1 = ctk.CTkLabel(cr, image=c1, text="")
    l1.image = c1
    l1.pack(side="left", fill="x", expand=True, padx=(0, S(6)))

    i2 = create_bar_chart(exp, "Gastos por categoría", size=(mw, mh))
    c2 = ctk.CTkImage(light_image=i2, dark_image=i2, size=(mw, mh))
    l2 = ctk.CTkLabel(cr, image=c2, text="")
    l2.image = c2
    l2.pack(side="right", fill="x", expand=True, padx=(S(6), 0))


def _stat_card(parent, title, value, color):
    f = card(parent, height=S(70))
    f.pack_propagate(False)
    ctk.CTkLabel(f, text=title, font=font(S(12)),
                 text_color=TEXT_SEC).pack(pady=(S(10), S(2)), padx=S(14), anchor="w")
    ctk.CTkLabel(f, text=value, font=font(S(20), "bold"),
                 text_color=color).pack(padx=S(14), anchor="w")
    return f
