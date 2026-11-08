"""Savings and investment items (pockets, CDTs, stocks)."""

import sqlite3
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from app import clock
from app.db.connection import _ddl, _insert_get_id, _to_cents, _to_dec, get_connection
from app.db.models import CATEGORY_ROLE_SAVINGS, SavingsItem
from app.db.transactions import _month_window

# Bolsillos hold money moved from accounts. Their balance is always
# derived from ahorro (deposit) minus retiro (withdrawal) movements.
# A bolsillo_programado adds a recurring ahorro template that the
# recurring engine materializes every month.


def _row_to_savings(row: sqlite3.Row) -> SavingsItem:
    balance = _to_dec(row["balance_cents"])
    current_value = (
        _to_dec(row["current_value_cents"]) if row["current_value_cents"] is not None else None
    )
    return SavingsItem(
        id=row["id"],
        name=row["name"],
        kind=row["kind"],
        category_id=row["category_id"],
        target=_to_dec(row["target_cents"]) if row["target_cents"] is not None else None,
        rate_bp=row["rate_bp"],
        term_days=row["term_days"],
        current_value=current_value,
        dividends=_to_dec(row["dividends_cents"]),
        scheduled_day=row["scheduled_day"],
        scheduled_amount=(
            _to_dec(row["scheduled_amount_cents"])
            if row["scheduled_amount_cents"] is not None
            else None
        ),
        source_account_id=row["source_account_id"],
        opening=_to_dec(row["opening_cents"]),
        balance=balance,
        invested=balance,
        matures_on=(
            date.fromisoformat(str(row["created_at"])[:10]) + timedelta(days=row["term_days"])
            if row["term_days"] and row["created_at"]
            else None
        ),
    )


def get_savings() -> list[SavingsItem]:
    """Return all savings items with their computed balance.

    ``opening`` is money that already existed when the item was created
    (e.g. an existing CDT) and belongs to no month; the balance is that
    opening amount plus the net of ahorro minus retiro movements.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*,
                   s.opening_cents + COALESCE((
                       SELECT SUM(CASE WHEN t.kind = 'ahorro' THEN t.amount_cents
                                       WHEN t.kind = 'retiro' THEN -t.amount_cents
                                       ELSE 0 END)
                       FROM transactions t
                       WHERE t.savings_id = s.id
                   ), 0) as balance_cents
            FROM savings s
            ORDER BY s.created_at, s.id
        """)
        return [_row_to_savings(row) for row in cursor.fetchall()]


def add_savings(
    name: str,
    kind: str,
    target: Decimal | float | int | None = None,
    rate_bp: int | None = None,
    term_days: int | None = None,
    current_value: Decimal | float | int | None = None,
    dividends: Decimal | float | int | None = None,
    scheduled_day: int | None = None,
    scheduled_amount: Decimal | float | int | None = None,
    source_account_id: int | None = None,
    category_id: int | None = None,
    initial_amount: Decimal | float | int | None = None,
    initial_account_id: int | None = None,
) -> int:
    """Create a savings item and return its id.

    ``initial_amount`` is the opening balance: money that already
    existed before using the app (e.g. an existing CDT). It belongs to
    no month and is stored on the item, not as an ahorro movement.
    A bolsillo_programado also creates a recurring ahorro template that
    materializes every month on the scheduled day.
    """
    cents = _to_cents(initial_amount) if initial_amount is not None else 0
    from_account = initial_account_id is not None and cents > 0
    with get_connection() as conn:
        cursor = conn.cursor()
        item_id = _insert_get_id(
            cursor,
            _ddl("""
            INSERT INTO savings
                (name, kind, category_id, target_cents, rate_bp, term_days, current_value_cents,
                 dividends_cents, scheduled_day, scheduled_amount_cents, source_account_id, opening_cents)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """),
            (
                name,
                kind,
                category_id,
                _to_cents(target) if target is not None else None,
                rate_bp,
                term_days,
                _to_cents(current_value) if current_value is not None else None,
                _to_cents(dividends) if dividends is not None else 0,
                scheduled_day,
                _to_cents(scheduled_amount) if scheduled_amount is not None else None,
                source_account_id,
                0 if from_account else cents,
            ),
        )

        if from_account:
            cursor.execute(
                """
                INSERT INTO transactions
                    (date, amount_cents, category_id, description, is_recurring,
                     recurring_day, subcategory_id, account_id, kind, to_account_id, card_id, savings_id)
                VALUES (?, ?, NULL, ?, 0, NULL, NULL, ?, 'ahorro', NULL, NULL, ?)
                """,
                (
                    clock.today().isoformat(),
                    cents,
                    f"Ahorro inicial: {name}",
                    initial_account_id,
                    item_id,
                ),
            )

        if kind == "bolsillo_programado" and scheduled_day is not None:
            template_date = date(clock.today().year, clock.today().month, scheduled_day)
            cursor.execute(
                """
                INSERT INTO transactions
                    (date, amount_cents, category_id, description, is_recurring,
                     recurring_day, subcategory_id, account_id, kind, to_account_id, card_id, savings_id)
                VALUES (?, ?, NULL, ?, 1, ?, NULL, ?, 'ahorro', NULL, NULL, ?)
                """,
                (
                    template_date.isoformat(),
                    _to_cents(scheduled_amount) if scheduled_amount is not None else 0,
                    f"Ahorro programado: {name}",
                    scheduled_day,
                    source_account_id,
                    item_id,
                ),
            )

        conn.commit()
        return item_id


def update_savings(
    item_id: int,
    name: str,
    kind: str,
    target: Decimal | float | int | None = None,
    rate_bp: int | None = None,
    term_days: int | None = None,
    current_value: Decimal | float | int | None = None,
    dividends: Decimal | float | int | None = None,
    scheduled_day: int | None = None,
    scheduled_amount: Decimal | float | int | None = None,
    source_account_id: int | None = None,
    category_id: int | None = None,
) -> None:
    """Update a savings item, keeping its recurring template in sync."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE savings
            SET name = ?, kind = ?, target_cents = ?, rate_bp = ?, term_days = ?,
                current_value_cents = ?, dividends_cents = ?, scheduled_day = ?,
                scheduled_amount_cents = ?, source_account_id = ?, category_id = ?
            WHERE id = ?
            """,
            (
                name,
                kind,
                _to_cents(target) if target is not None else None,
                rate_bp,
                term_days,
                _to_cents(current_value) if current_value is not None else None,
                _to_cents(dividends) if dividends is not None else 0,
                scheduled_day,
                _to_cents(scheduled_amount) if scheduled_amount is not None else None,
                source_account_id,
                category_id,
                item_id,
            ),
        )
        if kind == "bolsillo_programado" and scheduled_day is not None:
            template_date = date(clock.today().year, clock.today().month, scheduled_day)
            cursor.execute(
                """
                UPDATE transactions
                SET date = ?, amount_cents = ?, account_id = ?, recurring_day = ?
                WHERE is_recurring = 1 AND generated_from IS NULL
                  AND kind = 'ahorro' AND savings_id = ?
                """,
                (
                    template_date.isoformat(),
                    _to_cents(scheduled_amount) if scheduled_amount is not None else 0,
                    source_account_id,
                    scheduled_day,
                    item_id,
                ),
            )
        conn.commit()


def delete_savings(item_id: int) -> None:
    """Delete a savings item and its recurring template."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM transactions WHERE is_recurring = 1 AND generated_from IS NULL "
            "AND kind = 'ahorro' AND savings_id = ?",
            (item_id,),
        )
        cursor.execute("DELETE FROM savings WHERE id = ?", (item_id,))
        conn.commit()


# ── Savings in budgets and reports ────────────────────────────


def _savings_category(conn: Any) -> Any | None:
    """Category that groups savings movements (``role = 'savings'``).

    Looked up by role, not by name, so the user can rename it freely.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, color, icon FROM categories WHERE role = ?",
        (CATEGORY_ROLE_SAVINGS,),
    )
    return cursor.fetchone()


def _savings_net_for_month(conn: Any, month: int, year: int) -> Decimal:
    """Net amount moved to savings in a month (ahorro minus retiro).

    Savings linked to a budget category (reserves) are excluded here:
    they show under their own category instead of the general "Ahorro".
    """
    start, end = _month_window(month, year)
    cursor = conn.cursor()
    row = cursor.execute(
        """
        SELECT COALESCE(SUM(CASE WHEN t.kind = 'ahorro' THEN t.amount_cents
                                 WHEN t.kind = 'retiro' THEN -t.amount_cents
                                 ELSE 0 END), 0) as cents
        FROM transactions t
        LEFT JOIN savings sv ON sv.id = t.savings_id
        WHERE t.kind IN ('ahorro', 'retiro') AND t.date >= ? AND t.date < ?
          AND sv.category_id IS NULL
    """,
        (start, end),
    ).fetchone()
    return _to_dec(row["cents"])
