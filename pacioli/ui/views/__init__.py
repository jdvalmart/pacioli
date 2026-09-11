"""Views module for UI components."""

from pacioli.ui.views.dashboard import show_dashboard
from pacioli.ui.views.transactions import show_transactions
from pacioli.ui.views.budgets import show_budgets
from pacioli.ui.views.reports import show_reports
from pacioli.ui.views.categories import show_categories
from pacioli.ui.views.chat import open_chat
from pacioli.ui.views.ai_settings import open_ai_settings

__all__ = [
    "show_dashboard",
    "show_transactions",
    "show_budgets",
    "show_reports",
    "show_categories",
    "open_chat",
    "open_ai_settings",
]
