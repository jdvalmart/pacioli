#!/usr/bin/env python3
"""Reports view."""

import customtkinter as ctk

from pacioli.ui.tokens import theme, Spacing, FontSize, get_font
from pacioli.ui.components import StatCard
from pacioli.ui.theme import styled_tabs
from pacioli.ui.charts import create_trend_chart, create_pie_chart, create_bar_chart
from pacioli.data import (
    get_monthly_summary, get_monthly_summaries, get_category_spending
)
from pacioli.core.money import fmt_cop
from pacioli.ui.utils import S


def show_reports(app):
    """Render reports view."""
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
    """Paint report charts."""
    colors = theme.colors

    # Annual trend tab
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

    # Monthly tab
    mt = app._tab_m
    mt.update_idletasks()
    mw = max(mt.winfo_width() // 2 - S(20), S(250))
    mh = max(mt.winfo_height() - S(120), S(180))

    s = get_monthly_summary(app.current_month, app.current_year)

    # Stats row
    sr = ctk.CTkFrame(mt, fg_color="transparent")
    sr.pack(fill="x", pady=(S(10), S(6)), padx=S(12))
    sr.grid_columnconfigure(0, weight=1)
    sr.grid_columnconfigure(1, weight=1)
    sr.grid_columnconfigure(2, weight=1)

    StatCard(
        sr, label="Ingresos", value=fmt_cop(s.total_income),
        trend_color=colors.SUCCESS
    ).grid(row=0, column=0, sticky="ew", padx=(0, S(6)))

    StatCard(
        sr, label="Gastos", value=fmt_cop(s.total_expense),
        trend_color=colors.ERROR
    ).grid(row=0, column=1, sticky="ew", padx=S(6))

    StatCard(
        sr, label="Balance", value=fmt_cop(s.balance),
        trend_color=colors.PRIMARY
    ).grid(row=0, column=2, sticky="ew", padx=(S(6), 0))

    # Charts row
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
