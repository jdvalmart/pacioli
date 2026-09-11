#!/usr/bin/env python3
"""AI Chat view."""

import customtkinter as ctk
import threading

from pacioli.ui.tokens import theme, Spacing, FontSize, get_font
from pacioli.ui.components import Button, Card
from pacioli.data import (
    get_monthly_summary, get_budget_vs_actual,
    save_chat_message, get_chat_history, get_recent_chat_context,
    save_learning, get_learnings_context
)
from pacioli.services.ai import ask_budget_question, detect_correction, extract_correction_topic, MODEL
from pacioli.core.money import fmt_cop
from pacioli.ui.utils import S


def open_chat(app):
    """Open AI chat window."""
    colors = theme.colors

    win = ctk.CTkToplevel(app)
    win.title(f"Chat IA — {app._mh()}")
    win.geometry(f"{S(560)}x{S(520)}")
    win.transient(app)
    win.configure(fg_color=colors.BG_SECONDARY)

    s = get_monthly_summary(app.current_month, app.current_year)
    bva = get_budget_vs_actual(app.current_month, app.current_year)
    ctx_lines = [
        f"Período: {app._mh()}",
        f"Ingresos: {fmt_cop(s.total_income)}",
        f"Gastos: {fmt_cop(s.total_expense)}",
        f"Balance: {fmt_cop(s.balance)}",
    ]
    for d in bva:
        ctx_lines.append(f"- {d['name']}: {fmt_cop(d['actual'])} / {fmt_cop(d['budget'])} ({d['percent']:.0f}%)")
    budget_context = "\n".join(ctx_lines)
    learnings_ctx = get_learnings_context()

    # Chat display
    display = ctk.CTkTextbox(
        win, width=S(520), height=S(360),
        font=get_font(FontSize.BASE), state="disabled",
        fg_color=colors.BG_TERTIARY, text_color=colors.TEXT_PRIMARY
    )
    display.pack(padx=Spacing.LG, pady=(Spacing.LG, S(8)), fill="both", expand=True)

    # Input frame
    input_frame = ctk.CTkFrame(win, fg_color="transparent")
    input_frame.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.LG))

    user_input = ctk.StringVar()
    entry = ctk.CTkEntry(
        input_frame, textvariable=user_input, width=S(400), height=S(38),
        placeholder_text="Pregúntale a Pacioli...",
        font=get_font(FontSize.BASE),
        fg_color=colors.BG_TERTIARY, border_color=colors.BORDER_DEFAULT
    )
    entry.pack(side="left", padx=(0, S(8)))
    entry.bind("<Return>", lambda e: _send())

    def _append(role, text):
        """Append message to chat display."""
        display.configure(state="normal")
        tag = "👤 Tú" if role == "user" else "🤖 IA"
        display.insert("end", f"\n{tag}: {text}\n")
        display.configure(state="disabled")
        display.see("end")

    def _load_history():
        """Load chat history."""
        history = get_chat_history(app.current_month, app.current_year, limit=30)
        if history:
            for h in history:
                _append(h['role'], h['message'])
        else:
            _append("ai", f"Hola! Soy Pacioli, tu asistente financiero para {app._mh()}.\nPregúntame lo que quieras sobre tus finanzas.")

    def _send():
        """Send message to AI."""
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
        """Handle AI reply."""
        btn_send.configure(state="normal", text="Enviar")
        if result:
            save_chat_message("ai", result, app.current_month, app.current_year)
            _append("ai", result)
        else:
            _append("ai", "⚠️ No pude conectar con la IA. Verifica que Ollama esté corriendo "
                          f"(ollama serve) y que el modelo '{MODEL}' esté instalado.")

    btn_send = Button(
        input_frame, text="Enviar", variant="primary", size="md",
        width=S(80), height=S(38), command=_send
    )
    btn_send.pack(side="right")

    _load_history()
