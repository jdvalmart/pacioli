import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np
import re
from typing import List, Tuple, Dict, Any
import io
from PIL import Image

from database import MonthlySummary, get_category_spending, get_budget_vs_actual
from theme import BG, SURFACE, CARD, TEXT, TEXT_SEC, TEXT_DIM, ACCENT, GREEN, RED
from utils import fmt_cop


ACCENT_BLUE = ACCENT
ACCENT_GREEN = GREEN
ACCENT_RED = RED
ACCENT_YELLOW = "#D29922"
ACCENT_PURPLE = "#BC8CFF"
ACCENT_ORANGE = "#D29922"

DPI = 100


_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001F9FF"
    "\U00002702-\U000027B0"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D"
    "\U00002600-\U000026FF]+", flags=re.UNICODE)


def _strip_emoji(text):
    return _EMOJI_RE.sub('', text).strip()


def _setup(fig, ax, title=''):
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(SURFACE)
    ax.tick_params(colors=TEXT, labelsize=10)
    ax.xaxis.label.set_color(TEXT)
    ax.yaxis.label.set_color(TEXT)
    ax.set_title(title, color=TEXT, fontsize=13, pad=10, fontfamily='sans-serif')
    for s in ax.spines.values():
        s.set_color(TEXT_DIM)
        s.set_linewidth(0.5)
    ax.grid(True, color=TEXT_DIM, alpha=0.25, linestyle='--', linewidth=0.5)


def _legend(ax):
    leg = ax.legend(facecolor=SURFACE, edgecolor=TEXT_DIM, labelcolor=TEXT, fontsize=9, framealpha=0.9)
    return leg


def _to_image(fig) -> Image.Image:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=fig.get_facecolor(), bbox_inches='tight', dpi=DPI, transparent=False)
    buf.seek(0)
    plt.close(fig)
    return Image.open(buf)


def _empty(title, size):
    w, h = size if size else (500, 350)
    fw, fh = w / DPI, h / DPI
    fig, ax = plt.subplots(figsize=(fw, fh), dpi=DPI)
    _setup(fig, ax, title)
    ax.text(0.5, 0.5, 'No hay datos', ha='center', va='center', color=TEXT_DIM, fontsize=14, fontfamily='sans-serif')
    return _to_image(fig)


def create_pie_chart(data: List[Tuple[str, float, str, str]], title: str = '', size: tuple = None) -> Image.Image:
    w, h = size if size else (500, 350)
    fw, fh = w / DPI, h / DPI
    if not data:
        return _empty(title, size)

    labels = [_strip_emoji(f"{d[3]} {d[0]}") for d in data]
    values = [float(d[1]) for d in data]
    colors = [d[2] for d in data]

    fig, ax = plt.subplots(figsize=(fw, fh), dpi=DPI)
    _setup(fig, ax, title)

    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors, autopct='%1.1f%%',
        startangle=90, pctdistance=0.75,
        textprops={'color': TEXT, 'fontsize': 10, 'fontfamily': 'sans-serif'},
        wedgeprops={'edgecolor': BG, 'linewidth': 2, 'width': 0.55},
    )
    for t in autotexts:
        t.set_color('white')
        t.set_fontweight('bold')
        t.set_fontsize(9)

    return _to_image(fig)


def create_bar_chart(data: List[Tuple[str, float, str, str]], title: str = '', horizontal: bool = True, size: tuple = None) -> Image.Image:
    w, h = size if size else (600, 350)
    fw, fh = w / DPI, h / DPI
    if not data:
        return _empty(title, size)

    names = [_strip_emoji(f"{d[3]} {d[0]}") for d in data]
    values = [float(d[1]) for d in data]
    colors = [d[2] for d in data]

    if horizontal:
        fig, ax = plt.subplots(figsize=(fw, max(fh, len(names) * 0.45)), dpi=DPI)
        _setup(fig, ax, title)
        bars = ax.barh(names, values, color=colors, edgecolor=BG, height=0.6, linewidth=0.5)
        ax.invert_yaxis()
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + max(values) * 0.02, bar.get_y() + bar.get_height()/2,
                    fmt_cop(val), va='center', color=TEXT, fontsize=10, fontfamily='sans-serif')
    else:
        fig, ax = plt.subplots(figsize=(max(fw, len(names) * 0.5), fh), dpi=DPI)
        _setup(fig, ax, title)
        bars = ax.bar(names, values, color=colors, edgecolor=BG, width=0.6, linewidth=0.5)
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values) * 0.02,
                    fmt_cop(val), ha='center', color=TEXT, fontsize=10, fontfamily='sans-serif')
        ax.set_xticklabels(names, fontsize=10, rotation=30, ha='right', fontfamily='sans-serif')

    return _to_image(fig)


def create_trend_chart(summaries: List[MonthlySummary], title: str = '', size: tuple = None) -> Image.Image:
    w, h = size if size else (700, 350)
    fw, fh = w / DPI, h / DPI
    if not summaries:
        return _empty(title, size)

    months = [f"{s.month:02d}/{str(s.year)[2:]}" for s in summaries]
    income = [float(s.total_income) for s in summaries]
    expense = [float(s.total_expense) for s in summaries]
    balance = [float(s.balance) for s in summaries]

    active = [(m, inc, exp, bal) for m, inc, exp, bal in zip(months, income, expense, balance) if inc > 0 or exp > 0]
    if not active:
        return _empty(title, size)

    lbls = [a[0] for a in active]
    inc = [a[1] for a in active]
    exp = [a[2] for a in active]
    bal = [a[3] for a in active]

    x = np.arange(len(lbls))
    width = 0.25

    fig, ax = plt.subplots(figsize=(fw, fh), dpi=DPI)
    _setup(fig, ax, title)

    ax.bar(x - width, inc, width, label='Ingresos', color=ACCENT_GREEN, edgecolor=BG, linewidth=0.5)
    ax.bar(x, exp, width, label='Gastos', color=ACCENT_RED, edgecolor=BG, linewidth=0.5)
    ax.bar(x + width, bal, width, label='Balance', color=ACCENT_BLUE, edgecolor=BG, linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(lbls, rotation=45, ha='right', fontsize=10, fontfamily='sans-serif')
    _legend(ax)
    ax.axhline(y=0, color=TEXT_DIM, linestyle='-', linewidth=0.5)

    return _to_image(fig)


def create_budget_chart(budget_data: List[Dict[str, Any]], title: str = '', size: tuple = None) -> Image.Image:
    w, h = size if size else (600, 350)
    fw, fh = w / DPI, h / DPI
    if not budget_data:
        return _empty(title, size)

    names = [_strip_emoji(f"{d['icon']} {d['name']}") for d in budget_data]
    budgets = [float(d['budget']) for d in budget_data]
    actuals = [float(d['actual']) for d in budget_data]

    y = np.arange(len(names))
    height = 0.35

    fig, ax = plt.subplots(figsize=(fw, max(fh, len(names) * 0.45)), dpi=DPI)
    _setup(fig, ax, title)

    ax.barh(y + height/2, budgets, height, label='Presupuesto', color=ACCENT_BLUE, alpha=0.7, edgecolor=BG, linewidth=0.5)
    ax.barh(y - height/2, actuals, height, label='Real', color=ACCENT_ORANGE, alpha=0.9, edgecolor=BG, linewidth=0.5)

    for i, (budget, actual) in enumerate(zip(budgets, actuals)):
        color = ACCENT_GREEN if actual <= budget and budget > 0 else ACCENT_RED
        ax.text(max(budget, actual) + max(max(budgets), max(actuals)) * 0.02, i,
                f'{fmt_cop(actual)} / {fmt_cop(budget)}',
                va='center', color=color, fontsize=10, fontfamily='sans-serif')

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=10, fontfamily='sans-serif')
    ax.invert_yaxis()
    _legend(ax)

    return _to_image(fig)
