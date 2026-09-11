#!/usr/bin/env python3
"""Transactions view."""

import customtkinter as ctk
from datetime import date
import threading

from pacioli.ui.tokens import theme, Spacing, FontSize, get_font
from pacioli.ui.components import (
    Button, Card, Modal, ConfirmModal, AlertModal, EmptyState, SearchEmptyState, toasts
)
from pacioli.data import (
    get_transactions, add_transaction, update_transaction, delete_transaction,
    get_categories, get_subcategories, get_desc_learnings_context,
    export_transactions_csv, lookup_cat, invalidate_cat_cache
)
from pacioli.services.ai import ai_service
from pacioli.core.money import fmt_cop, parse_amount
from pacioli.ui.utils import S
from pacioli.core.logging_config import logger


def show_transactions(app):
    """Render transactions view."""
    colors = theme.colors

    app._hl(1)
    app._view = lambda: show_transactions(app)
    app._rerender_on_resize = False
    app._clear()
    app._title(f"💸 Transacciones — {app._mh()}")

    # Toolbar
    tb = ctk.CTkFrame(app.main, fg_color="transparent")
    tb.grid(row=1, column=0, sticky="ew", padx=S(24), pady=(0, S(8)))

    Button(
        tb, text="+ Nuevo gasto", variant="danger", size="md",
        command=lambda: _open_tx(app, 'expense')
    ).pack(side="left", padx=(0, S(8)))

    Button(
        tb, text="+ Nuevo ingreso", variant="success", size="md",
        command=lambda: _open_tx(app, 'income')
    ).pack(side="left")

    Button(
        tb, text="📥 Exportar CSV", variant="secondary", size="md",
        command=lambda: _export_csv(app)
    ).pack(side="left", padx=(S(8), 0))

    # Search input
    search_var = ctk.StringVar()

    # List frame
    lf = ctk.CTkScrollableFrame(app.main, fg_color="transparent")
    lf.grid(row=2, column=0, sticky="nsew", padx=S(24), pady=(0, S(12)))

    # Header
    hdr = ctk.CTkFrame(lf, fg_color="transparent")
    hdr.pack(fill="x", pady=(0, S(4)))
    for txt, w in [("Fecha", S(110)), ("Categoría", S(220)), ("Descripción", 0), ("Monto", S(130)), ("", S(80))]:
        kw = dict(font=get_font(FontSize.SM, "bold"), anchor="w", text_color=colors.TEXT_SECONDARY)
        if w:
            kw["width"] = w
        ctk.CTkLabel(hdr, text=txt, **kw).pack(side="left", padx=S(8))
    ctk.CTkFrame(lf, height=1, fg_color=colors.BORDER_SUBTLE).pack(fill="x", pady=(0, S(4)))

    txns = get_transactions(app.current_month, app.current_year)
    if not txns:
        EmptyState(
            lf,
            icon="💸",
            title="No hay transacciones este mes",
            message="Comienza agregando tu primera transacción",
            action_text="+ Nueva transacción",
            action_command=lambda: _open_tx(app, 'expense')
        ).pack(pady=S(30))
        return

    rows = ctk.CTkFrame(lf, fg_color="transparent")
    rows.pack(fill="x")

    def _render():
        for w in rows.winfo_children():
            w.destroy()
        q = search_var.get().lower().strip()
        shown = 0
        for t in txns:
            icon, color, cn, ct_ = lookup_cat(t.category_id)
            cat_label = f"{icon} {cn}"
            if t.subcategory_name:
                cat_label += f" → {t.subcategory_name}"
            searchable = f"{t.date} {cn} {t.subcategory_name or ''} {t.description or ''} {fmt_cop(t.amount)}".lower()
            if q and q not in searchable:
                continue
            shown += 1
            row = ctk.CTkFrame(rows, corner_radius=Spacing.SM, fg_color=colors.BG_TERTIARY)
            row.pack(fill="x", pady=Spacing.XS)
            dlabel = f"🔁 {t.date}" if (t.is_recurring or t.generated_from) else str(t.date)
            ctk.CTkLabel(
                row, text=dlabel, width=S(110), anchor="w",
                font=get_font(FontSize.BASE), text_color=colors.TEXT_PRIMARY
            ).pack(side="left", padx=S(8), pady=S(8))
            ctk.CTkLabel(
                row, text=cat_label, width=S(220), anchor="w", text_color=color,
                font=get_font(FontSize.BASE)
            ).pack(side="left", padx=S(8), pady=S(8))
            ctk.CTkLabel(
                row, text=t.description[:40] if t.description else "—", anchor="w",
                text_color=colors.TEXT_SECONDARY, font=get_font(FontSize.SM)
            ).pack(side="left", padx=S(8), pady=S(8), expand=True, fill="x")
            ac = colors.SUCCESS if ct_ == 'income' else colors.ERROR
            pf = "+" if ct_ == 'income' else "-"
            ctk.CTkLabel(
                row, text=f"{pf}{fmt_cop(t.amount)}", width=S(130), anchor="e",
                text_color=ac, font=get_font(FontSize.BASE, "bold")
            ).pack(side="left", padx=S(8), pady=S(8))
            bf = ctk.CTkFrame(row, fg_color="transparent")
            bf.pack(side="right", padx=S(8), pady=S(5))
            Button(
                bf, text="✏️", variant="ghost", size="sm", width=S(28), height=S(28),
                command=lambda tt=t, ct=ct_: _open_tx(app, ct, tt)
            ).pack(side="left", padx=S(2))
            Button(
                bf, text="🗑️", variant="ghost", size="sm", width=S(28), height=S(28),
                command=lambda tid=t.id: _del_tx(app, tid)
            ).pack(side="left", padx=S(2))

        if shown == 0:
            SearchEmptyState(
                rows,
                query=q,
                on_clear=lambda: search_var.set("")
            ).pack(pady=S(20))

    # Search input
    search_entry = ctk.CTkEntry(
        tb, textvariable=search_var, width=S(200), height=S(36),
        placeholder_text="🔍 Buscar...",
        font=get_font(FontSize.BASE),
        fg_color=colors.BG_TERTIARY,
        border_color=colors.BORDER_DEFAULT
    )
    search_entry.pack(side="right")

    debounce = {"job": None}

    def _on_search(*_):
        if debounce["job"]:
            app.after_cancel(debounce["job"])
        debounce["job"] = app.after(150, _render)

    search_var.trace_add("write", _on_search)
    _render()


def _open_tx(app, cat_type='expense', existing=None):
    """Open new/edit transaction dialog."""
    colors = theme.colors

    modal = Modal(app, title="✏️ Editar" if existing else "➕ Nueva transacción", size="md")

    f = ctk.CTkFrame(modal.content, fg_color="transparent")
    f.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.LG))

    # Date
    ctk.CTkLabel(
        f, text="Fecha (YYYY-MM-DD):",
        font=get_font(FontSize.BASE), text_color=colors.TEXT_PRIMARY
    ).pack(anchor="w")
    dv = ctk.StringVar(value=existing.date if existing else date.today().isoformat())
    ctk.CTkEntry(
        f, textvariable=dv, width=S(380), height=S(36),
        font=get_font(FontSize.BASE),
        fg_color=colors.BG_TERTIARY, border_color=colors.BORDER_DEFAULT
    ).pack(pady=(0, S(8)))

    # Category
    cats = get_categories(cat_type)
    cnames = [f"{c.icon} {c.name}" for c in cats]
    cids = [c.id for c in cats]
    ctk.CTkLabel(
        f, text="Categoría:",
        font=get_font(FontSize.BASE), text_color=colors.TEXT_PRIMARY
    ).pack(anchor="w")
    cv = ctk.StringVar(value=cnames[0] if cnames else "")
    cat_menu = ctk.CTkOptionMenu(
        f, variable=cv, values=cnames, width=S(380), height=S(36),
        font=get_font(FontSize.BASE), dropdown_font=get_font(FontSize.BASE),
        fg_color=colors.BG_TERTIARY, button_color=colors.PRIMARY, button_hover_color=colors.PRIMARY_HOVER
    )
    cat_menu.pack(pady=(0, S(8)))

    # Subcategory
    ctk.CTkLabel(
        f, text="Subcategoría (opcional):",
        font=get_font(FontSize.BASE), text_color=colors.TEXT_PRIMARY
    ).pack(anchor="w")
    sub_var = ctk.StringVar(value="Ninguna")
    sub_menu_widget = ctk.CTkOptionMenu(
        f, variable=sub_var, values=["Ninguna"],
        width=S(380), height=S(36),
        font=get_font(FontSize.BASE), dropdown_font=get_font(FontSize.BASE),
        fg_color=colors.BG_TERTIARY, button_color=colors.PRIMARY, button_hover_color=colors.PRIMARY_HOVER
    )
    sub_menu_widget.pack(pady=(0, S(8)))

    all_subs = {c.id: get_subcategories(c.id) for c in cats}
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

    # Amount
    ctk.CTkLabel(
        f, text="Monto:",
        font=get_font(FontSize.BASE), text_color=colors.TEXT_PRIMARY
    ).pack(anchor="w")
    av = ctk.StringVar(value=str(existing.amount) if existing else "")
    ctk.CTkEntry(
        f, textvariable=av, width=S(380), height=S(36),
        font=get_font(FontSize.BASE),
        fg_color=colors.BG_TERTIARY, border_color=colors.BORDER_DEFAULT
    ).pack(pady=(0, S(8)))

    # Description
    ctk.CTkLabel(
        f, text="Descripción:",
        font=get_font(FontSize.BASE), text_color=colors.TEXT_PRIMARY
    ).pack(anchor="w")
    descv = ctk.StringVar(value=existing.description if existing else "")
    desc_row = ctk.CTkFrame(f, fg_color="transparent")
    desc_row.pack(fill="x", pady=(0, S(8)))
    ctk.CTkEntry(
        desc_row, textvariable=descv, width=S(300), height=S(36),
        font=get_font(FontSize.BASE),
        fg_color=colors.BG_TERTIARY, border_color=colors.BORDER_DEFAULT
    ).pack(side="left")

    _last_ai_desc = {"value": None, "category": None, "subcategory": None}

    def _ai_desc():
        try:
            amt = parse_amount(av.get())
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
            # Prepare context for AI
            context = learnings_ctx if learnings_ctx else ""
            if sub_name:
                context = f"{context}\nSubcategory: {sub_name}" if context else f"Subcategory: {sub_name}"
            response = ai_service.generate_description(cat_name, float(amt), context)
            app.after(0, lambda: _set_desc(response))
        threading.Thread(target=_run, daemon=True).start()

    def _set_desc(response):
        btn_ai.configure(state="normal", text="✨ IA")
        if response.success:
            result = response.text
            descv.set(result)
            _last_ai_desc["value"] = result
        else:
            AlertModal(
                modal,
                title="IA",
                message=f"No se pudo conectar con Ollama.\n{response.error}",
                variant="warning"
            )

    btn_ai = Button(
        desc_row, text="✨ IA", variant="secondary", size="sm",
        width=S(60), height=S(36), command=_ai_desc
    )
    btn_ai.pack(side="right", padx=(S(6), 0))

    # Recurring
    rv = ctk.BooleanVar(value=bool(existing.is_recurring) if existing else False)
    ctk.CTkCheckBox(
        f, text="Recurrente", variable=rv,
        font=get_font(FontSize.BASE), fg_color=colors.PRIMARY
    ).pack(anchor="w", pady=(0, S(4)))

    dayv = ctk.StringVar(value=str(existing.recurring_day) if existing and existing.recurring_day else str(date.today().day))
    ctk.CTkLabel(
        f, text="Día del mes:",
        font=get_font(FontSize.BASE), text_color=colors.TEXT_PRIMARY
    ).pack(anchor="w")
    ctk.CTkEntry(
        f, textvariable=dayv, width=S(380), height=S(36),
        font=get_font(FontSize.BASE),
        fg_color=colors.BG_TERTIARY, border_color=colors.BORDER_DEFAULT
    ).pack(pady=(0, S(8)))

    def save():
        try:
            d_str = dv.get().strip()
            try:
                d = date.fromisoformat(d_str)
            except ValueError:
                raise ValueError(f"Fecha inválida: '{d_str}'. Use formato YYYY-MM-DD")

            amt = parse_amount(av.get())
            if amt <= 0:
                raise ValueError("El monto debe ser mayor a 0")

            if not cnames:
                raise ValueError("No hay categorías disponibles")
            cid = cids[cnames.index(cv.get())]
            desc = descv.get()
            rec = rv.get()
            rday = None
            if rec:
                try:
                    rday = int(dayv.get())
                except ValueError:
                    rday = 0
                if not 1 <= rday <= 31:
                    raise ValueError("Día del mes inválido: use un número entre 1 y 31")
            sub_sel = sub_var.get()
            sid = sub_ids_map.get(sub_sel) if sub_sel != "Ninguna" else None

            if _last_ai_desc["value"] and desc != _last_ai_desc["value"]:
                from pacioli.data.database import save_desc_learning
                save_desc_learning(
                    _last_ai_desc.get("category", ""),
                    _last_ai_desc.get("subcategory", ""),
                    _last_ai_desc["value"], desc
                )

            if existing:
                update_transaction(existing.id, d, amt, cid, desc, rec, rday, sid)
            else:
                add_transaction(d, amt, cid, desc, rec, rday, sid)
            modal.close()
            show_transactions(app)
            toasts.success(app, "Transacción guardada")
        except Exception as e:
            AlertModal(modal, title="Error", message=str(e), variant="error")

    modal.add_action("Cancelar", command=modal.close, variant="secondary", position="right")
    modal.add_action("Guardar", command=save, variant="primary", position="right")


def _del_tx(app, tid):
    """Delete transaction with confirmation."""
    def on_confirm():
        delete_transaction(tid)
        show_transactions(app)
        toasts.success(app, "Transacción eliminada")

    ConfirmModal(
        app,
        title="Confirmar",
        message="¿Eliminar esta transacción?",
        on_confirm=on_confirm,
        danger=True
    )


def _export_csv(app):
    """Export transactions to CSV."""
    from tkinter import filedialog
    filepath = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV", "*.csv")],
        initialfile=f"transacciones_{app.current_month:02d}_{app.current_year}.csv",
        parent=app
    )
    if filepath:
        try:
            export_transactions_csv(app.current_month, app.current_year, filepath)
            toasts.success(app, f"Transacciones exportadas a {filepath}")
        except Exception as e:
            AlertModal(app, title="Error", message=str(e), variant="error")
