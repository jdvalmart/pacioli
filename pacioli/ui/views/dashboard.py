#!/usr/bin/env python3
"""Dashboard view."""

import customtkinter as ctk
import threading

from pacioli.ui.tokens import theme, Spacing, FontSize, get_font
from pacioli.ui.components import Button, Card, StatCard, EmptyState, AlertModal
from pacioli.ui.charts import create_pie_chart, create_bar_chart
from pacioli.data import (
    get_monthly_summary, get_transactions, get_category_spending,
    get_budget_vs_actual, get_categories, lookup_cat
)
from pacioli.services.ai import analyze_spending
from pacioli.core.money import fmt_cop
from pacioli.ui.utils import S


def show_dashboard(app):
    """Render dashboard view in app.main."""
    colors = theme.colors

    app._hl(0)
    app._view = lambda: show_dashboard(app)
    app._rerender_on_resize = True
    app._clear()
    app._title(f"📊 Dashboard — {app._mh()}")

    s = get_monthly_summary(app.current_month, app.current_year)

    # Stats container
    stats = ctk.CTkFrame(app.main, fg_color="transparent")
    stats.grid(row=1, column=0, sticky="ew", padx=S(24), pady=(0, S(12)))
    stats.grid_columnconfigure(0, weight=1)
    stats.grid_columnconfigure(1, weight=1)
    stats.grid_columnconfigure(2, weight=1)

    # Stat cards
    StatCard(
        stats,
        label="💰 Ingresos",
        value=fmt_cop(s.total_income),
        trend_color=colors.SUCCESS
    ).grid(row=0, column=0, sticky="ew", padx=(0, S(6)))

    StatCard(
        stats,
        label="💸 Gastos",
        value=fmt_cop(s.total_expense),
        trend_color=colors.ERROR
    ).grid(row=0, column=1, sticky="ew", padx=S(6))

    StatCard(
        stats,
        label="🏦 Balance",
        value=fmt_cop(s.balance),
        trend_color=colors.PRIMARY
    ).grid(row=0, column=2, sticky="ew", padx=(S(6), 0))

    # AI buttons bar
    ai_bar = ctk.CTkFrame(app.main, fg_color="transparent")
    ai_bar.grid(row=1, column=0, sticky="e", padx=S(24), pady=(0, S(4)))

    def _run_analysis():
        btn.configure(state="disabled", text="⏳ Analizando...")
        def _work():
            bva = get_budget_vs_actual(app.current_month, app.current_year)
            result = analyze_spending(app._mh(), bva, s.total_expense, s.total_income)
            app.after(0, lambda: _show_result(result))
        threading.Thread(target=_work, daemon=True).start()

    def _show_result(result):
        btn.configure(state="normal", text="✨ Análisis IA")
        if not result:
            AlertModal(
                app,
                title="Análisis IA",
                message="No se pudo conectar con Ollama.\nVerifica que esté corriendo: ollama serve",
                variant="warning"
            )
            return

        # Show result in modal
        modal = Card(app, title=f"🤖 Análisis de {app._mh()}", variant="elevated")
        modal.place(relx=0.5, rely=0.5, anchor="center")

        tb = ctk.CTkTextbox(
            modal.content,
            width=S(460),
            height=S(260),
            font=get_font(FontSize.BASE),
            fg_color=colors.BG_TERTIARY
        )
        tb.pack(padx=Spacing.LG, pady=(0, Spacing.LG), fill="both", expand=True)
        tb.insert("1.0", result)
        tb.configure(state="disabled")

    btn = Button(
        ai_bar,
        text="✨ Análisis IA",
        variant="secondary",
        size="sm",
        command=_run_analysis
    )
    btn.pack(side="right", padx=(S(8), 0))

    btn_chat = Button(
        ai_bar,
        text="💬 Chat IA",
        variant="secondary",
        size="sm",
        command=lambda: _open_chat(app)
    )
    btn_chat.pack(side="right")

    # Charts container
    app._dash_ch = ctk.CTkFrame(app.main, fg_color="transparent")
    app._dash_ch.grid(row=2, column=0, sticky="nsew", padx=S(24), pady=(0, S(12)))
    app._dash_ch.grid_columnconfigure(0, weight=1)
    app._dash_ch.grid_columnconfigure(1, weight=1)
    app._dash_ch.grid_rowconfigure(0, weight=1)
    app.after(100, lambda: _paint_dash(app))

    # Recent transactions card
    rf = Card(app.main, title="🕐 Últimas transacciones", variant="elevated")
    rf.grid(row=3, column=0, sticky="ew", padx=S(24), pady=(0, S(12)))

    txns = get_transactions(app.current_month, app.current_year)[:6]
    if not txns:
        EmptyState(
            rf.content,
            icon="📭",
            title="No hay transacciones este mes",
            message="Comienza agregando tu primera transacción"
        ).pack(pady=S(10))
    else:
        for i, t in enumerate(txns):
            icon, color, cn, ct_ = lookup_cat(t.category_id)
            rc = colors.BG_HOVER if i % 2 == 0 else "transparent"
            row = ctk.CTkFrame(rf.content, fg_color=rc, corner_radius=Spacing.SM)
            row.pack(fill="x", pady=Spacing.XS, padx=Spacing.MD)

            dlabel = f"🔁 {t.date}" if (t.is_recurring or t.generated_from) else str(t.date)
            ctk.CTkLabel(
                row,
                text=f"{icon}  {dlabel}",
                font=get_font(FontSize.BASE),
                text_color=colors.TEXT_PRIMARY,
                anchor="w"
            ).pack(side="left", padx=Spacing.SM, pady=Spacing.SM)

            ctk.CTkLabel(
                row,
                text=cn,
                font=get_font(FontSize.BASE),
                text_color=color,
                anchor="w"
            ).pack(side="left", padx=Spacing.SM, pady=Spacing.SM)

            ctk.CTkLabel(
                row,
                text=t.description[:35] if t.description else "—",
                font=get_font(FontSize.SM),
                text_color=colors.TEXT_SECONDARY,
                anchor="w"
            ).pack(side="left", padx=Spacing.SM, pady=Spacing.SM, expand=True, fill="x")

            ac = colors.SUCCESS if ct_ == 'income' else colors.ERROR
            pf = "+" if ct_ == 'income' else "-"
            ctk.CTkLabel(
                row,
                text=f"{pf}{fmt_cop(t.amount)}",
                font=get_font(FontSize.MD, "bold"),
                text_color=ac,
                anchor="e"
            ).pack(side="right", padx=Spacing.SM, pady=Spacing.SM)


def _paint_dash(app):
    """Paint dashboard charts."""
    f = app._dash_ch
    if not f.winfo_exists():
        return
    f.update_idletasks()
    cw = f.winfo_width()
    ch = f.winfo_height()
    if cw < 100 or ch < 50:
        app.after(100, lambda: _paint_dash(app))
        return
    hw = cw // 2 - S(6)

    for w in f.winfo_children():
        w.destroy()

    pie_data = get_category_spending(app.current_month, app.current_year, 'expense')
    img1 = create_pie_chart(pie_data, "Distribución de gastos", size=(hw, ch))
    c1 = ctk.CTkImage(light_image=img1, dark_image=img1, size=(hw, ch))
    l1 = ctk.CTkLabel(f, image=c1, text="")
    l1.image = c1
    l1.grid(row=0, column=0, sticky="nsew", padx=(0, S(6)))

    bar_data = get_category_spending(app.current_month, app.current_year, 'expense')
    img2 = create_bar_chart(bar_data, "Gastos por categoría", size=(hw, ch))
    c2 = ctk.CTkImage(light_image=img2, dark_image=img2, size=(hw, ch))
    l2 = ctk.CTkLabel(f, image=c2, text="")
    l2.image = c2
    l2.grid(row=0, column=1, sticky="nsew", padx=(S(6), 0))


def _open_chat(app):
    """Open chat view."""
    from .chat import open_chat
    open_chat(app)
