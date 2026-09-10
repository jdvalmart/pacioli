#!/usr/bin/env python3
"""Vista de Categorías."""

import customtkinter as ctk
from tkinter import messagebox

from theme import (
    font, btn_primary, btn_danger, card, styled_tabs,
    BG, SURFACE, CARD, CARD_HOVER, BORDER, ACCENT, GREEN, RED, TEXT, TEXT_SEC
)
from database import (
    get_categories, add_category, delete_category,
    get_subcategories, add_subcategory, delete_subcategory
)
from utils import S, invalidate_cat_cache


def show_categories(app):
    """Renderiza la vista de categorías."""
    app._hl(4)
    app._view = lambda: show_categories(app)
    app._rerender_on_resize = False
    app._clear()
    app._title("⚙️ Categorías")

    tb = ctk.CTkFrame(app.main, fg_color="transparent")
    tb.grid(row=1, column=0, sticky="ew", padx=S(24), pady=(0, S(8)))
    btn_primary(tb, "➕ Nueva categoría", lambda: _open_cdlg(app), S(220), S(38)).pack(side="left")

    tabs = styled_tabs(app.main)
    tabs.grid(row=2, column=0, sticky="nsew", padx=S(24), pady=(0, S(12)))
    app.main.grid_rowconfigure(2, weight=1)

    t1 = tabs.add("💸 Gastos")
    t2 = tabs.add("💰 Ingresos")

    for container, ct in [(t1, 'expense'), (t2, 'income')]:
        cats = get_categories(ct)
        if not cats:
            ctk.CTkLabel(container, text="No hay categorías", text_color=TEXT_SEC,
                         font=font(S(13))).pack(pady=S(20))
            continue
        for c in cats:
            cat_frame = card(container)
            cat_frame.pack(fill="x", pady=S(3), padx=S(8))

            row = ctk.CTkFrame(cat_frame, fg_color="transparent")
            row.pack(fill="x")
            ctk.CTkLabel(row, text=f"{c.icon}  {c.name}", anchor="w",
                         font=font(S(15))).pack(side="left", padx=S(10), pady=S(10))
            ctk.CTkFrame(row, width=S(18), height=S(18),
                         fg_color=c.color, corner_radius=S(4)).pack(side="left", padx=S(8))
            ctk.CTkButton(row, text="+ Sub", width=S(56), height=S(26), fg_color=ACCENT,
                          hover_color="#4C9AFF", font=font(S(11)),
                          command=lambda cid=c.id: _open_subdlg(app, cid)).pack(side="right", padx=(0, S(4)), pady=S(6))
            ctk.CTkButton(row, text="🗑️", width=S(26), height=S(26), fg_color=RED,
                          hover_color="#DA3633", font=font(S(11)),
                          command=lambda cid=c.id: _del_cat(app, cid)).pack(
                side="right", padx=S(4), pady=S(6))

            subs = get_subcategories(c.id)
            if subs:
                sub_container = ctk.CTkFrame(cat_frame, fg_color="transparent")
                sub_container.pack(fill="x", padx=S(28), pady=(0, S(6)))
                for s in subs:
                    srow = ctk.CTkFrame(sub_container, fg_color="transparent")
                    srow.pack(fill="x", pady=S(1))
                    ctk.CTkLabel(srow, text=f"  {s.icon} {s.name}", anchor="w",
                                 font=font(S(13)), text_color=TEXT_SEC).pack(side="left", padx=S(8), pady=S(3))
                    ctk.CTkButton(srow, text="🗑️", width=S(22), height=S(22), fg_color=RED,
                                  hover_color="#DA3633", font=font(S(10)),
                                  command=lambda sid=s.id: _del_sub(app, sid)).pack(side="right", padx=S(4), pady=S(2))


def _open_cdlg(app):
    """Abre diálogo de nueva categoría."""
    dlg = ctk.CTkToplevel(app)
    dlg.title("Nueva categoría")
    dlg.geometry(f"{S(440)}x{S(380)}")
    dlg.transient(app)
    dlg.grab_set()

    ctk.CTkLabel(dlg, text="➕ Nueva categoría",
                 font=font(S(18), "bold")).pack(pady=(S(16), S(12)))

    f = ctk.CTkFrame(dlg, fg_color="transparent")
    f.pack(fill="x", padx=S(24), pady=(0, S(16)))

    ekw = dict(width=S(370), height=S(36), font=font(S(13)),
               fg_color=CARD, border_color=BORDER)
    lk = dict(font=font(S(13)))

    ctk.CTkLabel(f, text="Nombre:", **lk).pack(anchor="w")
    nv = ctk.StringVar()
    ctk.CTkEntry(f, textvariable=nv, **ekw).pack(pady=(0, S(8)))

    ctk.CTkLabel(f, text="Tipo:", **lk).pack(anchor="w")
    tv = ctk.StringVar(value="expense")
    ctk.CTkOptionMenu(f, variable=tv, values=["Gastos", "Ingresos"],
                      width=S(370), height=S(36), font=font(S(13)), dropdown_font=font(S(13)),
                      fg_color=CARD, button_color=ACCENT).pack(pady=(0, S(8)))

    ctk.CTkLabel(f, text="Color (hex):", **lk).pack(anchor="w")
    colv = ctk.StringVar(value="#3B82F6")
    ctk.CTkEntry(f, textvariable=colv, **ekw).pack(pady=(0, S(8)))

    ctk.CTkLabel(f, text="Icono (emoji):", **lk).pack(anchor="w")
    iv = ctk.StringVar(value="📁")
    ctk.CTkEntry(f, textvariable=iv, **ekw).pack(pady=(0, S(8)))

    _TYPE_MAP = {"Gastos": "expense", "Ingresos": "income"}

    def save():
        try:
            n = nv.get().strip()
            if not n:
                raise ValueError("Nombre requerido")
            cat_type = _TYPE_MAP.get(tv.get(), "expense")
            add_category(n, cat_type, colv.get(), iv.get())
            invalidate_cat_cache()
            dlg.destroy()
            show_categories(app)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=dlg)

    btn_primary(f, "Crear", save, S(370), S(42)).pack(pady=(S(4), 0))


def _open_subdlg(app, cat_id):
    """Abre diálogo de nueva subcategoría."""
    dlg = ctk.CTkToplevel(app)
    dlg.title("Nueva subcategoría")
    dlg.geometry(f"{S(400)}x{S(220)}")
    dlg.transient(app)
    dlg.grab_set()

    ctk.CTkLabel(dlg, text="➕ Nueva subcategoría",
                 font=font(S(16), "bold")).pack(pady=(S(14), S(10)))

    f = ctk.CTkFrame(dlg, fg_color="transparent")
    f.pack(fill="x", padx=S(24), pady=(0, S(14)))

    lk = dict(font=font(S(13)))

    ctk.CTkLabel(f, text="Nombre:", **lk).pack(anchor="w")
    nv = ctk.StringVar()
    ctk.CTkEntry(f, textvariable=nv, width=S(340), height=S(36),
                 font=font(S(13)), fg_color=CARD, border_color=BORDER).pack(pady=(0, S(8)))

    ctk.CTkLabel(f, text="Icono (emoji):", **lk).pack(anchor="w")
    iv = ctk.StringVar(value="📁")
    ctk.CTkEntry(f, textvariable=iv, width=S(340), height=S(36),
                 font=font(S(13)), fg_color=CARD, border_color=BORDER).pack(pady=(0, S(8)))

    def save():
        try:
            n = nv.get().strip()
            if not n:
                raise ValueError("Nombre requerido")
            add_subcategory(cat_id, n, iv.get())
            dlg.destroy()
            show_categories(app)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=dlg)

    btn_primary(f, "Crear", save, S(340), S(38)).pack()


def _del_cat(app, cid):
    if messagebox.askyesno("Confirmar", "¿Eliminar esta categoría y sus subcategorías?", parent=app):
        try:
            delete_category(cid)
        except ValueError as e:
            messagebox.showerror("Error", str(e), parent=app)
            return
        invalidate_cat_cache()
        show_categories(app)


def _del_sub(app, sid):
    if messagebox.askyesno("Confirmar", "¿Eliminar esta subcategoría?", parent=app):
        delete_subcategory(sid)
        show_categories(app)
