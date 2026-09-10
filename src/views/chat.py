#!/usr/bin/env python3
"""Vista de Chat IA."""

import customtkinter as ctk
import threading

from theme import (
    font, btn_primary, card,
    BG, SURFACE, CARD, CARD_HOVER, BORDER, ACCENT, GREEN, RED, PURPLE, TEXT, TEXT_SEC
)
from database import (
    get_monthly_summary, get_budget_vs_actual,
    save_chat_message, get_chat_history, get_recent_chat_context,
    save_learning, get_learnings_context
)
from ai import ask_budget_question, detect_correction, extract_correction_topic
from utils import S, fmt_cop


def open_chat(app):
    """Abre la ventana de chat IA."""
    win = ctk.CTkToplevel(app)
    win.title(f"Chat IA — {app._mh()}")
    win.geometry(f"{S(560)}x{S(520)}")
    win.transient(app)

    s = get_monthly_summary(app.current_month, app.current_year)
    bva = get_budget_vs_actual(app.current_month, app.current_year)
    ctx_lines = [
        f"Período: {app._mh()}",
        f"Ingresos: ${s.total_income:,.0f}",
        f"Gastos: ${s.total_expense:,.0f}",
        f"Balance: ${s.balance:,.0f}",
    ]
    for d in bva:
        ctx_lines.append(f"- {d['name']}: ${d['actual']:,.0f} / ${d['budget']:,.0f} ({d['percent']:.0f}%)")
    budget_context = "\n".join(ctx_lines)
    learnings_ctx = get_learnings_context()

    display = ctk.CTkTextbox(win, width=S(520), height=S(360),
                             font=font(S(13)), state="disabled", fg_color=CARD)
    display.pack(padx=S(16), pady=(S(12), S(8)), fill="both", expand=True)

    input_frame = ctk.CTkFrame(win, fg_color="transparent")
    input_frame.pack(fill="x", padx=S(16), pady=(0, S(12)))

    user_input = ctk.StringVar()
    entry = ctk.CTkEntry(input_frame, textvariable=user_input, width=S(400), height=S(38),
                         placeholder_text="Pregúntale a Pacioli...",
                         font=font(S(13)), fg_color=CARD, border_color=BORDER)
    entry.pack(side="left", padx=(0, S(8)))
    entry.bind("<Return>", lambda e: _send())

    def _append(role, text):
        display.configure(state="normal")
        tag = "👤 Tú" if role == "user" else "🤖 IA"
        display.insert("end", f"\n{tag}: {text}\n")
        display.configure(state="disabled")
        display.see("end")

    def _load_history():
        history = get_chat_history(app.current_month, app.current_year, limit=30)
        if history:
            for h in history:
                _append(h['role'], h['message'])
        else:
            _append("ai", f"Hola! Soy Pacioli, tu asistente financiero para {app._mh()}.\nPregúntame lo que quieras sobre tus finanzas.")

    def _send():
        nonlocal learnings_ctx
        q = user_input.get().strip()
        if not q:
            return
        user_input.set("")
        save_chat_message("user", q, app.current_month, app.current_year)
        _append("user", q)

        if detect_correction(q):
            topic = extract_correction_topic(q)
            save_learning(topic, q)
            learnings_ctx = get_learnings_context()
            _append("ai", "📝 Anotado! Aprendí de tu corrección.")

        btn_send.configure(state="disabled", text="⏳...")
        history_ctx = get_recent_chat_context(app.current_month, app.current_year, turns=8)

        def _work():
            result = ask_budget_question(q, budget_context, history_ctx, learnings_ctx)
            app.after(0, lambda: _reply(result))
        threading.Thread(target=_work, daemon=True).start()

    def _reply(result):
        btn_send.configure(state="normal", text="Enviar")
        if result:
            save_chat_message("ai", result, app.current_month, app.current_year)
            _append("ai", result)

    btn_send = ctk.CTkButton(input_frame, text="Enviar", width=S(80), height=S(38),
                             fg_color=ACCENT, hover_color="#4C9AFF",
                             font=font(S(13), "bold"), command=_send)
    btn_send.pack(side="right")

    _load_history()
