#!/usr/bin/env python3
"""Vista de Transacciones."""

import customtkinter as ctk
from tkinter import messagebox
from datetime import date
import threading

from theme import (
    font, btn_primary, btn_danger, card,
    BG, SURFACE, CARD, CARD_HOVER, BORDER, ACCENT, GREEN, RED, PURPLE, TEXT, TEXT_SEC
)
from database import (
    get_transactions, add_transaction, update_transaction, delete_transaction,
    get_categories, get_subcategories, get_desc_learnings_context,
    export_transactions_csv, auto_backup
)
from ai import generate_description
from utils import S, fmt_cop, lookup_cat, invalidate_cat_cache, parse_amount


def show_transactions(app):
    """Renderiza la vista de transacciones."""
    app._hl(1)
    app._view = lambda: show_transactions(app)
    app._rerender_on_resize = False
    app._clear()
    app._title(f"💸 Transacciones — {app._mh()}")

    tb = ctk.CTkFrame(app.main, fg_color="transparent")
    tb.grid(row=1, column=0, sticky="ew", padx=S(24), pady=(0, S(8)))
    ctk.CTkButton(tb, text="+ Nuevo gasto", width=S(160), height=S(36),
                  fg_color=RED, hover_color="#DA3633",
                  font=font(S(13), "bold"),
                  command=lambda: _open_tx(app, 'expense')).pack(side="left", padx=(0, S(8)))
    ctk.CTkButton(tb, text="+ Nuevo ingreso", width=S(160), height=S(36),
                  fg_color=GREEN, hover_color="#2EA043",
                  font=font(S(13), "bold"),
                  command=lambda: _open_tx(app, 'income')).pack(side="left")

    ctk.CTkButton(tb, text="📥 Exportar CSV", width=S(140), height=S(36),
                  fg_color=ACCENT, hover_color="#4C9AFF",
                  font=font(S(13), "bold"),
                  command=lambda: _export_csv(app)).pack(side="left", padx=(S(8), 0))

    search_var = ctk.StringVar()
    search_entry = ctk.CTkEntry(tb, textvariable=search_var, width=S(200), height=S(36),
                                placeholder_text="🔍 Buscar...",
                                font=font(S(13)), fg_color=CARD, border_color=BORDER)
    search_entry.pack(side="right")

    lf = ctk.CTkScrollableFrame(app.main, fg_color="transparent")
    lf.grid(row=2, column=0, sticky="nsew", padx=S(24), pady=(0, S(12)))

    hdr = ctk.CTkFrame(lf, fg_color="transparent")
    hdr.pack(fill="x", pady=(0, S(4)))
    for txt, w in [("Fecha", S(110)), ("Categoría", S(220)), ("Descripción", 0), ("Monto", S(130)), ("", S(80))]:
        kw = dict(font=font(S(12), "bold"), anchor="w", text_color=TEXT_SEC)
        if w:
            kw["width"] = w
        ctk.CTkLabel(hdr, text=txt, **kw).pack(side="left", padx=S(8))
    ctk.CTkFrame(lf, height=1, fg_color=BORDER).pack(fill="x", pady=(0, S(4)))

    txns = get_transactions(app.current_month, app.current_year)
    if not txns:
        ctk.CTkLabel(lf, text="No hay transacciones este mes",
                     text_color=TEXT_SEC, font=font(S(13))).pack(pady=S(30))
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
            row = ctk.CTkFrame(rows, corner_radius=S(6), fg_color=CARD)
            row.pack(fill="x", pady=S(2))
            dlabel = f"🔁 {t.date}" if (t.is_recurring or t.generated_from) else str(t.date)
            ctk.CTkLabel(row, text=dlabel, width=S(110), anchor="w",
                         font=font(S(13))).pack(side="left", padx=S(8), pady=S(8))
            ctk.CTkLabel(row, text=cat_label, width=S(220), anchor="w", text_color=color,
                         font=font(S(13))).pack(side="left", padx=S(8), pady=S(8))
            ctk.CTkLabel(row, text=t.description[:40] if t.description else "—", anchor="w",
                         text_color=TEXT_SEC, font=font(S(12))).pack(
                side="left", padx=S(8), pady=S(8), expand=True, fill="x")
            ac = GREEN if ct_ == 'income' else RED
            pf = "+" if ct_ == 'income' else "-"
            ctk.CTkLabel(row, text=f"{pf}{fmt_cop(t.amount)}", width=S(130), anchor="e",
                         text_color=ac, font=font(S(13), "bold")).pack(
                side="left", padx=S(8), pady=S(8))
            bf = ctk.CTkFrame(row, fg_color="transparent")
            bf.pack(side="right", padx=S(8), pady=S(5))
            ctk.CTkButton(bf, text="✏️", width=S(28), height=S(28), fg_color=ACCENT,
                          hover_color="#4C9AFF", font=font(S(12)),
                          command=lambda tt=t, ct=ct_: _open_tx(app, ct, tt)).pack(side="left", padx=S(2))
            ctk.CTkButton(bf, text="🗑️", width=S(28), height=S(28), fg_color=RED,
                          hover_color="#DA3633", font=font(S(12)),
                          command=lambda tid=t.id: _del_tx(app, tid)).pack(side="left", padx=S(2))
        if shown == 0:
            ctk.CTkLabel(rows, text=f'No se encontró "{q}"',
                         text_color=TEXT_SEC, font=font(S(13))).pack(pady=S(20))

    debounce = {"job": None}

    def _on_search(*_):
        if debounce["job"]:
            app.after_cancel(debounce["job"])
        debounce["job"] = app.after(150, _render)

    search_var.trace_add("write", _on_search)
    _render()


def _open_tx(app, cat_type='expense', existing=None):
    """Abre diálogo de nueva/editar transacción."""
    dlg = ctk.CTkToplevel(app)
    dlg.title("Editar" if existing else "Nueva transacción")
    dlg.geometry(f"{S(460)}x{S(580)}")
    dlg.transient(app)
    dlg.grab_set()

    ctk.CTkLabel(dlg, text="✏️ Editar" if existing else "➕ Nueva",
                 font=font(S(18), "bold")).pack(pady=(S(16), S(12)))

    f = ctk.CTkFrame(dlg, fg_color="transparent")
    f.pack(fill="x", padx=S(24), pady=(0, S(16)))

    ekw = dict(width=S(380), height=S(36), font=font(S(13)),
               fg_color=CARD, border_color=BORDER)
    lk = dict(font=font(S(13)))

    ctk.CTkLabel(f, text="Fecha (YYYY-MM-DD):", **lk).pack(anchor="w")
    dv = ctk.StringVar(value=existing.date if existing else date.today().isoformat())
    ctk.CTkEntry(f, textvariable=dv, **ekw).pack(pady=(0, S(8)))

    cats = get_categories(cat_type)
    cnames = [f"{c.icon} {c.name}" for c in cats]
    cids = [c.id for c in cats]
    ctk.CTkLabel(f, text="Categoría:", **lk).pack(anchor="w")
    cv = ctk.StringVar(value=cnames[0] if cnames else "")
    cat_menu = ctk.CTkOptionMenu(f, variable=cv, values=cnames, width=S(380), height=S(36),
                                 font=font(S(13)), dropdown_font=font(S(13)),
                                 fg_color=CARD, button_color=ACCENT, button_hover_color="#4C9AFF")
    cat_menu.pack(pady=(0, S(8)))

    ctk.CTkLabel(f, text="Subcategoría (opcional):", **lk).pack(anchor="w")
    sub_var = ctk.StringVar(value="Ninguna")
    sub_menu_widget = ctk.CTkOptionMenu(f, variable=sub_var, values=["Ninguna"],
                                        width=S(380), height=S(36),
                                        font=font(S(13)), dropdown_font=font(S(13)),
                                        fg_color=CARD, button_color=ACCENT, button_hover_color="#4C9AFF")
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

    ctk.CTkLabel(f, text="Monto:", **lk).pack(anchor="w")
    av = ctk.StringVar(value=str(existing.amount) if existing else "")
    ctk.CTkEntry(f, textvariable=av, **ekw).pack(pady=(0, S(8)))

    ctk.CTkLabel(f, text="Descripción:", **lk).pack(anchor="w")
    descv = ctk.StringVar(value=existing.description if existing else "")
    desc_row = ctk.CTkFrame(f, fg_color="transparent")
    desc_row.pack(fill="x", pady=(0, S(8)))
    ctk.CTkEntry(desc_row, textvariable=descv, width=S(300), height=S(36),
                 font=font(S(13)), fg_color=CARD, border_color=BORDER).pack(side="left")

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
            result = generate_description(cat_name, sub_name, amt, learnings_ctx)
            app.after(0, lambda: _set_desc(result))
        threading.Thread(target=_run, daemon=True).start()

    def _set_desc(result):
        btn_ai.configure(state="normal", text="✨ IA")
        if result:
            descv.set(result)
            _last_ai_desc["value"] = result
        else:
            messagebox.showwarning(
                "IA", "No se pudo conectar con Ollama para generar la descripción.",
                parent=dlg
            )

    btn_ai = ctk.CTkButton(desc_row, text="✨ IA", width=S(60), height=S(36),
                           fg_color=PURPLE, hover_color="#A371F7",
                           font=font(S(12), "bold"), command=_ai_desc)
    btn_ai.pack(side="right", padx=(S(6), 0))

    rv = ctk.BooleanVar(value=bool(existing.is_recurring) if existing else False)
    ctk.CTkCheckBox(f, text="Recurrente", variable=rv,
                    font=font(S(13)), fg_color=ACCENT).pack(anchor="w", pady=(0, S(4)))

    dayv = ctk.StringVar(value=str(existing.recurring_day) if existing and existing.recurring_day else str(date.today().day))
    ctk.CTkLabel(f, text="Día del mes:", **lk).pack(anchor="w")
    ctk.CTkEntry(f, textvariable=dayv, **ekw).pack(pady=(0, S(8)))

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
                from database import save_desc_learning
                save_desc_learning(
                    _last_ai_desc.get("category", ""),
                    _last_ai_desc.get("subcategory", ""),
                    _last_ai_desc["value"], desc
                )

            if existing:
                update_transaction(existing.id, d, amt, cid, desc, rec, rday, sid)
            else:
                add_transaction(d, amt, cid, desc, rec, rday, sid)
            dlg.destroy()
            show_transactions(app)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=dlg)

    btn_primary(f, "Guardar", save, S(380), S(42)).pack(pady=(S(10), 0))


def _del_tx(app, tid):
    if messagebox.askyesno("Confirmar", "¿Eliminar esta transacción?", parent=app):
        delete_transaction(tid)
        show_transactions(app)


def _export_csv(app):
    """Exporta transacciones del mes a CSV."""
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
            messagebox.showinfo("Exportado", f"Transacciones exportadas a:\n{filepath}", parent=app)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=app)


def _run_auto_backup():
    """Ejecuta backup automático (llamar al inicio)."""
    try:
        auto_backup()
    except Exception:
        pass
