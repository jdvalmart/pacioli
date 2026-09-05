#!/usr/bin/env python3
"""Tema limpio y consistente para Budget App"""

import customtkinter as ctk

# ── Colores ──────────────────────────────────────────────────
BG        = "#0D1117"   # fondo principal
SURFACE   = "#161B22"   # sidebar, panels
CARD      = "#1C2128"   # cards, entries
CARD_HOVER= "#252D38"   # hover
BORDER    = "#30363D"   # bordes sutiles
ACCENT    = "#58A6FF"   # azul principal (acciones)
GREEN     = "#3FB950"   # ingresos, éxito
RED       = "#F85149"   # gastos, eliminar
ORANGE    = "#D29922"   # advertencia
PURPLE    = "#BC8CFF"   # IA
TEAL      = "#39D353"   # acento
TEXT      = "#E6EDF3"   # texto principal
TEXT_SEC  = "#8B949E"   # texto secundario
TEXT_DIM  = "#484F58"   # texto dim

# ── Fuentes ──────────────────────────────────────────────────
FONT = "Nunito"

# ── Espaciado ────────────────────────────────────────────────
def S(v, scale=1.0):
    """Escalar tamaño."""
    return max(int(v * scale), 1)

# ── Aplicar tema ─────────────────────────────────────────────
def apply_theme():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")


# ── Helper: fuente consistente ───────────────────────────────
def font(size=14, weight="normal"):
    return ctk.CTkFont(family=FONT, size=size, weight=weight)


# ── Helper: botón primario ───────────────────────────────────
def btn_primary(parent, text, command=None, width=200, height=40):
    return ctk.CTkButton(
        parent, text=text, command=command,
        width=width, height=height,
        corner_radius=10,
        fg_color=ACCENT, hover_color="#4C9AFF",
        font=font(14, "bold"),
        text_color="#FFFFFF"
    )


# ── Helper: botón peligro ───────────────────────────────────
def btn_danger(parent, text, command=None, width=80, height=32):
    return ctk.CTkButton(
        parent, text=text, command=command,
        width=width, height=height,
        corner_radius=8,
        fg_color=RED, hover_color="#DA3633",
        font=font(12),
        text_color="#FFFFFF"
    )


# ── Helper: card ─────────────────────────────────────────────
def card(parent, **kwargs):
    return ctk.CTkFrame(parent, corner_radius=12, fg_color=CARD, **kwargs)
