"""Loan rules: balance with daily-accrued interest and a payoff projection.

All amounts are integer cents. Interest is quoted as an effective annual
rate (EA, basis points), as Colombian banks do, and accrues daily between
events: ``balance * ((1 + EA) ** (days / 365) - 1)``. Each payment first
covers accrued interest and the rest reduces capital. Without a rate the
balance is simply the starting balance minus payments (an estimate).

The starting point (``balance_cents`` at ``as_of``) is the last balance the
user confirmed with the bank; payments before it are already reflected there.
"""

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

BP = 10_000


@dataclass(frozen=True)
class Payment:
    date: date
    cents: int


@dataclass(frozen=True)
class LoanStatus:
    balance_cents: int  # what is owed today, interest accrued to today included
    paid_cents: int  # paid since the starting point
    interest_cents: int  # part of those payments (and accrual) that was interest
    remaining_installments: int | None  # at the regular installment; None = never ends
    payoff: date | None  # estimated last payment month (first day)


def accrued(balance_cents: int, rate_bp: int | None, days: int) -> int:
    """Interest on ``balance`` for ``days`` at an effective annual rate."""
    if not rate_bp or balance_cents <= 0 or days <= 0:
        return 0
    factor = float((1 + rate_bp / BP) ** (days / 365)) - 1
    return round(balance_cents * factor)


def monthly_rate(rate_bp: int | None) -> float:
    """Effective monthly rate equivalent to an effective annual rate."""
    return float((1 + (rate_bp or 0) / BP) ** (1 / 12)) - 1


def installments_left(
    balance_cents: int, installment_cents: int, rate_bp: int | None
) -> int | None:
    """Payments of ``installment`` needed to clear ``balance`` (annuity formula)."""
    if balance_cents <= 0:
        return 0
    if installment_cents <= 0:
        return None
    r = monthly_rate(rate_bp)
    if r == 0:
        return math.ceil(balance_cents / installment_cents)
    if installment_cents <= balance_cents * r:
        return None  # the installment does not even cover the interest
    return math.ceil(-math.log(1 - r * balance_cents / installment_cents) / math.log(1 + r))


def _add_months(day: date, months: int) -> date:
    index = day.year * 12 + day.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def loan_status(
    balance_cents: int,
    as_of: date,
    rate_bp: int | None,
    installment_cents: int,
    payments: Iterable[Payment],
    today: date,
) -> LoanStatus:
    """Balance today and payoff projection from the confirmed starting balance."""
    balance = balance_cents
    last = as_of
    paid = 0
    interest = 0
    for payment in sorted((p for p in payments if as_of <= p.date <= today), key=lambda p: p.date):
        due = accrued(balance, rate_bp, (payment.date - last).days)
        interest += due
        balance = max(balance + due - payment.cents, 0)
        paid += payment.cents
        last = payment.date
    due = accrued(balance, rate_bp, (today - last).days)
    interest += due
    balance += due

    left = installments_left(balance, installment_cents, rate_bp)
    payoff = None if left is None else (_add_months(today, left - 1) if left > 0 else None)
    return LoanStatus(
        balance_cents=balance,
        paid_cents=paid,
        interest_cents=interest,
        remaining_installments=left,
        payoff=payoff,
    )
