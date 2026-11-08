"""Credit card billing rules: cycles, installment schedules and amounts due.

All amounts are integer cents. A card has a ``cutoff_day`` (the day a
statement closes) and a ``payment_day`` (the day it is due). Both are
clamped to the month's last day, so a cutoff on the 31st closes on Feb 28.

Cycles are identified by an *ordinal* (``year * 12 + month - 1`` of the
cutoff that closes them), which makes "the next cycle" a plain ``+ 1``.

Rules modelled on how banks bill:

- A purchase belongs to the statement closed by the first cutoff on or
  after its date; installment *k* (0-based) is billed ``k`` cycles later.
- Interest applies only to multi-installment plans. The financed total is
  rounded to the cent once, then split so the installments add up exactly;
  the leftover cents go to the first installments.
- Each installment is attributed (for budgets and reports) to the month in
  which its statement is paid.
- Payments settle the oldest billed statements first (FIFO); money paid
  beyond what has been billed reduces the open cycle's installment.
"""

import calendar
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

BP_DENOMINATOR = 10_000  # interest is stored in basis points (1% = 100 bp)


@dataclass(frozen=True)
class Card:
    """The billing parameters of a credit card."""

    cutoff_day: int
    payment_day: int


@dataclass(frozen=True)
class Purchase:
    """A card purchase (``gasto_tc``) as stored."""

    date: date
    amount_cents: int
    installments: int = 1
    interest_bp: int = 0


@dataclass(frozen=True)
class Installment:
    """One billed installment of a purchase."""

    number: int  # 1-based
    of: int
    cycle: int  # ordinal of the cycle that bills it
    year: int  # month in which it is paid (statement due date)
    month: int
    cents: int


@dataclass(frozen=True)
class CardStatus:
    """Derived amounts of a card at a given date."""

    cycle_start: date  # last cutoff on or before today (exclusive bound)
    cycle_end: date  # next cutoff after today (inclusive bound)
    payment_date: date  # due date of the open cycle's statement
    pending_cents: int  # open cycle's installments not yet prepaid
    due_cents: int  # billed in closed statements and still unpaid
    outstanding_cents: int  # everything financed minus everything paid


# ── Calendar helpers ──────────────────────────────────────────


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    """Move ``(year, month)`` by ``delta`` months."""
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def day_in_month(year: int, month: int, day: int) -> date:
    """``day`` of the month, clamped to its last day."""
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def cycle_of(card: Card, day: date) -> int:
    """Ordinal of the cycle that contains ``day`` (closed by the next cutoff)."""
    end = day_in_month(day.year, day.month, card.cutoff_day)
    if day > end:
        year, month = shift_month(day.year, day.month, 1)
        end = day_in_month(year, month, card.cutoff_day)
    return end.year * 12 + (end.month - 1)


def cutoff_of(card: Card, cycle: int) -> date:
    """Cutoff date that closes a cycle."""
    return day_in_month(cycle // 12, cycle % 12 + 1, card.cutoff_day)


def payment_date_of(card: Card, cycle: int) -> date:
    """Due date of a cycle's statement.

    It falls on ``payment_day`` of the cutoff's month, or of the next
    month when that day comes before the cutoff.
    """
    cutoff = cutoff_of(card, cycle)
    payment = day_in_month(cutoff.year, cutoff.month, card.payment_day)
    if payment < cutoff:
        year, month = shift_month(cutoff.year, cutoff.month, 1)
        payment = day_in_month(year, month, card.payment_day)
    return payment


# ── Amounts ───────────────────────────────────────────────────


def financed_cents(purchase: Purchase) -> int:
    """Purchase total including plan interest, rounded half-up to the cent."""
    if purchase.installments <= 1 or purchase.interest_bp <= 0:
        return purchase.amount_cents
    numerator = purchase.amount_cents * (BP_DENOMINATOR + purchase.interest_bp)
    return (2 * numerator + BP_DENOMINATOR) // (2 * BP_DENOMINATOR)


def schedule(card: Card, purchase: Purchase) -> list[Installment]:
    """Every installment of a purchase, with its cycle and payment month."""
    count = max(purchase.installments, 1)
    total = financed_cents(purchase)
    base, leftover = divmod(total, count)
    first_cycle = cycle_of(card, purchase.date)
    result = []
    for k in range(count):
        cycle = first_cycle + k
        due = payment_date_of(card, cycle)
        result.append(
            Installment(
                number=k + 1,
                of=count,
                cycle=cycle,
                year=due.year,
                month=due.month,
                cents=base + (1 if k < leftover else 0),
            )
        )
    return result


def installment_in_month(
    card: Card, purchase: Purchase, year: int, month: int
) -> Installment | None:
    """The installment of a purchase paid in ``(year, month)``, if any."""
    for item in schedule(card, purchase):
        if (item.year, item.month) == (year, month):
            return item
    return None


def card_status(
    card: Card, purchases: Iterable[Purchase], payments_cents: int, today: date
) -> CardStatus:
    """Cycle dates and amounts of a card as of ``today``."""
    open_cycle = cycle_of(card, today)
    billed_closed = 0
    billed_open = 0
    financed = 0
    for purchase in purchases:
        financed += financed_cents(purchase)
        for item in schedule(card, purchase):
            if item.cycle < open_cycle:
                billed_closed += item.cents
            elif item.cycle == open_cycle:
                billed_open += item.cents

    outstanding = max(financed - payments_cents, 0)
    due = max(billed_closed - payments_cents, 0)
    prepaid = max(payments_cents - billed_closed, 0)
    pending = min(max(billed_open - prepaid, 0), outstanding)

    return CardStatus(
        cycle_start=cutoff_of(card, open_cycle - 1),
        cycle_end=cutoff_of(card, open_cycle),
        payment_date=payment_date_of(card, open_cycle),
        pending_cents=pending,
        due_cents=due,
        outstanding_cents=outstanding,
    )
