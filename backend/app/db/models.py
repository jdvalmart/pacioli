"""Dataclasses returned by the data layer."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class Category:
    """Expense or income category."""

    id: int | None
    name: str
    type: str  # 'income' or 'expense'
    color: str
    icon: str
    role: str | None = None  # system role, e.g. 'savings'


@dataclass
class Subcategory:
    """Subcategory belonging to a category."""

    id: int | None
    category_id: int
    name: str
    icon: str


@dataclass
class Transaction:
    """A single transaction (or a recurring template).

    ``kind`` is ingreso, gasto, transferencia (moves money between
    two of the user's accounts) or gasto_tc (credit card expense).
    Transfers have no category and carry a ``to_account_id``.
    """

    id: int | None
    date: date
    amount: Decimal
    category_id: int | None
    description: str
    is_recurring: bool
    recurring_day: int | None  # Day of month for recurring templates
    kind: str = "gasto"
    subcategory_id: int | None = None
    subcategory_name: str | None = None
    subcategory_icon: str | None = None
    generated_from: int | None = None  # Recurring template that generated it
    category_name: str | None = None  # Joined from categories
    category_type: str | None = None
    color: str | None = None
    icon: str | None = None
    account_id: int | None = None  # Where the money moved from/into
    account_name: str | None = None
    account_icon: str | None = None
    to_account_id: int | None = None  # Transfer destination
    to_account_name: str | None = None
    to_account_icon: str | None = None
    card_id: int | None = None  # Credit card for gasto_tc
    card_name: str | None = None
    installments: int = 1  # Cuotas for a gasto_tc purchase
    interest_bp: int = 0  # Total interest for the plan, in basis points
    savings_id: int | None = None  # Savings/investment item for ahorro/retiro
    savings_name: str | None = None
    installment_number: int | None = None  # gasto_tc: cuota billed in the listed month
    billed_amount: Decimal | None = None  # gasto_tc: that cuota's amount, interest included


@dataclass
class Budget:
    """Monthly budget for a category."""

    id: int | None
    category_id: int
    month: int  # 1-12
    year: int
    amount: Decimal


@dataclass
class Account:
    """A place where money lives (wallet, savings, bank...).

    ``starting`` is the opening balance that already existed when the
    account was created; it belongs to no month. ``balance`` is that
    opening amount plus the net of the account's linked transactions.
    """

    id: int | None
    name: str
    type: str  # 'efectivo' | 'digital' | 'ahorros' | 'banco'
    icon: str
    color: str
    starting: Decimal | None = None
    balance: Decimal | None = None


ACCOUNT_TYPE_DEFAULTS = {
    "efectivo": ("💵", "#10B981"),
    "digital": ("📱", "#3B82F6"),
    "ahorros": ("🐷", "#8B5CF6"),
    "banco": ("🏦", "#64748B"),
}


@dataclass
class CreditCard:
    """A credit card with a spending limit and billing cycle days.

    The open cycle runs from the last cutoff to the next one; its
    purchases (``pending``) are billed at ``cycle_end`` and due on
    ``payment_date``. ``debt`` is what is already billed and due now,
    ``outstanding`` is every unpaid purchase and ``available`` is the
    remaining credit (limit minus the outstanding balance).
    """

    id: int | None
    name: str
    limit: Decimal
    cutoff_day: int
    payment_day: int
    pending: Decimal | None = None
    debt: Decimal | None = None
    outstanding: Decimal | None = None
    available: Decimal | None = None
    cycle_start: date | None = None
    cycle_end: date | None = None
    payment_date: date | None = None


@dataclass
class SavingsItem:
    """A savings or investment bucket.

    Bolsillos hold money moved from accounts; a bolsillo_programado
    additionally schedules a recurring deposit; CDTs carry an
    interest rate and term; acciones track invested capital against a
    manually updated market value. ``balance`` is the net of ahorro
    minus retiro movements.
    """

    id: int | None
    name: str
    kind: str  # 'bolsillo' | 'bolsillo_programado' | 'cdt' | 'acciones'
    category_id: int | None = None
    target: Decimal | None = None
    rate_bp: int | None = None
    term_days: int | None = None
    current_value: Decimal | None = None
    dividends: Decimal | None = None
    scheduled_day: int | None = None
    scheduled_amount: Decimal | None = None
    source_account_id: int | None = None
    opening: Decimal | None = None
    balance: Decimal | None = None
    invested: Decimal | None = None
    matures_on: date | None = None


SAVINGS_KIND_ICONS = {
    "bolsillo": "👝",
    "bolsillo_programado": "📆",
    "cdt": "🏦",
    "acciones": "📈",
}


@dataclass
class MonthlySummary:
    """Aggregated totals for a month.

    ``balance`` is the month-only result; ``carryover`` is the
    accumulated balance of all previous months (from the first
    recorded transaction) and ``accumulated_balance`` is the sum of
    both, i.e. the running balance at the end of the month.
    """

    month: int
    year: int
    total_income: Decimal
    total_expense: Decimal
    balance: Decimal
    carryover: Decimal
    accumulated_balance: Decimal
    by_category: dict[str, Decimal]


# System role of the category that groups savings movements (categories.role).
CATEGORY_ROLE_SAVINGS = "savings"
