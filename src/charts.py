import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import numpy as np
import re
from typing import List, Tuple, Dict, Any
import io
from PIL import Image

from database import MonthlySummary, get_category_spending, get_budget_vs_actual
from theme import THEME


DARK_BG = THEME["bg_dark"]
DARK_SURFACE = THEME["bg_surface"]
DARK_TEXT = THEME["text"]
DARK_MUTED = THEME["text_dim"]
ACCENT_BLUE = THEME["blue"]
ACCENT_GREEN = THEME["accent"]
ACCENT_RED = THEME["red"]
ACCENT_YELLOW = THEME["gold"]
ACCENT_PURPLE = THEME["purple"]
ACCENT_ORANGE = THEME["orange"]


DPI = 130


_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001F9FF"
    "\U00002702-\U000027B0"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D"
    "\U00002600-\U000026FF]+", flags=re.UNICODE)


def _strip_emoji(text):
    return _EMOJI_RE.sub('', text).strip()


def apply_dark_theme(fig: Figure, ax: plt.Axes):
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(DARK_SURFACE)
    ax.tick_params(colors=DARK_TEXT, labelsize=9)
    ax.xaxis.label.set_color(DARK_TEXT)
    ax.yaxis.label.set_color(DARK_TEXT)
    ax.title.set_color(DARK_TEXT)
    for spine in ax.spines.values():
        spine.set_color(DARK_MUTED)
    ax.grid(True, color=DARK_MUTED, alpha=0.3, linestyle='--')


def create_pie_chart(data: List[Tuple[str, float, str, str]], title: str = '', size: tuple = None) -> Image.Image:
    fig_w = (size[0] / DPI) if size else 5
    fig_h = (size[1] / DPI) if size else 4
    if not data:
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=DPI)
        apply_dark_theme(fig, ax)
        ax.text(0.5, 0.5, 'No hay datos', ha='center', va='center', color=DARK_MUTED, fontsize=14)
        ax.set_title(title, color=DARK_TEXT, fontsize=13, pad=10)
    else:
        labels = [_strip_emoji(f"{d[3]} {d[0]}") for d in data]
        values = [d[1] for d in data]
        colors = [d[2] for d in data]

        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=DPI)
        apply_dark_theme(fig, ax)

        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'color': DARK_TEXT, 'fontsize': 10},
            wedgeprops={'edgecolor': DARK_BG, 'linewidth': 2}
        )

        for autotext in autotexts:
            autotext.set_color('#FFFFFF')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(10)

        ax.set_title(title, color=DARK_TEXT, fontsize=13, pad=10)

    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=DARK_BG, bbox_inches='tight', dpi=DPI)
    buf.seek(0)
    plt.close(fig)

    return Image.open(buf)


def create_bar_chart(data: List[Tuple[str, float, str, str]], title: str = '', horizontal: bool = True, size: tuple = None) -> Image.Image:
    fig_w = (size[0] / DPI) if size else 6
    fig_h = (size[1] / DPI) if size else 4
    if not data:
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=DPI)
        apply_dark_theme(fig, ax)
        ax.text(0.5, 0.5, 'No hay datos', ha='center', va='center', color=DARK_MUTED, fontsize=14)
        ax.set_title(title, color=DARK_TEXT, fontsize=13, pad=10)
    else:
        names = [_strip_emoji(f"{d[3]} {d[0]}") for d in data]
        values = [d[1] for d in data]
        colors = [d[2] for d in data]

        fig, ax = plt.subplots(figsize=(fig_w, max(fig_h, len(names) * 0.4)), dpi=DPI)
        apply_dark_theme(fig, ax)

        if horizontal:
            bars = ax.barh(names, values, color=colors, edgecolor=DARK_BG, height=0.6)
            ax.invert_yaxis()
            for bar, val in zip(bars, values):
                ax.text(bar.get_width() + max(values) * 0.01, bar.get_y() + bar.get_height()/2,
                        f'{val:,.0f}'.replace(",", "."), va='center', color=DARK_TEXT, fontsize=10)
        else:
            bars = ax.bar(names, values, color=colors, edgecolor=DARK_BG, width=0.6)
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values) * 0.01,
                        f'{val:,.0f}'.replace(",", "."), ha='center', color=DARK_TEXT, fontsize=10)

        ax.set_title(title, color=DARK_TEXT, fontsize=13, pad=10)

    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=DARK_BG, bbox_inches='tight', dpi=DPI)
    buf.seek(0)
    plt.close(fig)

    return Image.open(buf)


def create_trend_chart(summaries: List[MonthlySummary], title: str = '', size: tuple = None) -> Image.Image:
    fig_w = (size[0] / DPI) if size else 8
    fig_h = (size[1] / DPI) if size else 4
    if not summaries:
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=DPI)
        apply_dark_theme(fig, ax)
        ax.text(0.5, 0.5, 'No hay datos', ha='center', va='center', color=DARK_MUTED, fontsize=14)
        ax.set_title(title, color=DARK_TEXT, fontsize=13, pad=10)
    else:
        months = [f"{s.month:02d}/{str(s.year)[2:]}" for s in summaries]
        income = [s.total_income for s in summaries]
        expense = [s.total_expense for s in summaries]
        balance = [s.balance for s in summaries]

        x = np.arange(len(months))
        width = 0.25

        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=DPI)
        apply_dark_theme(fig, ax)

        bars1 = ax.bar(x - width, income, width, label='Ingresos', color=ACCENT_GREEN, edgecolor=DARK_BG)
        bars2 = ax.bar(x, expense, width, label='Gastos', color=ACCENT_RED, edgecolor=DARK_BG)
        bars3 = ax.bar(x + width, balance, width, label='Balance', color=ACCENT_BLUE, edgecolor=DARK_BG)

        ax.set_xticks(x)
        ax.set_xticklabels(months, rotation=45, ha='right', fontsize=10)
        ax.legend(facecolor=DARK_SURFACE, edgecolor=DARK_MUTED, labelcolor=DARK_TEXT, fontsize=10)
        ax.set_title(title, color=DARK_TEXT, fontsize=13, pad=10)

        ax.axhline(y=0, color=DARK_MUTED, linestyle='-', linewidth=0.5)

    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=DARK_BG, bbox_inches='tight', dpi=DPI)
    buf.seek(0)
    plt.close(fig)

    return Image.open(buf)


def create_budget_chart(budget_data: List[Dict[str, Any]], title: str = '', size: tuple = None) -> Image.Image:
    fig_w = (size[0] / DPI) if size else 6
    fig_h = (size[1] / DPI) if size else 4
    if not budget_data:
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=DPI)
        apply_dark_theme(fig, ax)
        ax.text(0.5, 0.5, 'Sin presupuestos', ha='center', va='center', color=DARK_MUTED, fontsize=14)
        ax.set_title(title, color=DARK_TEXT, fontsize=13, pad=10)
    else:
        names = [_strip_emoji(f"{d['icon']} {d['name']}") for d in budget_data]
        budgets = [d['budget'] for d in budget_data]
        actuals = [d['actual'] for d in budget_data]

        y = np.arange(len(names))
        height = 0.35

        fig, ax = plt.subplots(figsize=(fig_w, max(fig_h, len(names) * 0.4)), dpi=DPI)
        apply_dark_theme(fig, ax)

        bars1 = ax.barh(y + height/2, budgets, height, label='Presupuesto', color=ACCENT_BLUE, alpha=0.7, edgecolor=DARK_BG)
        bars2 = ax.barh(y - height/2, actuals, height, label='Real', color=ACCENT_ORANGE, alpha=0.9, edgecolor=DARK_BG)

        for i, (budget, actual) in enumerate(zip(budgets, actuals)):
            color = ACCENT_GREEN if actual <= budget and budget > 0 else ACCENT_RED
            ax.text(max(budget, actual) + max(max(budgets), max(actuals)) * 0.01, i,
                    f'{actual:,.0f}'.replace(",", ".") + ' / ' + f'{budget:,.0f}'.replace(",", "."),
                    va='center', color=color, fontsize=10, fontweight='bold')

        ax.set_yticks(y)
        ax.set_yticklabels(names, fontsize=10)
        ax.invert_yaxis()
        ax.legend(facecolor=DARK_SURFACE, edgecolor=DARK_MUTED, labelcolor=DARK_TEXT, fontsize=10, loc='lower right')
        ax.set_title(title, color=DARK_TEXT, fontsize=13, pad=10)

    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=DARK_BG, bbox_inches='tight', dpi=100)
    buf.seek(0)
    plt.close(fig)

    return Image.open(buf)