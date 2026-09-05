#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk
from tkinter import messagebox
from datetime import date

from database import (
    init_db, get_categories, add_category, delete_category,
    get_subcategories, add_subcategory, delete_subcategory,
    get_transactions, add_transaction, update_transaction, delete_transaction,
    set_budget, delete_budget,
    get_monthly_summary, get_monthly_summaries,
    get_category_spending, get_budget_vs_actual,
    save_chat_message, get_chat_history, clear_chat_history,
    save_learning, get_learnings_context, get_recent_chat_context,
    save_desc_learning, get_desc_learnings_context
)
from ai import generate_description, analyze_spending, ask_budget_question, detect_correction, extract_correction_topic
from theme import apply_custom_theme, THEME
from charts import (
    create_pie_chart, create_bar_chart, create_trend_chart, create_budget_chart
)

MONTHS = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

# ── Auto-scale based on screen resolution (base: 1366x768) ──
def _screen_scale():
    try:
        import tkinter as _tk
        _r = _tk.Tk()
        sw, sh = _r.winfo_screenwidth(), _r.winfo_screenheight()
        _r.destroy()
        return max(sw / 1366, sh / 768, 1.0)
    except Exception:
        return 1.0

_SC = _screen_scale()

def S(v):
    return max(int(v * _SC), 1)


def fmt_cop(v):
    return f"${int(round(abs(v))):,.0f}".replace(",", ".")


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
        self.show_dashboard()

    def _maximize(self):
        try:
            self.attributes('-zoomed', True)
        except Exception:
            self.state('zoomed')

    def _on_resize(self, event):
        if event.widget == self and hasattr(self, '_view'):
            if hasattr(self, '_resize_after'):
                self.after_cancel(self._resize_after)
            self._resize_after = self.after(300, self._view)

    # ── Sidebar ──────────────────────────────────────────────
    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=S(220), corner_radius=0, fg_color=THEME["bg_surface"])
        sb.grid(row=0, column=0, sticky="nsw")
        sb.grid_propagate(False)
        sb.grid_rowconfigure(8, weight=1)

        ctk.CTkLabel(sb, text="💰\nPresupuesto",
                     font=ctk.CTkFont(family=THEME["font_family"], size=S(22), weight="bold")).grid(row=0, column=0, pady=(S(24), S(20)), padx=S(10))

        self._nav = []
        for i, (text, cmd) in enumerate([
            ("📊  Dashboard", self.show_dashboard),
            ("💸  Transacciones", self.show_transactions),
            ("🎯  Presupuestos", self.show_budgets),
            ("📈  Reportes", self.show_reports),
            ("⚙️  Categorías", self.show_categories),
        ]):
            b = ctk.CTkButton(sb, text=text, anchor="w", height=S(42),
                              corner_radius=S(12), font=ctk.CTkFont(family=THEME["font_family"], size=S(15)),
                              fg_color="transparent", hover_color=THEME["bg_card_hover"], command=cmd)
            b.grid(row=i + 1, column=0, sticky="ew", padx=S(12), pady=S(3))
            self._nav.append(b)

        ctk.CTkFrame(sb, height=1, fg_color="#444").grid(row=6, column=0, sticky="ew", padx=S(16), pady=S(16))

        self.month_var = ctk.StringVar(value=f"{MONTHS[self.current_month]} {self.current_year}")
        ctk.CTkLabel(sb, text="Período:", font=ctk.CTkFont(family=THEME["font_family"], size=S(13))).grid(row=7, column=0, pady=(S(8), S(2)))
        months = []
        for y in range(date.today().year + 1, 2024, -1):
            for m in range(12, 0, -1):
                months.append(f"{MONTHS[m]} {y}")
        ctk.CTkOptionMenu(sb, variable=self.month_var, values=months,
                          command=self._on_month_change, width=S(180), height=S(36),
                          font=ctk.CTkFont(family=THEME["font_family"], size=S(13)),
                          dropdown_font=ctk.CTkFont(family=THEME["font_family"], size=S(14))).grid(row=8, column=0, pady=S(4), padx=S(20), sticky="n")

    def _on_month_change(self, value):
        parts = value.split()
        self.current_month = list(MONTHS.keys())[list(MONTHS.values()).index(parts[0])]
        self.current_year = int(parts[1])
        if hasattr(self, '_view'):
            self._view()

    def _hl(self, idx):
        for i, b in enumerate(self._nav):
            b.configure(fg_color=THEME["accent"] if i == idx else "transparent")

    def _clear(self):
        for w in self.main.winfo_children():
            w.destroy()

    def _mh(self):
        return f"{MONTHS[self.current_month]} {self.current_year}"

    def _build_main(self):
        self.main = ctk.CTkFrame(self, corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(2, weight=1)

    def _title(self, text):
        ctk.CTkLabel(self.main, text=text,
                     font=ctk.CTkFont(family=THEME["font_family"], size=S(24), weight="bold")).grid(
            row=0, column=0, sticky="w", padx=S(20), pady=(S(14), S(8)))

    def _card(self, parent, r, c, title, value, color):
        card = ctk.CTkFrame(parent, corner_radius=S(14), height=S(80), fg_color=THEME["bg_card"])
        card.grid(row=r, column=c, sticky="ew", padx=S(6), pady=S(4))
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(family=THEME["font_family"], size=S(14)),
                     text_color=THEME["text_muted"]).pack(pady=(S(12), S(2)), anchor="w", padx=S(16))
        ctk.CTkLabel(card, text=value, font=ctk.CTkFont(family=THEME["font_family"], size=S(24), weight="bold"),
                     text_color=color).pack(anchor="w", padx=S(16), pady=(0, S(12)))

    # ══════════════════════════════════════════════════════════
    #  DASHBOARD
    # ══════════════════════════════════════════════════════════
    def show_dashboard(self):
        self._hl(0)
        self._view = self.show_dashboard
        self._clear()

        self._title(f"📊 Dashboard — {self._mh()}")

        cards = ctk.CTkFrame(self.main, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew", padx=S(20), pady=(0, S(8)))
        cards.grid_columnconfigure(0, weight=1)
        cards.grid_columnconfigure(1, weight=1)
        cards.grid_columnconfigure(2, weight=1)

        s = get_monthly_summary(self.current_month, self.current_year)
        self._card(cards, 0, 0, "💰 Ingresos", fmt_cop(s.total_income), "#10B981")
        self._card(cards, 0, 1, "💸 Gastos", fmt_cop(s.total_expense), "#EF4444")
        self._card(cards, 0, 2, "🏦 Balance", fmt_cop(s.balance), "#3B82F6")

        ai_bar = ctk.CTkFrame(self.main, fg_color="transparent")
        ai_bar.grid(row=1, column=0, sticky="e", padx=S(20), pady=(0, S(4)))

        def _run_analysis():
            btn_ai_dash.configure(state="disabled", text="⏳ Analizando...")
            def _work():
                bva = get_budget_vs_actual(self.current_month, self.current_year)
                result = analyze_spending(self._mh(), bva, s.total_expense, s.total_income)
                self.after(0, lambda: _show_analysis(result))
            import threading
            threading.Thread(target=_work, daemon=True).start()

        def _show_analysis(result):
            btn_ai_dash.configure(state="normal", text="✨ Análisis IA")
            if not result:
                return
            win = ctk.CTkToplevel(self)
            win.title(f"Análisis IA — {self._mh()}")
            win.geometry(f"{S(520)}x{S(380)}")
            win.transient(self)
            ctk.CTkLabel(win, text=f"🤖 Análisis de {self._mh()}",
                         font=ctk.CTkFont(size=S(18), weight="bold")).pack(pady=(S(14), S(8)))
            ctk.CTkTextbox(win, width=S(480), height=S(280),
                           font=ctk.CTkFont(size=S(14))).pack(padx=S(16), pady=(0, S(12)), fill="both", expand=True)
            tb = win.winfo_children()[-1]
            tb.insert("1.0", result)
            tb.configure(state="disabled")

        btn_ai_dash = ctk.CTkButton(ai_bar, text="✨ Análisis IA", height=S(34),
                                    fg_color="#7C3AED", font=ctk.CTkFont(size=S(14), weight="bold"),
                                    command=_run_analysis)
        btn_ai_dash.pack(side="right", padx=(0, S(8)))

        btn_chat = ctk.CTkButton(ai_bar, text="💬 Chat IA", height=S(34),
                                 fg_color="#6D28D9", font=ctk.CTkFont(size=S(14), weight="bold"),
                                 command=self._open_chat)
        btn_chat.pack(side="right")

        self._dash_ch = ctk.CTkFrame(self.main, fg_color="transparent")
        self._dash_ch.grid(row=2, column=0, sticky="nsew", padx=S(20), pady=(0, S(8)))
        self._dash_ch.grid_columnconfigure(0, weight=1)
        self._dash_ch.grid_columnconfigure(1, weight=1)
        self._dash_ch.grid_rowconfigure(0, weight=1)
        self.after(100, self._paint_dash)

        rf = ctk.CTkFrame(self.main)
        rf.grid(row=3, column=0, sticky="ew", padx=S(20), pady=(0, S(10)))
        ctk.CTkLabel(rf, text="🕐 Últimas transacciones",
                     font=ctk.CTkFont(size=S(16), weight="bold")).pack(pady=(S(10), S(6)), padx=S(14), anchor="w")

        txns = get_transactions(self.current_month, self.current_year)[:6]
        if not txns:
            ctk.CTkLabel(rf, text="No hay transacciones este mes",
                         text_color="#666", font=ctk.CTkFont(size=S(14))).pack(pady=S(10))
        else:
            for i, t in enumerate(txns):
                try:
                    cat = next(c for c in get_categories() if c.id == t.category_id)
                    icon, color, cn, ct_ = cat.icon, cat.color, cat.name, cat.type
                except StopIteration:
                    icon, color, cn, ct_ = "📁", "#888", "—", "expense"
                rc = "#2B2B3D" if i % 2 == 0 else "transparent"
                row = ctk.CTkFrame(rf, fg_color=rc, corner_radius=S(4))
                row.pack(fill="x", pady=S(1), padx=S(14))
                ctk.CTkLabel(row, text=f"{icon}  {t.date}", font=ctk.CTkFont(size=S(14)),
                             anchor="w").pack(side="left", padx=S(10), pady=S(6))
                ctk.CTkLabel(row, text=cn, font=ctk.CTkFont(size=S(14)),
                             text_color=color, anchor="w").pack(side="left", padx=S(10), pady=S(6))
                ctk.CTkLabel(row, text=t.description[:35] if t.description else "—",
                             font=ctk.CTkFont(size=S(13)), text_color="#999",
                             anchor="w").pack(side="left", padx=S(10), pady=S(6), expand=True, fill="x")
                ac = "#10B981" if ct_ == 'income' else "#EF4444"
                pf = "+" if ct_ == 'income' else "-"
                ctk.CTkLabel(row, text=f"{pf}{fmt_cop(t.amount)}", font=ctk.CTkFont(size=S(15), weight="bold"),
                             text_color=ac, anchor="e").pack(side="right", padx=S(10), pady=S(6))

    def _paint_dash(self):
        f = self._dash_ch
        f.update_idletasks()
        cw = f.winfo_width()
        ch = f.winfo_height()
        if cw < 100 or ch < 50:
            self.after(100, self._paint_dash)
            return
        hw = cw // 2 - S(6)

        for w in f.winfo_children():
            w.destroy()

        pie_data = get_category_spending(self.current_month, self.current_year, 'expense')
        img1 = create_pie_chart(pie_data, "Distribución de gastos", size=(hw, ch))
        c1 = ctk.CTkImage(light_image=img1, dark_image=img1, size=(hw, ch))
        l1 = ctk.CTkLabel(f, image=c1, text="")
        l1.image = c1
        l1.grid(row=0, column=0, sticky="nsew", padx=(0, S(6)))

        bar_data = get_category_spending(self.current_month, self.current_year, 'expense')
        img2 = create_bar_chart(bar_data, "Gastos por categoría", size=(hw, ch))
        c2 = ctk.CTkImage(light_image=img2, dark_image=img2, size=(hw, ch))
        l2 = ctk.CTkLabel(f, image=c2, text="")
        l2.image = c2
        l2.grid(row=0, column=1, sticky="nsew", padx=(S(6), 0))

    # ══════════════════════════════════════════════════════════
    #  TRANSACTIONS
    # ══════════════════════════════════════════════════════════
    def _open_chat(self):
        win = ctk.CTkToplevel(self)
        win.title(f"Chat IA — {self._mh()}")
        win.geometry(f"{S(580)}x{S(560)}")
        win.transient(self)

        s = get_monthly_summary(self.current_month, self.current_year)
        bva = get_budget_vs_actual(self.current_month, self.current_year)
        context_lines = [
            f"Período: {self._mh()}",
            f"Ingresos: ${s.total_income:,.0f}",
            f"Gastos: ${s.total_expense:,.0f}",
            f"Balance: ${s.balance:,.0f}",
        ]
        for d in bva:
            context_lines.append(
                f"- {d['name']}: ${d['actual']:,.0f} / ${d['budget']:,.0f} ({d['percent']:.0f}%)"
            )
        budget_context = "\n".join(context_lines)
        learnings_ctx = get_learnings_context()

        chat_display = ctk.CTkTextbox(win, width=S(540), height=S(380),
                                       font=ctk.CTkFont(size=S(14)), state="disabled")
        chat_display.pack(padx=S(16), pady=(S(12), S(8)), fill="both", expand=True)

        input_frame = ctk.CTkFrame(win, fg_color="transparent")
        input_frame.pack(fill="x", padx=S(16), pady=(0, S(12)))

        user_input = ctk.StringVar()
        entry = ctk.CTkEntry(input_frame, textvariable=user_input, width=S(420), height=S(40),
                             placeholder_text="Pregunta sobre tu presupuesto...",
                             font=ctk.CTkFont(size=S(14)))
        entry.pack(side="left", padx=(0, S(8)))
        entry.bind("<Return>", lambda e: _send())

        def _append_chat(role, text):
            chat_display.configure(state="normal")
            tag = "Tú" if role == "user" else "🤖 IA"
            chat_display.insert("end", f"\n{tag}: {text}\n")
            chat_display.configure(state="disabled")
            chat_display.see("end")

        def _load_history():
            history = get_chat_history(self.current_month, self.current_year, limit=30)
            if history:
                for h in history:
                    _append_chat(h['role'], h['message'])
            else:
                _append_chat("ai", f"Hola! Soy tu asistente de presupuesto para {self._mh()}.\nPregúntame lo que quieras sobre tus finanzas.\n\nSi me corrijo, aprenderé de tus preferencias.")

        def _send():
            nonlocal learnings_ctx
            q = user_input.get().strip()
            if not q:
                return
            user_input.set("")
            save_chat_message("user", q, self.current_month, self.current_year)
            _append_chat("user", q)

            is_correction = detect_correction(q)
            if is_correction:
                topic = extract_correction_topic(q)
                save_learning(topic, q)
                _append_chat("ai", "📝 Anotado! Aprendí de tu corrección.")
                learnings_ctx = get_learnings_context()

            btn_send.configure(state="disabled", text="⏳...")
            history_ctx = get_recent_chat_context(self.current_month, self.current_year, turns=8)

            def _work():
                result = ask_budget_question(q, budget_context, history_ctx, learnings_ctx)
                self.after(0, lambda: _ai_reply(result, q))
            import threading
            threading.Thread(target=_work, daemon=True).start()

        def _ai_reply(result, user_msg):
            btn_send.configure(state="normal", text="Enviar")
            if result:
                save_chat_message("ai", result, self.current_month, self.current_year)
                _append_chat("ai", result)

        btn_send = ctk.CTkButton(input_frame, text="Enviar", width=S(80), height=S(40),
                                 fg_color="#7C3AED", font=ctk.CTkFont(size=S(14), weight="bold"),
                                 command=_send)
        btn_send.pack(side="right")

        btn_clear = ctk.CTkButton(input_frame, text="🗑️", width=S(40), height=S(40),
                                  fg_color="#EF4444", font=ctk.CTkFont(size=S(14)),
                                  command=lambda: self._clear_chat(win, chat_display, _load_history))
        btn_clear.pack(side="right", padx=(0, S(4)))

        _load_history()

    def _clear_chat(self, win, display, reload_fn):
        if messagebox.askyesno("Confirmar", "¿Borrar todo el historial de chat de este mes?", parent=win):
            clear_chat_history(self.current_month, self.current_year)
            display.configure(state="normal")
            display.delete("1.0", "end")
            display.configure(state="disabled")
            reload_fn()

    def show_transactions(self):
        self._hl(1)
        self._view = self.show_transactions
        self._clear()

        self._title(f"💸 Transacciones — {self._mh()}")

        tb = ctk.CTkFrame(self.main, fg_color="transparent")
        tb.grid(row=1, column=0, sticky="ew", padx=S(20), pady=(0, S(6)))
        ctk.CTkButton(tb, text="+ Nuevo gasto", width=S(150), height=S(38), fg_color="#EF4444",
                      font=ctk.CTkFont(size=S(15), weight="bold"),
                      command=lambda: self._open_tx('expense')).pack(side="left", padx=(0, S(8)))
        ctk.CTkButton(tb, text="+ Nuevo ingreso", width=S(150), height=S(38), fg_color="#10B981",
                      font=ctk.CTkFont(size=S(15), weight="bold"),
                      command=lambda: self._open_tx('income')).pack(side="left")

        lf = ctk.CTkScrollableFrame(self.main, fg_color="transparent")
        lf.grid(row=2, column=0, sticky="nsew", padx=S(20), pady=(0, S(10)))

        hdr = ctk.CTkFrame(lf, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, S(4)))
        for txt, w in [("Fecha", S(110)), ("Categoría", S(140)), ("Descripción", 0), ("Monto", S(130)), ("", S(80))]:
            kw = dict(font=ctk.CTkFont(size=S(14), weight="bold"), anchor="w")
            if w:
                kw["width"] = w
            ctk.CTkLabel(hdr, text=txt, **kw).pack(side="left", padx=S(8))
        ctk.CTkFrame(lf, height=1, fg_color="#555").pack(fill="x", pady=(0, S(4)))

        txns = get_transactions(self.current_month, self.current_year)
        if not txns:
            ctk.CTkLabel(lf, text="No hay transacciones este mes",
                         text_color="#666", font=ctk.CTkFont(size=S(14))).pack(pady=S(30))
            return

        for t in txns:
            try:
                cat = next(c for c in get_categories() if c.id == t.category_id)
                icon, color, cn, ct_ = cat.icon, cat.color, cat.name, cat.type
            except StopIteration:
                icon, color, cn, ct_ = "📁", "#888", "—", "expense"

            row = ctk.CTkFrame(lf, corner_radius=S(4))
            row.pack(fill="x", pady=S(2))
            ctk.CTkLabel(row, text=t.date, width=S(110), anchor="w",
                         font=ctk.CTkFont(size=S(14))).pack(side="left", padx=S(8), pady=S(7))
            cat_label = f"{icon} {cn}"
            if t.subcategory_name:
                cat_label += f" → {t.subcategory_icon} {t.subcategory_name}" if t.subcategory_icon else f" → {t.subcategory_name}"
            ctk.CTkLabel(row, text=cat_label, width=S(220), anchor="w", text_color=color,
                         font=ctk.CTkFont(size=S(14))).pack(side="left", padx=S(8), pady=S(7))
            ctk.CTkLabel(row, text=t.description[:40] if t.description else "—", anchor="w",
                         text_color="#CCC", font=ctk.CTkFont(size=S(13))).pack(
                side="left", padx=S(8), pady=S(7), expand=True, fill="x")
            ac = "#10B981" if ct_ == 'income' else "#EF4444"
            pf = "+" if ct_ == 'income' else "-"
            ctk.CTkLabel(row, text=f"{pf}{fmt_cop(t.amount)}", width=S(130), anchor="e",
                         text_color=ac, font=ctk.CTkFont(size=S(14), weight="bold")).pack(
                side="left", padx=S(8), pady=S(7))
            bf = ctk.CTkFrame(row, fg_color="transparent")
            bf.pack(side="right", padx=S(8), pady=S(5))
            ctk.CTkButton(bf, text="✏️", width=S(30), height=S(30), fg_color="#3B82F6",
                          font=ctk.CTkFont(size=S(13)),
                          command=lambda tt=t, ct=ct_: self._open_tx(ct, tt)).pack(side="left", padx=S(3))
            ctk.CTkButton(bf, text="🗑️", width=S(30), height=S(30), fg_color="#EF4444",
                          font=ctk.CTkFont(size=S(13)),
                          command=lambda tid=t.id: self._del_tx(tid)).pack(side="left", padx=S(3))

    def _open_tx(self, cat_type='expense', existing=None):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Editar" if existing else "Nueva transacción")
        dlg.geometry(f"{S(460)}x{S(600)}")
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="✏️ Editar" if existing else "➕ Nueva",
                     font=ctk.CTkFont(size=S(20), weight="bold")).pack(pady=(S(16), S(12)))

        f = ctk.CTkFrame(dlg, fg_color="transparent")
        f.pack(fill="x", padx=S(24), pady=(0, S(16)))

        ekw = dict(width=S(380), height=S(36), font=ctk.CTkFont(size=S(14)))
        lk = dict(font=ctk.CTkFont(size=S(14)))

        ctk.CTkLabel(f, text="Fecha (YYYY-MM-DD):", **lk).pack(anchor="w")
        dv = ctk.StringVar(value=existing.date if existing else date.today().isoformat())
        ctk.CTkEntry(f, textvariable=dv, **ekw).pack(pady=(0, S(10)))

        cats = get_categories(cat_type)
        cnames = [f"{c.icon} {c.name}" for c in cats]
        cids = [c.id for c in cats]
        ctk.CTkLabel(f, text="Categoría:", **lk).pack(anchor="w")
        cv = ctk.StringVar(value=cnames[0] if cnames else "")
        cat_menu = ctk.CTkOptionMenu(f, variable=cv, values=cnames, width=S(380), height=S(36),
                                     font=ctk.CTkFont(size=S(14)),
                                     dropdown_font=ctk.CTkFont(size=S(14)))
        cat_menu.pack(pady=(0, S(10)))

        ctk.CTkLabel(f, text="Subcategoría (opcional):", **lk).pack(anchor="w")
        sub_frame = ctk.CTkFrame(f, fg_color="transparent")
        sub_frame.pack(fill="x", pady=(0, S(10)))
        sub_var = ctk.StringVar(value="Ninguna")
        sub_menu_widget = ctk.CTkOptionMenu(sub_frame, variable=sub_var, values=["Ninguna"],
                                            width=S(380), height=S(36),
                                            font=ctk.CTkFont(size=S(14)),
                                            dropdown_font=ctk.CTkFont(size=S(14)))
        sub_menu_widget.pack()

        all_subs = {}
        for c in cats:
            all_subs[c.id] = get_subcategories(c.id)
        sub_ids_map = {}

        def update_subs(*_):
            nonlocal sub_ids_map
            try:
                sel_idx = cnames.index(cv.get())
            except ValueError:
                return
            cat_id = cids[sel_idx]
            subs = all_subs.get(cat_id, [])
            if subs:
                sub_names = ["Ninguna"] + [f"{s.icon} {s.name}" for s in subs]
                sub_ids_map = {f"{s.icon} {s.name}": s.id for s in subs}
                sub_menu_widget.configure(values=sub_names)
                sub_var.set("Ninguna")
            else:
                sub_menu_widget.configure(values=["Ninguna"])
                sub_ids_map = {}
                sub_var.set("Ninguna")

        cat_menu.configure(command=update_subs)

        if existing and existing.subcategory_id:
            for cid_key, sid in sub_ids_map.items() if sub_ids_map else []:
                pass

        ctk.CTkLabel(f, text="Monto:", **lk).pack(anchor="w")
        av = ctk.StringVar(value=str(existing.amount) if existing else "")
        ctk.CTkEntry(f, textvariable=av, **ekw).pack(pady=(0, S(10)))

        ctk.CTkLabel(f, text="Descripción:", **lk).pack(anchor="w")
        descv = ctk.StringVar(value=existing.description if existing else "")
        desc_row = ctk.CTkFrame(f, fg_color="transparent")
        desc_row.pack(fill="x", pady=(0, S(10)))
        ctk.CTkEntry(desc_row, textvariable=descv, width=S(300), height=S(36),
                     font=ctk.CTkFont(size=S(14))).pack(side="left")

        _last_ai_desc = {"value": None, "category": None}

        def _ai_desc():
            try:
                amt = float(av.get())
            except ValueError:
                amt = 0
            try:
                sel_idx = cnames.index(cv.get())
                cat_name = cats[sel_idx].name
            except (ValueError, IndexError):
                cat_name = ""
            sub_name = sub_var.get() if sub_var.get() != "Ninguna" else ""
            _last_ai_desc["category"] = cat_name
            _last_ai_desc["subcategory"] = sub_name
            btn_ai.configure(state="disabled", text="⏳...")
            learnings_ctx = get_desc_learnings_context(cat_name)
            def _run():
                result = generate_description(cat_name, sub_name, amt, learnings_ctx)
                self.after(0, lambda: _set_desc(result))
            import threading
            threading.Thread(target=_run, daemon=True).start()

        def _set_desc(result):
            btn_ai.configure(state="normal", text="✨ IA")
            if result:
                descv.set(result)
                _last_ai_desc["value"] = result

        btn_ai = ctk.CTkButton(desc_row, text="✨ IA", width=S(60), height=S(36),
                               fg_color="#7C3AED", font=ctk.CTkFont(size=S(13), weight="bold"),
                               command=_ai_desc)
        btn_ai.pack(side="right", padx=(S(6), 0))

        rv = ctk.BooleanVar(value=bool(existing.is_recurring) if existing else False)
        ctk.CTkCheckBox(f, text="Recurrente", variable=rv,
                        font=ctk.CTkFont(size=S(14))).pack(anchor="w", pady=(0, S(6)))

        dayv = ctk.StringVar(value=str(existing.recurring_day) if existing and existing.recurring_day else str(date.today().day))
        ctk.CTkLabel(f, text="Día del mes:", **lk).pack(anchor="w")
        ctk.CTkEntry(f, textvariable=dayv, **ekw).pack(pady=(0, S(10)))

        def save():
            try:
                d = date.fromisoformat(dv.get())
                amt = float(av.get())
                cid = cids[cnames.index(cv.get())]
                desc = descv.get()
                rec = rv.get()
                rday = int(dayv.get()) if rec else None
                sub_sel = sub_var.get()
                sid = sub_ids_map.get(sub_sel) if sub_sel != "Ninguna" else None

                if _last_ai_desc["value"] and desc != _last_ai_desc["value"]:
                    save_desc_learning(
                        _last_ai_desc.get("category", ""),
                        _last_ai_desc.get("subcategory", ""),
                        _last_ai_desc["value"],
                        desc
                    )

                if existing:
                    update_transaction(existing.id, d, amt, cid, desc, rec, rday, sid)
                else:
                    add_transaction(d, amt, cid, desc, rec, rday, sid)
                dlg.destroy()
                self.show_transactions()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=dlg)

        ctk.CTkButton(f, text="Guardar", fg_color="#10B981", command=save,
                      width=S(380), height=S(42), font=ctk.CTkFont(size=S(15), weight="bold")).pack(pady=(S(12), 0))

    def _del_tx(self, tid):
        if messagebox.askyesno("Confirmar", "¿Eliminar esta transacción?", parent=self):
            delete_transaction(tid)
            self.show_transactions()

    # ══════════════════════════════════════════════════════════
    #  BUDGETS
    # ══════════════════════════════════════════════════════════
    def show_budgets(self):
        self._hl(2)
        self._view = self.show_budgets
        self._clear()

        self._title(f"🎯 Presupuestos — {self._mh()}")

        tb = ctk.CTkFrame(self.main, fg_color="transparent")
        tb.grid(row=1, column=0, sticky="ew", padx=S(20), pady=(0, S(6)))
        ctk.CTkButton(tb, text="+ Asignar presupuesto", width=S(220), height=S(38), fg_color="#3B82F6",
                      font=ctk.CTkFont(size=S(15), weight="bold"),
                      command=self._open_bdlg).pack(side="left")

        bva = get_budget_vs_actual(self.current_month, self.current_year)

        self._bva_f = ctk.CTkFrame(self.main, fg_color="transparent")
        self._bva_f.grid(row=2, column=0, sticky="nsew", padx=S(20), pady=(0, S(8)))
        self._bva_f.grid_columnconfigure(0, weight=1)
        self._bva_f.grid_columnconfigure(1, weight=1)
        self._bva_f.grid_rowconfigure(0, weight=1)
        self._bva_d = bva
        self.after(100, self._paint_bva)

        if bva:
            tf = ctk.CTkFrame(self.main)
            tf.grid(row=3, column=0, sticky="ew", padx=S(20), pady=(0, S(10)))
            ctk.CTkLabel(tf, text="📋 Detalle por categoría",
                         font=ctk.CTkFont(size=S(16), weight="bold")).pack(pady=(S(10), S(6)), padx=S(14), anchor="w")

            hdr = ctk.CTkFrame(tf, fg_color="transparent")
            hdr.pack(fill="x", padx=S(14), pady=(0, S(4)))
            for txt, w in [("Categoría", S(160)), ("Presupuesto", S(120)), ("Real", S(120)),
                           ("Restante", S(120)), ("%", S(60)), ("", S(40))]:
                ctk.CTkLabel(hdr, text=txt, font=ctk.CTkFont(size=S(14), weight="bold"),
                             width=w, anchor="w").pack(side="left", padx=S(4))

            for i, d in enumerate(bva):
                rc = "#2B2B3D" if i % 2 == 0 else "transparent"
                row = ctk.CTkFrame(tf, fg_color=rc, corner_radius=S(4))
                row.pack(fill="x", pady=S(1), padx=S(14))
                ctk.CTkLabel(row, text=f"{d['icon']} {d['name']}", anchor="w", width=S(160),
                             font=ctk.CTkFont(size=S(14))).pack(side="left", padx=S(4), pady=S(7))
                ctk.CTkLabel(row, text=fmt_cop(d['budget']), width=S(120), anchor="w", text_color="#89B4FA",
                             font=ctk.CTkFont(size=S(14))).pack(side="left", padx=S(4), pady=S(7))
                ctk.CTkLabel(row, text=fmt_cop(d['actual']), width=S(120), anchor="w", text_color="#FAB387",
                             font=ctk.CTkFont(size=S(14))).pack(side="left", padx=S(4), pady=S(7))
                rem = d['remaining']
                rc2 = "#A6E3A1" if rem >= 0 else "#F38BA8"
                ctk.CTkLabel(row, text=fmt_cop(rem), width=S(120), anchor="w", text_color=rc2,
                             font=ctk.CTkFont(size=S(14))).pack(side="left", padx=S(4), pady=S(7))
                pct = d['percent']
                pc = "#A6E3A1" if pct <= 80 else ("#F9E2AF" if pct <= 100 else "#F38BA8")
                ctk.CTkLabel(row, text=f"{pct:.0f}%", width=S(60), anchor="w", text_color=pc,
                             font=ctk.CTkFont(size=S(14), weight="bold")).pack(side="left", padx=S(4), pady=S(7))
                ctk.CTkButton(row, text="🗑️", width=S(30), height=S(30), fg_color="#EF4444",
                              font=ctk.CTkFont(size=S(13)),
                              command=lambda cid=d['category_id']: self._del_b(cid)).pack(
                    side="right", padx=S(6), pady=S(5))
        else:
            ctk.CTkLabel(self.main, text="No hay presupuestos definidos para este mes",
                         text_color="#666", font=ctk.CTkFont(size=S(15))).grid(row=3, column=0, pady=S(30))

    def _paint_bva(self):
        f = self._bva_f
        f.update_idletasks()
        cw = f.winfo_width()
        ch = f.winfo_height()
        if cw < 100 or ch < 50:
            self.after(100, self._paint_bva)
            return
        hw = cw // 2 - S(6)

        for w in f.winfo_children():
            w.destroy()

        img1 = create_budget_chart(self._bva_d, "Presupuesto vs Real", size=(hw, ch))
        c1 = ctk.CTkImage(light_image=img1, dark_image=img1, size=(hw, ch))
        l1 = ctk.CTkLabel(f, image=c1, text="")
        l1.image = c1
        l1.grid(row=0, column=0, sticky="nsew", padx=(0, S(6)))

        pb = [(d['name'], d['budget'], d['color'], d['icon']) for d in self._bva_d if d['budget'] > 0]
        img2 = create_pie_chart(pb, "Presupuesto por categoría", size=(hw, ch))
        c2 = ctk.CTkImage(light_image=img2, dark_image=img2, size=(hw, ch))
        l2 = ctk.CTkLabel(f, image=c2, text="")
        l2.image = c2
        l2.grid(row=0, column=1, sticky="nsew", padx=(S(6), 0))

    def _open_bdlg(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Asignar presupuesto")
        dlg.geometry(f"{S(440)}x{S(320)}")
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="🎯 Asignar presupuesto",
                     font=ctk.CTkFont(size=S(20), weight="bold")).pack(pady=(S(16), S(12)))

        f = ctk.CTkFrame(dlg, fg_color="transparent")
        f.pack(fill="x", padx=S(24), pady=(0, S(16)))

        exp = get_categories('expense')
        cn = [f"{c.icon} {c.name}" for c in exp]
        ci = [c.id for c in exp]

        lk = dict(font=ctk.CTkFont(size=S(14)))
        ctk.CTkLabel(f, text="Categoría:", **lk).pack(anchor="w")
        cv = ctk.StringVar(value=cn[0] if cn else "")
        ctk.CTkOptionMenu(f, variable=cv, values=cn, width=S(370), height=S(36),
                          font=ctk.CTkFont(size=S(14)),
                          dropdown_font=ctk.CTkFont(size=S(14))).pack(pady=(0, S(14)))

        ctk.CTkLabel(f, text="Presupuesto mensual:", **lk).pack(anchor="w")
        av = ctk.StringVar()
        ctk.CTkEntry(f, textvariable=av, width=S(370), height=S(36),
                     placeholder_text="0.00", font=ctk.CTkFont(size=S(14))).pack(pady=(0, S(16)))

        def save():
            try:
                cid = ci[cn.index(cv.get())]
                set_budget(cid, self.current_month, self.current_year, float(av.get()))
                dlg.destroy()
                self.show_budgets()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=dlg)

        ctk.CTkButton(f, text="Guardar", fg_color="#10B981", command=save,
                      width=S(370), height=S(42), font=ctk.CTkFont(size=S(15), weight="bold")).pack()

    def _del_b(self, cid):
        if messagebox.askyesno("Confirmar", "¿Eliminar este presupuesto?", parent=self):
            delete_budget(cid, self.current_month, self.current_year)
            self.show_budgets()

    # ══════════════════════════════════════════════════════════
    #  REPORTS
    # ══════════════════════════════════════════════════════════
    def show_reports(self):
        self._hl(3)
        self._view = self.show_reports
        self._clear()

        self._title(f"📈 Reportes — {self._mh()}")

        tabs = ctk.CTkTabview(self.main)
        tabs.grid(row=1, column=0, sticky="nsew", padx=S(20), pady=(0, S(10)))
        self.main.grid_rowconfigure(1, weight=1)

        self._tab_t = tabs.add("Tendencia anual")
        self._tab_m = tabs.add(self._mh())
        self.after(100, self._paint_reports)

    def _paint_reports(self):
        tt = self._tab_t
        tt.update_idletasks()
        tw = max(tt.winfo_width() - S(40), S(400))
        th = max(tt.winfo_height() - S(80), S(250))

        summaries = get_monthly_summaries(self.current_year)
        img = create_trend_chart(summaries, f"Tendencia {self.current_year}", size=(tw, th))
        ci = ctk.CTkImage(light_image=img, dark_image=img, size=(tw, th))
        lbl = ctk.CTkLabel(tt, image=ci, text="")
        lbl.image = ci
        lbl.pack(pady=S(12))

        mt = self._tab_m
        mt.update_idletasks()
        mw = max(mt.winfo_width() // 2 - S(20), S(250))
        mh = max(mt.winfo_height() - S(120), S(180))

        s = get_monthly_summary(self.current_month, self.current_year)
        sr = ctk.CTkFrame(mt, fg_color="transparent")
        sr.pack(fill="x", pady=(S(10), S(6)), padx=S(12))
        sr.grid_columnconfigure(0, weight=1)
        sr.grid_columnconfigure(1, weight=1)
        sr.grid_columnconfigure(2, weight=1)
        self._card(sr, 0, 0, "Ingresos", fmt_cop(s.total_income), "#10B981")
        self._card(sr, 0, 1, "Gastos", fmt_cop(s.total_expense), "#EF4444")
        self._card(sr, 0, 2, "Balance", fmt_cop(s.balance), "#3B82F6")

        cr = ctk.CTkFrame(mt, fg_color="transparent")
        cr.pack(fill="x", padx=S(12), pady=(0, S(10)))

        inc = get_category_spending(self.current_month, self.current_year, 'income')
        exp = get_category_spending(self.current_month, self.current_year, 'expense')

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

    # ══════════════════════════════════════════════════════════
    #  CATEGORIES
    # ══════════════════════════════════════════════════════════
    def show_categories(self):
        self._hl(4)
        self._view = self.show_categories
        self._clear()

        self._title("⚙️ Categorías")

        tb = ctk.CTkFrame(self.main, fg_color="#1E1E2E")
        tb.grid(row=1, column=0, sticky="ew", padx=S(20), pady=(0, S(8)))
        ctk.CTkButton(tb, text="➕ Nueva categoría", width=S(240), height=S(44), fg_color="#3B82F6",
                      font=ctk.CTkFont(size=S(16), weight="bold"),
                      command=self._open_cdlg).pack(side="left")

        tab_font = ctk.CTkFont(size=S(16), weight="bold")
        tabs = ctk.CTkTabview(self.main, height=S(500))
        tabs.grid(row=2, column=0, sticky="nsew", padx=S(20), pady=(0, S(10)))
        self.main.grid_rowconfigure(2, weight=1)

        t1 = tabs.add("💸 Gastos")
        t2 = tabs.add("💰 Ingresos")

        try:
            tabs._segmented_button.configure(font=tab_font, height=S(38))
        except Exception:
            pass

        for container, ct in [(t1, 'expense'), (t2, 'income')]:
            cats = get_categories(ct)
            if not cats:
                ctk.CTkLabel(container, text="No hay categorías", text_color="#666",
                             font=ctk.CTkFont(size=S(14))).pack(pady=S(20))
                continue
            for c in cats:
                cat_frame = ctk.CTkFrame(container, corner_radius=S(6))
                cat_frame.pack(fill="x", pady=S(3), padx=S(10))

                row = ctk.CTkFrame(cat_frame, fg_color="transparent")
                row.pack(fill="x")
                ctk.CTkLabel(row, text=f"{c.icon}  {c.name}", anchor="w",
                             font=ctk.CTkFont(size=S(16))).pack(side="left", padx=S(10), pady=S(10))
                ctk.CTkFrame(row, width=S(22), height=S(22),
                             fg_color=c.color, corner_radius=S(4)).pack(side="left", padx=S(10))
                ctk.CTkButton(row, text="+ Sub", width=S(60), height=S(28), fg_color="#3B82F6",
                              font=ctk.CTkFont(size=S(12)),
                              command=lambda cid=c.id: self._open_subdlg(cid)).pack(side="right", padx=(0, S(4)), pady=S(6))
                ctk.CTkButton(row, text="🗑️", width=S(30), height=S(28), fg_color="#EF4444",
                              font=ctk.CTkFont(size=S(12)),
                              command=lambda cid=c.id: self._del_cat(cid)).pack(
                    side="right", padx=S(4), pady=S(6))

                subs = get_subcategories(c.id)
                if subs:
                    sub_container = ctk.CTkFrame(cat_frame, fg_color="transparent")
                    sub_container.pack(fill="x", padx=S(28), pady=(0, S(6)))
                    for s in subs:
                        srow = ctk.CTkFrame(sub_container, fg_color="transparent")
                        srow.pack(fill="x", pady=S(1))
                        ctk.CTkLabel(srow, text=f"  {s.icon} {s.name}", anchor="w",
                                     font=ctk.CTkFont(size=S(14)), text_color="#AAA").pack(side="left", padx=S(8), pady=S(3))
                        ctk.CTkButton(srow, text="🗑️", width=S(24), height=S(24), fg_color="#EF4444",
                                      font=ctk.CTkFont(size=S(11)),
                                      command=lambda sid=s.id: self._del_sub(sid)).pack(side="right", padx=S(4), pady=S(2))

    def _open_cdlg(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Nueva categoría")
        dlg.geometry(f"{S(440)}x{S(400)}")
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="➕ Nueva categoría",
                     font=ctk.CTkFont(size=S(20), weight="bold")).pack(pady=(S(16), S(12)))

        f = ctk.CTkFrame(dlg, fg_color="transparent")
        f.pack(fill="x", padx=S(24), pady=(0, S(16)))

        ekw = dict(width=S(370), height=S(36), font=ctk.CTkFont(size=S(14)))
        lk = dict(font=ctk.CTkFont(size=S(14)))

        ctk.CTkLabel(f, text="Nombre:", **lk).pack(anchor="w")
        nv = ctk.StringVar()
        ctk.CTkEntry(f, textvariable=nv, **ekw).pack(pady=(0, S(10)))

        ctk.CTkLabel(f, text="Tipo:", **lk).pack(anchor="w")
        tv = ctk.StringVar(value="expense")
        ctk.CTkOptionMenu(f, variable=tv, values=["expense", "income"],
                          width=S(370), height=S(36), font=ctk.CTkFont(size=S(14)),
                          dropdown_font=ctk.CTkFont(size=S(14))).pack(pady=(0, S(10)))

        ctk.CTkLabel(f, text="Color (hex):", **lk).pack(anchor="w")
        colv = ctk.StringVar(value="#3B82F6")
        ctk.CTkEntry(f, textvariable=colv, **ekw).pack(pady=(0, S(10)))

        ctk.CTkLabel(f, text="Icono (emoji):", **lk).pack(anchor="w")
        iv = ctk.StringVar(value="📁")
        ctk.CTkEntry(f, textvariable=iv, **ekw).pack(pady=(0, S(10)))

        def save():
            try:
                n = nv.get().strip()
                if not n:
                    raise ValueError("Nombre requerido")
                add_category(n, tv.get(), colv.get(), iv.get())
                dlg.destroy()
                self.show_categories()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=dlg)

        ctk.CTkButton(f, text="Crear", fg_color="#10B981", command=save,
                      width=S(370), height=S(42), font=ctk.CTkFont(size=S(15), weight="bold")).pack(pady=(S(6), 0))

    def _del_cat(self, cid):
        if messagebox.askyesno("Confirmar", "¿Eliminar esta categoría y sus subcategorías?", parent=self):
            delete_category(cid)
            self.show_categories()

    def _open_subdlg(self, cat_id):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Nueva subcategoría")
        dlg.geometry(f"{S(400)}x{S(240)}")
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="➕ Nueva subcategoría",
                     font=ctk.CTkFont(size=S(18), weight="bold")).pack(pady=(S(16), S(12)))

        f = ctk.CTkFrame(dlg, fg_color="transparent")
        f.pack(fill="x", padx=S(24), pady=(0, S(16)))

        lk = dict(font=ctk.CTkFont(size=S(14)))

        ctk.CTkLabel(f, text="Nombre:", **lk).pack(anchor="w")
        nv = ctk.StringVar()
        ctk.CTkEntry(f, textvariable=nv, width=S(340), height=S(36),
                     font=ctk.CTkFont(size=S(14))).pack(pady=(0, S(10)))

        ctk.CTkLabel(f, text="Icono (emoji):", **lk).pack(anchor="w")
        iv = ctk.StringVar(value="📁")
        ctk.CTkEntry(f, textvariable=iv, width=S(340), height=S(36),
                     font=ctk.CTkFont(size=S(14))).pack(pady=(0, S(10)))

        def save():
            try:
                n = nv.get().strip()
                if not n:
                    raise ValueError("Nombre requerido")
                add_subcategory(cat_id, n, iv.get())
                dlg.destroy()
                self.show_categories()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=dlg)

        ctk.CTkButton(f, text="Crear", fg_color="#10B981", command=save,
                      width=S(340), height=S(38), font=ctk.CTkFont(size=S(14), weight="bold")).pack()

    def _del_sub(self, sid):
        if messagebox.askyesno("Confirmar", "¿Eliminar esta subcategoría?", parent=self):
            delete_subcategory(sid)
            self.show_categories()


def main():
    init_db()
    apply_custom_theme()
    app = BudgetApp()
    app.mainloop()


if __name__ == '__main__':
    main()
