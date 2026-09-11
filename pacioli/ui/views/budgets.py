#!/usr/bin/env python3
"""Budgets view."""

import customtkinter as ctk

from pacioli.ui.tokens import theme, Spacing, FontSize, get_font
from pacioli.ui.components import Button, Card, Modal, ConfirmModal, AlertModal, EmptyState, toasts
from pacioli.ui.charts import create_budget_chart, create_pie_chart
from pacioli.data import (
    get_budget_vs_actual, set_budget, delete_budget, get_categories
)
from pacioli.core.money import fmt_cop, parse_amount
from pacioli.ui.utils import S


def show_budgets(app):
    """Render budgets view."""
    colors = theme.colors

    app._hl(2)
    app._view = lambda: show_budgets(app)
    app._rerender_on_resize = True
    app._clear()
    app._title(f"🎯 Presupuestos — {app._mh()}")

    # Toolbar
    tb = ctk.CTkFrame(app.main, fg_color="transparent")
    tb.grid(row=1, column=0, sticky="ew", padx=S(24), pady=(0, S(8)))
    Button(
        tb, text="+ Asignar presupuesto", variant="primary", size="md",
        command=lambda: _open_bdlg(app)
    ).pack(side="left")

    bva = get_budget_vs_actual(app.current_month, app.current_year)

    # Charts container
    app._bva_f = ctk.CTkFrame(app.main, fg_color="transparent")
    app._bva_f.grid(row=2, column=0, sticky="nsew", padx=S(24), pady=(0, S(8)))
    app._bva_f.grid_columnconfigure(0, weight=1)
    app._bva_f.grid_columnconfigure(1, weight=1)
    app._bva_f.grid_rowconfigure(0, weight=1)
    app._bva_d = bva
    app.after(100, lambda: _paint_bva(app))

    if not bva:
        EmptyState(
            app.main,
            icon="🎯",
            title="No hay presupuestos este mes",
            message="Comienza asignando presupuestos a tus categorías de gastos",
            action_text="+ Asignar presupuesto",
            action_command=lambda: _open_bdlg(app)
        ).grid(row=3, column=0, sticky="ew", padx=S(24), pady=(0, S(12)))
        return

    # Detail card
    tf = Card(app.main, title="📋 Detalle por categoría", variant="elevated")
    tf.grid(row=3, column=0, sticky="ew", padx=S(24), pady=(0, S(12)))

    # Header
    hdr = ctk.CTkFrame(tf.content, fg_color="transparent")
    hdr.pack(fill="x", pady=(0, S(4)))
    for txt, w in [("Categoría", S(160)), ("Presupuesto", S(120)), ("Real", S(120)),
                   ("Restante", S(120)), ("%", S(60)), ("", S(40))]:
        ctk.CTkLabel(
            hdr, text=txt, font=get_font(FontSize.SM, "bold"),
            width=w, anchor="w", text_color=colors.TEXT_SECONDARY
        ).pack(side="left", padx=S(4))

    # Rows
    for i, d in enumerate(bva):
        rc = colors.BG_HOVER if i % 2 == 0 else colors.BG_TERTIARY
        row = ctk.CTkFrame(tf.content, fg_color=rc, corner_radius=Spacing.SM)
        row.pack(fill="x", pady=Spacing.XS, padx=Spacing.MD)
        ctk.CTkLabel(
            row, text=f"{d['icon']} {d['name']}", anchor="w", width=S(160),
            font=get_font(FontSize.BASE), text_color=colors.TEXT_PRIMARY
        ).pack(side="left", padx=S(4), pady=S(7))
        ctk.CTkLabel(
            row, text=fmt_cop(d['budget']), width=S(120), anchor="w", text_color=colors.PRIMARY,
            font=get_font(FontSize.BASE)
        ).pack(side="left", padx=S(4), pady=S(7))
        ctk.CTkLabel(
            row, text=fmt_cop(d['actual']), width=S(120), anchor="w", text_color=colors.WARNING,
            font=get_font(FontSize.BASE)
        ).pack(side="left", padx=S(4), pady=S(7))
        rem = d['remaining']
        rc2 = colors.SUCCESS if rem >= 0 else colors.ERROR
        ctk.CTkLabel(
            row, text=fmt_cop(rem), width=S(120), anchor="w", text_color=rc2,
            font=get_font(FontSize.BASE)
        ).pack(side="left", padx=S(4), pady=S(7))
        pct = d['percent']
        pc = colors.SUCCESS if pct <= 80 else (colors.WARNING if pct <= 100 else colors.ERROR)
        ctk.CTkLabel(
            row, text=f"{pct:.0f}%", width=S(60), anchor="w", text_color=pc,
            font=get_font(FontSize.BASE, "bold")
        ).pack(side="left", padx=S(4), pady=S(7))
        Button(
            row, text="🗑️", variant="ghost", size="sm", width=S(28), height=S(28),
            command=lambda cid=d['category_id']: _del_b(app, cid)
        ).pack(side="right", padx=S(6), pady=S(5))


def _paint_bva(app):
    """Paint budget charts."""
    f = app._bva_f
    if not f.winfo_exists():
        return
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
    """Open budget assignment dialog."""
    colors = theme.colors

    modal = Modal(app, title="🎯 Asignar presupuesto", size="sm")

    f = ctk.CTkFrame(modal.content, fg_color="transparent")
    f.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.LG))

    exp = get_categories('expense')
    cn = [f"{c.icon} {c.name}" for c in exp]
    ci = [c.id for c in exp]

    ctk.CTkLabel(
        f, text="Categoría:",
        font=get_font(FontSize.BASE), text_color=colors.TEXT_PRIMARY
    ).pack(anchor="w")
    cv = ctk.StringVar(value=cn[0] if cn else "")
    ctk.CTkOptionMenu(
        f, variable=cv, values=cn, width=S(370), height=S(36),
        font=get_font(FontSize.BASE), dropdown_font=get_font(FontSize.BASE),
        fg_color=colors.BG_TERTIARY, button_color=colors.PRIMARY
    ).pack(pady=(0, Spacing.LG))

    ctk.CTkLabel(
        f, text="Presupuesto mensual:",
        font=get_font(FontSize.BASE), text_color=colors.TEXT_PRIMARY
    ).pack(anchor="w")
    av = ctk.StringVar()
    ctk.CTkEntry(
        f, textvariable=av, width=S(370), height=S(36),
        placeholder_text="0", font=get_font(FontSize.BASE),
        fg_color=colors.BG_TERTIARY, border_color=colors.BORDER_DEFAULT
    ).pack(pady=(0, Spacing.LG))

    def save():
        try:
            amt = parse_amount(av.get())
            if amt <= 0:
                raise ValueError("El monto debe ser mayor a 0")
            if not cn:
                raise ValueError("No hay categorías disponibles")
            cid = ci[cn.index(cv.get())]
            set_budget(cid, app.current_month, app.current_year, amt)
            modal.close()
            show_budgets(app)
            toasts.success(app, "Presupuesto asignado")
        except Exception as e:
            AlertModal(modal, title="Error", message=str(e), variant="error")

    modal.add_action("Cancelar", command=modal.close, variant="secondary", position="right")
    modal.add_action("Guardar", command=save, variant="primary", position="right")


def _del_b(app, cid):
    """Delete budget with confirmation."""
    def on_confirm():
        delete_budget(cid, app.current_month, app.current_year)
        show_budgets(app)
        toasts.success(app, "Presupuesto eliminado")

    ConfirmModal(
        app,
        title="Confirmar",
        message="¿Eliminar este presupuesto?",
        on_confirm=on_confirm,
        danger=True
    )
