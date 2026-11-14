"""Transactions and recurring materialization."""

import calendar
import sqlite3
from datetime import date
from decimal import Decimal

from app import clock
from app.db.cards import CARD_CANDIDATES_SQL, _billed_in, card_candidates_params
from app.db.connection import _ddl, _insert_get_id, _to_cents, _to_dec, get_connection
from app.db.models import Transaction
from app.domain.kinds import TxKind

_TX_KEYS = {f.name for f in Transaction.__dataclass_fields__.values()}


def _month_window(month: int, year: int) -> tuple[str, str]:
    """Return the [start, end) ISO date range covering a month."""
    start = f"{year}-{month:02d}-01"
    end = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
    return start, end


def _row_to_tx(row: sqlite3.Row) -> Transaction:
    data = dict(row)
    data["amount"] = _to_dec(data.pop("amount_cents"))
    data["date"] = date.fromisoformat(data["date"])
    return Transaction(**{k: v for k, v in data.items() if k in _TX_KEYS})


def get_transactions(month: int, year: int) -> list[Transaction]:
    """Return all transactions of a month, newest first.

    Card purchases (``gasto_tc``) belong to the month in which their
    statement is paid, not to the purchase month, so the list matches the
    budgets and the category breakdown.
    """
    start_date, end_date = _month_window(month, year)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT t.*, c.name as category_name, c.type as category_type, c.color, c.icon,
                   s.name as subcategory_name, s.icon as subcategory_icon,
                   a.name as account_name, a.icon as account_icon,
                   a2.name as to_account_name, a2.icon as to_account_icon,
                   cc.name as card_name, cc.cutoff_day, cc.payment_day,
                   sv.name as savings_name, ln.name as loan_name
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN subcategories s ON t.subcategory_id = s.id
            LEFT JOIN accounts a ON t.account_id = a.id
            LEFT JOIN accounts a2 ON t.to_account_id = a2.id
            LEFT JOIN credit_cards cc ON t.card_id = cc.id
            LEFT JOIN savings sv ON t.savings_id = sv.id
            LEFT JOIN loans ln ON t.loan_id = ln.id
            WHERE (t.kind <> 'gasto_tc' AND t.date >= ? AND t.date < ?)
               OR ("""
            + CARD_CANDIDATES_SQL
            + """)
            ORDER BY t.date DESC
        """,
            (start_date, end_date, *card_candidates_params(year, month)),
        )
        rows = cursor.fetchall()

    result = []
    for row in rows:
        if row["kind"] == TxKind.GASTO_TC:
            billed = _billed_in(row, year, month)
            if billed is None:
                continue
            tx = _row_to_tx(row)
            tx.installment_number = billed[0]
            tx.billed_amount = _to_dec(billed[1])
            result.append(tx)
        elif start_date <= row["date"] < end_date:
            result.append(_row_to_tx(row))
    return result


def add_transaction(
    date_val: date,
    amount: Decimal | float | int,
    category_id: int | None = None,
    description: str = "",
    is_recurring: bool = False,
    recurring_day: int | None = None,
    subcategory_id: int | None = None,
    account_id: int | None = None,
    kind: str = "gasto",
    to_account_id: int | None = None,
    card_id: int | None = None,
    savings_id: int | None = None,
    installments: int = 1,
    interest_bp: int = 0,
    loan_id: int | None = None,
) -> int:
    """Create a transaction and return its id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        sql = _ddl("""
            INSERT INTO transactions
                (date, amount_cents, category_id, description, is_recurring,
                 recurring_day, subcategory_id, account_id, kind, to_account_id, card_id, savings_id,
                 installments, interest_bp, loan_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """)
        new_id = _insert_get_id(
            cursor,
            sql,
            (
                date_val.isoformat(),
                _to_cents(amount),
                category_id,
                description,
                int(is_recurring),
                recurring_day,
                subcategory_id,
                account_id,
                kind,
                to_account_id,
                card_id,
                savings_id,
                installments,
                interest_bp,
                loan_id,
            ),
        )
        conn.commit()
        return new_id


def update_transaction(
    trans_id: int,
    date_val: date,
    amount: Decimal | float | int,
    category_id: int | None,
    description: str,
    is_recurring: bool = False,
    recurring_day: int | None = None,
    subcategory_id: int | None = None,
    account_id: int | None = None,
    kind: str = "gasto",
    to_account_id: int | None = None,
    card_id: int | None = None,
    savings_id: int | None = None,
    installments: int = 1,
    interest_bp: int = 0,
    loan_id: int | None = None,
) -> None:
    """Update an existing transaction."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE transactions
            SET date = ?, amount_cents = ?, category_id = ?, description = ?,
                is_recurring = ?, recurring_day = ?, subcategory_id = ?,
                account_id = ?, kind = ?, to_account_id = ?, card_id = ?, savings_id = ?,
                installments = ?, interest_bp = ?, loan_id = ?
            WHERE id = ?
        """,
            (
                date_val.isoformat(),
                _to_cents(amount),
                category_id,
                description,
                int(is_recurring),
                recurring_day,
                subcategory_id,
                account_id,
                kind,
                to_account_id,
                card_id,
                savings_id,
                installments,
                interest_bp,
                loan_id,
                trans_id,
            ),
        )
        conn.commit()


def delete_transaction(trans_id: int) -> None:
    """Delete a transaction by id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE id = ?", (trans_id,))
        conn.commit()


# A transaction with is_recurring=1 and generated_from NULL is a
# "template". When navigating to a later month, ensure_recurring()
# creates that month's instance (day clamped to the last day of the
# month when needed) and records it in recurring_materialized so it
# is never duplicated, even if the user deletes the instance.


def ensure_recurring(month: int, year: int) -> int:
    """Materialize recurring templates for the given month.

    Only months up to the current one are materialized: future months
    have not happened yet, so creating their movements now would inflate
    the current balances.

    Returns:
        Number of new transactions created.
    """
    today = clock.today()
    if (year, month) > (today.year, today.month):
        return 0
    last_day = calendar.monthrange(year, month)[1]
    created = 0
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, date, amount_cents, category_id, description,
                   recurring_day, subcategory_id, account_id, kind, to_account_id, card_id, savings_id, loan_id
            FROM transactions
            WHERE is_recurring = 1 AND generated_from IS NULL
              AND recurring_day IS NOT NULL
        """)
        templates = cursor.fetchall()
        for t in templates:
            t_year, t_month = int(t["date"][:4]), int(t["date"][5:7])
            if (year, month) <= (t_year, t_month):
                continue
            cursor.execute(
                "SELECT 1 FROM recurring_materialized WHERE template_id = ? AND month = ? AND year = ?",
                (t["id"], month, year),
            )
            if cursor.fetchone():
                continue
            day = min(t["recurring_day"], last_day)
            cursor.execute(
                """
                INSERT INTO transactions
                    (date, amount_cents, category_id, description,
                     is_recurring, recurring_day, subcategory_id, generated_from, account_id, kind, to_account_id, card_id, savings_id, loan_id)
                VALUES (?, ?, ?, ?, 0, NULL, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    f"{year:04d}-{month:02d}-{day:02d}",
                    t["amount_cents"],
                    t["category_id"],
                    t["description"],
                    t["subcategory_id"],
                    t["id"],
                    t["account_id"],
                    t["kind"],
                    t["to_account_id"],
                    t["card_id"],
                    t["savings_id"],
                    t["loan_id"],
                ),
            )
            cursor.execute(
                "INSERT INTO recurring_materialized (template_id, month, year) VALUES (?, ?, ?)",
                (t["id"], month, year),
            )
            created += 1
        conn.commit()
    return created
