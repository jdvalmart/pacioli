#!/usr/bin/env python3
"""Categories view."""

import customtkinter as ctk

from pacioli.ui.tokens import theme, Spacing, FontSize, get_font
from pacioli.ui.components import Button, Card, Modal, ConfirmModal, AlertModal, EmptyState, toasts
from pacioli.ui.theme import styled_tabs
from pacioli.data import (
    get_categories, add_category, delete_category,
    get_subcategories, add_subcategory, delete_subcategory,
    invalidate_cat_cache
)
from pacioli.ui.utils import S


def show_categories(app):
    """Render categories view."""
    colors = theme.colors

    app._hl(4)
    app._view = lambda: show_categories(app)
    app._rerender_on_resize = False
    app._clear()
    app._title("⚙️ Categorías")

    # Toolbar
    tb = ctk.CTkFrame(app.main, fg_color="transparent")
    tb.grid(row=1, column=0, sticky="ew", padx=S(24), pady=(0, S(8)))
    Button(
        tb, text="➕ Nueva categoría", variant="primary", size="md",
        command=lambda: _open_cdlg(app)
    ).pack(side="left")

    # Tabs
    tabs = styled_tabs(app.main)
    tabs.grid(row=2, column=0, sticky="nsew", padx=S(24), pady=(0, S(12)))
    app.main.grid_rowconfigure(2, weight=1)

    t1 = tabs.add("💸 Gastos")
    t2 = tabs.add("💰 Ingresos")

    for container, ct in [(t1, 'expense'), (t2, 'income')]:
        cats = get_categories(ct)
        if not cats:
            EmptyState(
                container,
                icon="📁",
                title="No hay categorías",
                message="Comienza agregando tu primera categoría",
                action_text="+ Nueva categoría",
                action_command=lambda: _open_cdlg(app)
            ).pack(pady=S(20))
            continue

        for c in cats:
            cat_frame = Card(container, variant="elevated")
            cat_frame.pack(fill="x", pady=S(3), padx=S(8))

            row = ctk.CTkFrame(cat_frame.content, fg_color="transparent")
            row.pack(fill="x")
            ctk.CTkLabel(
                row, text=f"{c.icon}  {c.name}", anchor="w",
                font=get_font(FontSize.MD), text_color=colors.TEXT_PRIMARY
            ).pack(side="left", padx=Spacing.SM, pady=Spacing.SM)
            ctk.CTkFrame(
                row, width=S(18), height=S(18),
                fg_color=c.color, corner_radius=Spacing.XS
            ).pack(side="left", padx=S(8))
            Button(
                row, text="+ Sub", variant="secondary", size="sm",
                width=S(56), height=S(26),
                command=lambda cid=c.id: _open_subdlg(app, cid)
            ).pack(side="right", padx=(0, S(4)), pady=S(6))
            Button(
                row, text="🗑️", variant="ghost", size="sm",
                width=S(26), height=S(26),
                command=lambda cid=c.id: _del_cat(app, cid)
            ).pack(side="right", padx=S(4), pady=S(6))

            subs = get_subcategories(c.id)
            if subs:
                sub_container = ctk.CTkFrame(cat_frame.content, fg_color="transparent")
                sub_container.pack(fill="x", padx=S(28), pady=(0, S(6)))
                for s in subs:
                    srow = ctk.CTkFrame(sub_container, fg_color="transparent")
                    srow.pack(fill="x", pady=Spacing.XS)
                    ctk.CTkLabel(
                        srow, text=f"  {s.icon} {s.name}", anchor="w",
                        font=get_font(FontSize.BASE), text_color=colors.TEXT_SECONDARY
                    ).pack(side="left", padx=S(8), pady=S(3))
                    Button(
                        srow, text="🗑️", variant="ghost", size="sm",
                        width=S(22), height=S(22),
                        command=lambda sid=s.id: _del_sub(app, sid)
                    ).pack(side="right", padx=S(4), pady=S(2))


def _open_cdlg(app):
    """Open new category dialog."""
    colors = theme.colors

    modal = Modal(app, title="➕ Nueva categoría", size="sm")

    f = ctk.CTkFrame(modal.content, fg_color="transparent")
    f.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.LG))

    # Name
    ctk.CTkLabel(
        f, text="Nombre:",
        font=get_font(FontSize.BASE), text_color=colors.TEXT_PRIMARY
    ).pack(anchor="w")
    nv = ctk.StringVar()
    ctk.CTkEntry(
        f, textvariable=nv, width=S(370), height=S(36),
        font=get_font(FontSize.BASE),
        fg_color=colors.BG_TERTIARY, border_color=colors.BORDER_DEFAULT
    ).pack(pady=(0, S(8)))

    # Type
    ctk.CTkLabel(
        f, text="Tipo:",
        font=get_font(FontSize.BASE), text_color=colors.TEXT_PRIMARY
    ).pack(anchor="w")
    tv = ctk.StringVar(value="expense")
    ctk.CTkOptionMenu(
        f, variable=tv, values=["Gastos", "Ingresos"],
        width=S(370), height=S(36),
        font=get_font(FontSize.BASE), dropdown_font=get_font(FontSize.BASE),
        fg_color=colors.BG_TERTIARY, button_color=colors.PRIMARY
    ).pack(pady=(0, S(8)))

    # Color
    ctk.CTkLabel(
        f, text="Color (hex):",
        font=get_font(FontSize.BASE), text_color=colors.TEXT_PRIMARY
    ).pack(anchor="w")
    colv = ctk.StringVar(value="#3B82F6")
    ctk.CTkEntry(
        f, textvariable=colv, width=S(370), height=S(36),
        font=get_font(FontSize.BASE),
        fg_color=colors.BG_TERTIARY, border_color=colors.BORDER_DEFAULT
    ).pack(pady=(0, S(8)))

    # Icon
    ctk.CTkLabel(
        f, text="Icono (emoji):",
        font=get_font(FontSize.BASE), text_color=colors.TEXT_PRIMARY
    ).pack(anchor="w")
    iv = ctk.StringVar(value="📁")
    ctk.CTkEntry(
        f, textvariable=iv, width=S(370), height=S(36),
        font=get_font(FontSize.BASE),
        fg_color=colors.BG_TERTIARY, border_color=colors.BORDER_DEFAULT
    ).pack(pady=(0, S(8)))

    _TYPE_MAP = {"Gastos": "expense", "Ingresos": "income"}

    def save():
        try:
            n = nv.get().strip()
            if not n:
                raise ValueError("Nombre requerido")
            cat_type = _TYPE_MAP.get(tv.get(), "expense")
            add_category(n, cat_type, colv.get(), iv.get())
            invalidate_cat_cache()
            modal.close()
            show_categories(app)
            toasts.success(app, "Categoría creada")
        except Exception as e:
            AlertModal(modal, title="Error", message=str(e), variant="error")

    modal.add_action("Cancelar", command=modal.close, variant="secondary", position="right")
    modal.add_action("Crear", command=save, variant="primary", position="right")


def _open_subdlg(app, cat_id):
    """Open new subcategory dialog."""
    colors = theme.colors

    modal = Modal(app, title="➕ Nueva subcategoría", size="sm")

    f = ctk.CTkFrame(modal.content, fg_color="transparent")
    f.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.LG))

    # Name
    ctk.CTkLabel(
        f, text="Nombre:",
        font=get_font(FontSize.BASE), text_color=colors.TEXT_PRIMARY
    ).pack(anchor="w")
    nv = ctk.StringVar()
    ctk.CTkEntry(
        f, textvariable=nv, width=S(340), height=S(36),
        font=get_font(FontSize.BASE),
        fg_color=colors.BG_TERTIARY, border_color=colors.BORDER_DEFAULT
    ).pack(pady=(0, S(8)))

    # Icon
    ctk.CTkLabel(
        f, text="Icono (emoji):",
        font=get_font(FontSize.BASE), text_color=colors.TEXT_PRIMARY
    ).pack(anchor="w")
    iv = ctk.StringVar(value="📁")
    ctk.CTkEntry(
        f, textvariable=iv, width=S(340), height=S(36),
        font=get_font(FontSize.BASE),
        fg_color=colors.BG_TERTIARY, border_color=colors.BORDER_DEFAULT
    ).pack(pady=(0, S(8)))

    def save():
        try:
            n = nv.get().strip()
            if not n:
                raise ValueError("Nombre requerido")
            add_subcategory(cat_id, n, iv.get())
            modal.close()
            show_categories(app)
            toasts.success(app, "Subcategoría creada")
        except Exception as e:
            AlertModal(modal, title="Error", message=str(e), variant="error")

    modal.add_action("Cancelar", command=modal.close, variant="secondary", position="right")
    modal.add_action("Crear", command=save, variant="primary", position="right")


def _del_cat(app, cid):
    """Delete category with confirmation."""
    def on_confirm():
        try:
            delete_category(cid)
            invalidate_cat_cache()
            show_categories(app)
            toasts.success(app, "Categoría eliminada")
        except ValueError as e:
            AlertModal(app, title="Error", message=str(e), variant="error")

    ConfirmModal(
        app,
        title="Confirmar",
        message="¿Eliminar esta categoría y sus subcategorías?",
        on_confirm=on_confirm,
        danger=True
    )


def _del_sub(app, sid):
    """Delete subcategory with confirmation."""
    def on_confirm():
        delete_subcategory(sid)
        show_categories(app)
        toasts.success(app, "Subcategoría eliminada")

    ConfirmModal(
        app,
        title="Confirmar",
        message="¿Eliminar esta subcategoría?",
        on_confirm=on_confirm,
        danger=True
    )
