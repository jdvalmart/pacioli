#!/usr/bin/env python3
"""Vista de Presupuestos."""

import customtkinter as ctk
from tkinter import messagebox

from theme import (
    font, btn_primary, btn_danger, card,
    BG, SURFACE, CARD, CARD_HOVER, BORDER, ACCENT, GREEN, RED, ORANGE, TEXT, TEXT_SEC
)
from charts import create_budget_chart, create_pie_chart
from database import (
    get_budget_vs_actual, set_budget, delete_budget, get_categories
)
from utils import S, fmt_cop


def show_budgets(app):
    """Renderiza la vista de presupuestos."""
    app._hl(2)
    app._view = lambda: show_budgets(app)
    app._clear()
    app._title(f"🎯 Presupuestos — {app._mh()}")

    tb = ctk.CTkFrame(app.main, fg_color="transparent")
    tb.grid(row=1, column=0, sticky="ew", padx=S(24), pady=(0, S(8)))
    btn_primary(tb, "+ Asignar presupuesto", lambda: _open_bdlg(app), S(220), S(36)).pack(side="left")

    bva = get_budget_vs_actual(app.current_month, app.current_year)

    app._bva_f = ctk.CTkFrame(app.main, fg_color="transparent")
    app._bva_f.grid(row=2, column=0, sticky="nsew", padx=S(24), pady=(0, S(8)))
    app._bva_f.grid_columnconfigure(0, weight=1)
    app._bva_f.grid_columnconfigure(1, weight=1)
    app._bva_f.grid_rowconfigure(0, weight=1)
    app._bva_d = bva
    app.after(100, lambda: _paint_bva(app))

    if bva:
        tf = card(app.main)
        tf.grid(row=3, column=0, sticky="ew", padx=S(24), pady=(0, S(12)))
        ctk.CTkLabel(tf, text="📋 Detalle por categoría",
                     font=font(S(14), "bold")).pack(pady=(S(10), S(6)), padx=S(14), anchor="w")

        hdr = ctk.CTkFrame(tf, fg_color="transparent")
        hdr.pack(fill="x", padx=S(14), pady=(0, S(4)))
        for txt, w in [("Categoría", S(160)), ("Presupuesto", S(120)), ("Real", S(120)),
                       ("Restante", S(120)), ("%", S(60)), ("", S(40))]:
            ctk.CTkLabel(hdr, text=txt, font=font(S(12), "bold"),
                         width=w, anchor="w", text_color=TEXT_SEC).pack(side="left", padx=S(4))

        for i, d in enumerate(bva):
            rc = CARD_HOVER if i % 2 == 0 else CARD
            row = ctk.CTkFrame(tf, fg_color=rc, corner_radius=S(6))
            row.pack(fill="x", pady=S(1), padx=S(14))
            ctk.CTkLabel(row, text=f"{d['icon']} {d['name']}", anchor="w", width=S(160),
                         font=font(S(13))).pack(side="left", padx=S(4), pady=S(7))
            ctk.CTkLabel(row, text=fmt_cop(d['budget']), width=S(120), anchor="w", text_color=ACCENT,
                         font=font(S(13))).pack(side="left", padx=S(4), pady=S(7))
            ctk.CTkLabel(row, text=fmt_cop(d['actual']), width=S(120), anchor="w", text_color=ORANGE,
                         font=font(S(13))).pack(side="left", padx=S(4), pady=S(7))
            rem = d['remaining']
            rc2 = GREEN if rem >= 0 else RED
            ctk.CTkLabel(row, text=fmt_cop(rem), width=S(120), anchor="w", text_color=rc2,
                         font=font(S(13))).pack(side="left", padx=S(4), pady=S(7))
            pct = d['percent']
            pc = GREEN if pct <= 80 else (ORANGE if pct <= 100 else RED)
            ctk.CTkLabel(row, text=f"{pct:.0f}%", width=S(60), anchor="w", text_color=pc,
                         font=font(S(13), "bold")).pack(side="left", padx=S(4), pady=S(7))
            ctk.CTkButton(row, text="🗑️", width=S(28), height=S(28), fg_color=RED,
                          hover_color="#DA3633", font=font(S(12)),
                          command=lambda cid=d['category_id']: _del_b(app, cid)).pack(
                side="right", padx=S(6), pady=S(5))


def _paint_bva(app):
    f = app._bva_f
    f.update_idletasks()
    cw = f.winfo_width()
    ch = f.winfo_height()
    if cw < 100 or ch < 50:
        app.after(100, lambda: _paint_bva(app))
        return
    hw = cw // 2 - S(6)

    for w in f.winfo_children():
        w.destroy()

    img1 = create_budget_chart(app._bva_d, "Presupuesto vs Real", size=(hw, ch))
    c1 = ctk.CTkImage(light_image=img1, dark_image=img1, size=(hw, ch))
    l1 = ctk.CTkLabel(f, image=c1, text="")
    l1.image = c1
    l1.grid(row=0, column=0, sticky="nsew", padx=(0, S(6)))

    pb = [(d['name'], d['budget'], d['color'], d['icon']) for d in app._bva_d if d['budget'] > 0]
    img2 = create_pie_chart(pb, "Presupuesto por categoría", size=(hw, ch))
    c2 = ctk.CTkImage(light_image=img2, dark_image=img2, size=(hw, ch))
    l2 = ctk.CTkLabel(f, image=c2, text="")
    l2.image = c2
    l2.grid(row=0, column=1, sticky="nsew", padx=(S(6), 0))


def _open_bdlg(app):
    """Abre diálogo de asignar presupuesto."""
    dlg = ctk.CTkToplevel(app)
    dlg.title("Asignar presupuesto")
    dlg.geometry(f"{S(440)}x{S(300)}")
    dlg.transient(app)
    dlg.grab_set()

    ctk.CTkLabel(dlg, text="🎯 Asignar presupuesto",
                 font=font(S(18), "bold")).pack(pady=(S(16), S(12)))

    f = ctk.CTkFrame(dlg, fg_color="transparent")
    f.pack(fill="x", padx=S(24), pady=(0, S(16)))

    exp = get_categories('expense')
    cn = [f"{c.icon} {c.name}" for c in exp]
    ci = [c.id for c in exp]

    lk = dict(font=font(S(13)))
    ctk.CTkLabel(f, text="Categoría:", **lk).pack(anchor="w")
    cv = ctk.StringVar(value=cn[0] if cn else "")
    ctk.CTkOptionMenu(f, variable=cv, values=cn, width=S(370), height=S(36),
                      font=font(S(13)), dropdown_font=font(S(13)),
                      fg_color=CARD, button_color=ACCENT).pack(pady=(0, S(12)))

    ctk.CTkLabel(f, text="Presupuesto mensual:", **lk).pack(anchor="w")
    av = ctk.StringVar()
    ctk.CTkEntry(f, textvariable=av, width=S(370), height=S(36),
                 placeholder_text="0", font=font(S(13)),
                 fg_color=CARD, border_color=BORDER).pack(pady=(0, S(14)))

    def save():
        try:
            amt_str = av.get().strip()
            try:
                amt = float(amt_str)
                if amt <= 0:
                    raise ValueError("El monto debe ser mayor a 0")
            except ValueError as e:
                if "must be greater" in str(e):
                    raise
                raise ValueError(f"Monto inválido: '{amt_str}'. Ingrese un número")
            if not cn:
                raise ValueError("No hay categorías disponibles")
            cid = ci[cn.index(cv.get())]
            set_budget(cid, app.current_month, app.current_year, amt)
            dlg.destroy()
            show_budgets(app)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=dlg)

    btn_primary(f, "Guardar", save, S(370), S(42)).pack()


def _del_b(app, cid):
    if messagebox.askyesno("Confirmar", "¿Eliminar este presupuesto?", parent=app):
        delete_budget(cid, app.current_month, app.current_year)
        show_budgets(app)
