#!/usr/bin/env python3
"""Utilidades compartidas para Pacioli."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
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


# ── Formato y parseo de dinero ──────────────────────────────

def fmt_cop(v) -> str:
    """Formatea cualquier número (Decimal/int/float) como $1.234.567 COP."""
    d = v if isinstance(v, Decimal) else Decimal(str(v))
    sign = "-" if d < 0 else ""
    units = abs(d).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return f"{sign}${units:,}".replace(",", ".")


def _resolve_single_separator(s: str, sep: str) -> str:
    parts = s.split(sep)
    if len(parts) > 2:
        return s.replace(sep, '')  # 1.234.567 → miles
    if len(parts) == 2 and len(parts[1]) == 3 and parts[0].isdigit() and parts[0] != '0':
        return s.replace(sep, '')  # 1.500 → miles (convención CO)
    return s.replace(sep, '.')     # decimal


def parse_amount(text: str) -> Decimal:
    """Convierte texto del usuario a Decimal (2 decimales máx.).

    Acepta: '1500000', '1.500.000', '1500000,50', '1.500.000,50',
    '1,500.50', '$ 2.000'. Con un solo separador, tres dígitos finales
    se interpretan como miles ('1.500' → 1500); si no, decimal ('1.50').
    Lanza ValueError con mensaje en español.
    """
    s = (text or "").strip().replace("$", "").replace(" ", "").replace("\u00a0", "")
    if not s:
        raise ValueError("Ingrese un monto")
    if s.startswith('-'):
        raise ValueError("El monto no puede ser negativo")
    s = s.lstrip('+')
    if not re.fullmatch(r'[0-9.,]+', s):
        raise ValueError(f"Monto inválido: '{text.strip()}'. Ingrese un número")
    if '.' in s and ',' in s:
        if s.rfind('.') > s.rfind(','):
            s = s.replace(',', '')                     # 1,500.50
        else:
            s = s.replace('.', '').replace(',', '.')   # 1.500,50
    elif ',' in s:
        s = _resolve_single_separator(s, ',')
    elif '.' in s:
        s = _resolve_single_separator(s, '.')
    try:
        d = Decimal(s)
    except InvalidOperation:
        raise ValueError(f"Monto inválido: '{text.strip()}'. Ingrese un número")
    return d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


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
