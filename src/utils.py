#!/usr/bin/env python3
"""Utilidades compartidas para Pacioli."""

from datetime import date
from database import get_categories, get_subcategories


# ── Constantes de meses ─────────────────────────────────────
MONTHS = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}


# ── Escalado de pantalla ────────────────────────────────────
_BASE_W = 1366

def _screen_scale():
    try:
        import tkinter as _tk
        _r = _tk.Tk()
        sw, sh = _r.winfo_screenwidth(), _r.winfo_screenheight()
        _r.destroy()
        return max(sw / _BASE_W, sh / 768, 1.0)
    except Exception:
        return 1.0

_SC = _screen_scale()

def S(v):
    return max(int(v * _SC), 1)


# ── Formato COP ─────────────────────────────────────────────
def fmt_cop(v):
    sign = "-" if v < 0 else ""
    return f"{sign}${int(round(abs(v))):,.0f}".replace(",", ".")


# ── Cache de categorías (N+1 fix) ──────────────────────────
_cat_cache = {}

def get_cat_map():
    """Retorna dict {id: Category} cacheado."""
    global _cat_cache
    if not _cat_cache:
        for c in get_categories():
            _cat_cache[c.id] = c
    return _cat_cache

def invalidate_cat_cache():
    """Llamar después de agregar/eliminar categorías."""
    global _cat_cache
    _cat_cache = {}

def lookup_cat(category_id):
    """Busca una categoría por ID usando el cache."""
    cat_map = get_cat_map()
    cat = cat_map.get(category_id)
    if cat:
        return cat.icon, cat.color, cat.name, cat.type
    return "📁", "#8B949E", "—", "expense"
