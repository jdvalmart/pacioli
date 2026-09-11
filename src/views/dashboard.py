#!/usr/bin/env python3
"""Vista de Dashboard."""

import customtkinter as ctk
import threading
from tkinter import messagebox

from theme import (
    font, btn_primary, card, styled_tabs,
    BG, SURFACE, CARD, CARD_HOVER, BORDER, ACCENT, GREEN, RED, PURPLE, TEXT, TEXT_SEC
)
from charts import create_pie_chart, create_bar_chart
from database import (
    get_monthly_summary, get_transactions, get_category_spending,
    get_budget_vs_actual, get_categories
)
from ai import analyze_spending
from utils import S, fmt_cop, lookup_cat


def show_dashboard(app):
    """Renderiza la vista de dashboard en app.main."""
    app._hl(0)
    app._view = lambda: show_dashboard(app)
    app._rerender_on_resize = True
    app._clear()
    app._title(f"📊 Dashboard — {app._mh()}")

    s = get_monthly_summary(app.current_month, app.current_year)

    stats = ctk.CTkFrame(app.main, fg_color="transparent")
    stats.grid(row=1, column=0, sticky="ew", padx=S(24), pady=(0, S(12)))
    stats.grid_columnconfigure(0, weight=1)
    stats.grid_columnconfigure(1, weight=1)
    stats.grid_columnconfigure(2, weight=1)

    _stat_card(stats, "💰 Ingresos", fmt_cop(s.total_income), GREEN)
    _stat_card(stats, "💸 Gastos", fmt_cop(s.total_expense), RED)
    _stat_card(stats, "🏦 Balance", fmt_cop(s.balance), ACCENT)

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
            messagebox.showwarning(
                "Análisis IA",
                "No se pudo conectar con Ollama.\nVerifica que esté corriendo: ollama serve",
                parent=app
            )
            return
        win = ctk.CTkToplevel(app)
        win.title(f"Análisis IA — {app._mh()}")
        win.geometry(f"{S(500)}x{S(360)}")
        win.transient(app)
        ctk.CTkLabel(win, text=f"🤖 Análisis de {app._mh()}",
                     font=font(S(16), "bold")).pack(pady=(S(14), S(8)))
        tb = ctk.CTkTextbox(win, width=S(460), height=S(260),
                            font=font(S(13)), fg_color=CARD)
        tb.pack(padx=S(16), pady=(0, S(12)), fill="both", expand=True)
        tb.insert("1.0", result)
        tb.configure(state="disabled")

    btn = ctk.CTkButton(ai_bar, text="✨ Análisis IA", height=S(32),
                        fg_color=PURPLE, hover_color="#A371F7",
                        font=font(S(13), "bold"), command=_run_analysis)
    btn.pack(side="right", padx=(S(8), 0))

    btn_chat = ctk.CTkButton(ai_bar, text="💬 Chat IA", height=S(32),
                             fg_color="#6E40C9", hover_color="#8957E5",
                             font=font(S(13), "bold"),
                             command=lambda: _open_chat(app))
    btn_chat.pack(side="right")

    app._dash_ch = ctk.CTkFrame(app.main, fg_color="transparent")
    app._dash_ch.grid(row=2, column=0, sticky="nsew", padx=S(24), pady=(0, S(12)))
    app._dash_ch.grid_columnconfigure(0, weight=1)
    app._dash_ch.grid_columnconfigure(1, weight=1)
    app._dash_ch.grid_rowconfigure(0, weight=1)
    app.after(100, lambda: _paint_dash(app))

    rf = card(app.main)
    rf.grid(row=3, column=0, sticky="ew", padx=S(24), pady=(0, S(12)))
    ctk.CTkLabel(rf, text="🕐 Últimas transacciones",
                 font=font(S(14), "bold")).pack(pady=(S(10), S(6)), padx=S(14), anchor="w")

    txns = get_transactions(app.current_month, app.current_year)[:6]
    if not txns:
        ctk.CTkLabel(rf, text="No hay transacciones este mes",
                     text_color=TEXT_SEC, font=font(S(13))).pack(pady=S(10))
    else:
        for i, t in enumerate(txns):
            icon, color, cn, ct_ = lookup_cat(t.category_id)
            rc = CARD_HOVER if i % 2 == 0 else "transparent"
            row = ctk.CTkFrame(rf, fg_color=rc, corner_radius=S(6))
            row.pack(fill="x", pady=S(1), padx=S(14))
            dlabel = f"🔁 {t.date}" if (t.is_recurring or t.generated_from) else str(t.date)
            ctk.CTkLabel(row, text=f"{icon}  {dlabel}", font=font(S(13)),
                         anchor="w").pack(side="left", padx=S(10), pady=S(6))
            ctk.CTkLabel(row, text=cn, font=font(S(13)),
                         text_color=color, anchor="w").pack(side="left", padx=S(10), pady=S(6))
            ctk.CTkLabel(row, text=t.description[:35] if t.description else "—",
                         font=font(S(12)), text_color=TEXT_SEC,
                         anchor="w").pack(side="left", padx=S(10), pady=S(6), expand=True, fill="x")
            ac = GREEN if ct_ == 'income' else RED
            pf = "+" if ct_ == 'income' else "-"
            ctk.CTkLabel(row, text=f"{pf}{fmt_cop(t.amount)}", font=font(S(14), "bold"),
                         text_color=ac, anchor="e").pack(side="right", padx=S(10), pady=S(6))


def _stat_card(parent, title, value, color):
    f = card(parent, height=S(70))
    f.pack_propagate(False)
    ctk.CTkLabel(f, text=title, font=font(S(12)),
                 text_color=TEXT_SEC).pack(pady=(S(10), S(2)), padx=S(14), anchor="w")
    ctk.CTkLabel(f, text=value, font=font(S(20), "bold"),
                 text_color=color).pack(padx=S(14), anchor="w")
    return f


def _paint_dash(app):
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
    from .chat import open_chat
    open_chat(app)
