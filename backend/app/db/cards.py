"""Credit cards; billing rules live in app.domain.billing."""

from datetime import date
from decimal import Decimal
from typing import Any

from app import clock
from app.db.connection import _ddl, _insert_get_id, _to_cents, _to_dec, get_connection
from app.db.models import CreditCard
from app.domain import billing

# A card has a spending limit and billing cycle days. Its spent and
# available amounts are always derived from the current month's
# gasto_tc transactions linked to it.


def _card_of(row: Any) -> billing.Card | None:
    """Billing parameters joined on a gasto_tc row (None if the card was deleted)."""
    if row["cutoff_day"] is None:
        return None
    return billing.Card(cutoff_day=row["cutoff_day"], payment_day=row["payment_day"])


def _purchase_of(row: Any) -> billing.Purchase:
    return billing.Purchase(
        date=date.fromisoformat(row["date"]),
        amount_cents=row["amount_cents"],
        installments=row["installments"] or 1,
        interest_bp=row["interest_bp"] or 0,
    )


def _billed_in(row: Any, year: int, month: int) -> tuple[int, int] | None:
    """(installment number, cents) of a gasto_tc row paid in ``(year, month)``.

    Each installment counts in the month its statement is due. A purchase
    whose card was deleted has no cycle: it counts once, in full, in its
    purchase month.
    """
    purchase = _purchase_of(row)
    card = _card_of(row)
    if card is None:
        if (purchase.date.year, purchase.date.month) == (year, month):
            return 1, billing.financed_cents(purchase)
        return None
    item = billing.installment_in_month(card, purchase, year, month)
    return None if item is None else (item.number, item.cents)


def _row_to_card(row: Any, conn: Any, today: date) -> CreditCard:
    card = billing.Card(cutoff_day=row["cutoff_day"], payment_day=row["payment_day"])
    purchases = [
        _purchase_of(r)
        for r in conn.execute(
            "SELECT date, amount_cents, installments, interest_bp FROM transactions "
            "WHERE card_id = ? AND kind = 'gasto_tc' AND date <= ?",
            (row["id"], today.isoformat()),
        ).fetchall()
    ]
    # Only what had happened by ``today``: a past-month view must not
    # count later purchases or payments.
    payments = conn.execute(
        "SELECT COALESCE(SUM(amount_cents), 0) as cents FROM transactions "
        "WHERE card_id = ? AND kind = 'pago_tc' AND date <= ?",
        (row["id"], today.isoformat()),
    ).fetchone()["cents"]
    status = billing.card_status(card, purchases, int(payments), today)

    limit = _to_dec(row["limit_cents"])
    outstanding = _to_dec(status.outstanding_cents)
    return CreditCard(
        id=row["id"],
        name=row["name"],
        limit=limit,
        cutoff_day=card.cutoff_day,
        payment_day=card.payment_day,
        pending=_to_dec(status.pending_cents),
        debt=_to_dec(status.due_cents),
        outstanding=outstanding,
        available=limit - outstanding,
        cycle_start=status.cycle_start,
        cycle_end=status.cycle_end,
        payment_date=status.payment_date,
    )


def get_credit_cards(today: date | None = None) -> list[CreditCard]:
    """Return all credit cards with their cycle, pending and outstanding amounts."""
    today = today or clock.today()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM credit_cards ORDER BY created_at, id")
        return [_row_to_card(row, conn, today) for row in cursor.fetchall()]


def add_credit_card(
    name: str,
    limit: Decimal | float | int,
    cutoff_day: int,
    payment_day: int,
) -> int:
    """Create a credit card and return its id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        sql = _ddl("""
            INSERT INTO credit_cards (name, limit_cents, cutoff_day, payment_day)
            VALUES (?, ?, ?, ?)
            """)
        new_id = _insert_get_id(cursor, sql, (name, _to_cents(limit), cutoff_day, payment_day))
        conn.commit()
        return new_id


def update_credit_card(
    card_id: int,
    name: str,
    limit: Decimal | float | int,
    cutoff_day: int,
    payment_day: int,
) -> None:
    """Update a credit card."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE credit_cards
            SET name = ?, limit_cents = ?, cutoff_day = ?, payment_day = ?
            WHERE id = ?
            """,
            (name, _to_cents(limit), cutoff_day, payment_day, card_id),
        )
        conn.commit()


def delete_credit_card(card_id: int) -> None:
    """Delete a credit card, leaving its transactions unlinked."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM credit_cards WHERE id = ?", (card_id,))
        conn.commit()
