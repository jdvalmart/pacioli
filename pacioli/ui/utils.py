"""Utilidades específicas de la interfaz de usuario."""


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
    """Escala un valor según la resolución de pantalla."""
    return max(int(v * _SC), 1)
