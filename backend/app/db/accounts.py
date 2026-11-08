"""Accounts and their derived balances."""

import sqlite3
from decimal import Decimal

from app.db.connection import _ddl, _insert_get_id, _to_cents, _to_dec, get_connection
from app.db.models import ACCOUNT_TYPE_DEFAULTS, Account

# An account represents where the money lives. Its balance is always
# derived from the net (income minus expense) of its linked
# transactions. Money that already existed when the account was
# created is a regular income transaction ("Saldo inicial: ...").


def _ensure_income_category(conn: sqlite3.Connection) -> int:
    """Return the id of the 'Otros ingresos' income category, creating it if missing."""
    row = conn.execute(
        "SELECT id FROM categories WHERE type = 'income' AND name = 'Otros ingresos'"
    ).fetchone()
    if row:
        return int(row["id"])
    cursor = conn.cursor()
    return _insert_get_id(
        cursor,
        _ddl(
            "INSERT INTO categories (name, type, color, icon) VALUES ('Otros ingresos', 'income', '#065F46', '💵')"
        ),
        (),
    )


def _row_to_account(row: sqlite3.Row) -> Account:
    return Account(
        id=row["id"],
        name=row["name"],
        type=row["type"],
        icon=row["icon"],
        color=row["color"],
        starting=_to_dec(row["starting_cents"]),
        balance=_to_dec(row["balance_cents"]),
    )


def get_accounts() -> list[Account]:
    """Return all accounts with their computed balance, oldest first.

    The balance starts from the account's opening amount and then adds
    ingresos, subtracts gastos and pagos_tc, and moves transfers between
    two accounts. Moving money to any savings item (bolsillo, programmed
    pocket, CDT or stocks) takes it out of the account; a retiro brings
    it back.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.*,
                   a.starting_cents + COALESCE((
                       SELECT SUM(
                           CASE
                               WHEN t.kind = 'ingreso' THEN t.amount_cents
                               WHEN t.kind IN ('gasto', 'pago_tc') THEN -t.amount_cents
                               WHEN t.kind = 'transferencia' THEN
                                   CASE WHEN t.account_id = a.id THEN -t.amount_cents
                                        WHEN t.to_account_id = a.id THEN t.amount_cents
                                        ELSE 0 END
                               WHEN t.kind = 'ahorro' THEN -t.amount_cents
                               WHEN t.kind = 'retiro' THEN t.amount_cents
                               ELSE 0
                           END
                       )
                       FROM transactions t
                       WHERE t.account_id = a.id OR t.to_account_id = a.id
                   ), 0) as balance_cents
            FROM accounts a
            ORDER BY a.created_at, a.id
        """)
        return [_row_to_account(row) for row in cursor.fetchall()]


def add_account(
    name: str,
    acct_type: str,
    starting_amount: Decimal | float | int,
    icon: str | None = None,
    color: str | None = None,
) -> int:
    """Create an account and return its id.

    ``starting_amount`` is the opening balance: money that already
    existed before using the app. It belongs to no month and is stored
    on the account, not as a transaction.
    """
    default_icon, default_color = ACCOUNT_TYPE_DEFAULTS.get(acct_type, ("💵", "#10B981"))
    with get_connection() as conn:
        cursor = conn.cursor()
        sql = _ddl("""
            INSERT INTO accounts (name, type, icon, color, starting_cents)
            VALUES (?, ?, ?, ?, ?)
            """)
        new_id = _insert_get_id(
            cursor,
            sql,
            (
                name,
                acct_type,
                icon or default_icon,
                color or default_color,
                _to_cents(starting_amount),
            ),
        )
        conn.commit()
        return new_id


def update_account(
    account_id: int,
    name: str,
    acct_type: str | None = None,
    starting_amount: Decimal | float | int | None = None,
) -> None:
    """Update an account's name, type and opening balance."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if acct_type is not None:
            icon, color = ACCOUNT_TYPE_DEFAULTS.get(acct_type, ("💵", "#10B981"))
            cursor.execute(
                "UPDATE accounts SET name = ?, type = ?, icon = ?, color = ? WHERE id = ?",
                (name, acct_type, icon, color, account_id),
            )
        else:
            cursor.execute("UPDATE accounts SET name = ? WHERE id = ?", (name, account_id))
        if starting_amount is not None:
            cursor.execute(
                "UPDATE accounts SET starting_cents = ? WHERE id = ?",
                (_to_cents(starting_amount), account_id),
            )
        conn.commit()


def delete_account(account_id: int) -> None:
    """Delete an account, leaving its transactions unlinked."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        conn.commit()
