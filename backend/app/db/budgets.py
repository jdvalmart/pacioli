"""Monthly budgets per category and the monthly plan total."""

from decimal import Decimal

from app.db.connection import _to_cents, _to_dec, get_connection
from app.db.models import Budget


def get_budgets(month: int, year: int) -> list[Budget]:
    """Return budgets for a month."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, category_id, month, year, amount_cents FROM budgets WHERE month = ? AND year = ?",
            (month, year),
        )
        return [
            Budget(
                id=r["id"],
                category_id=r["category_id"],
                month=r["month"],
                year=r["year"],
                amount=_to_dec(r["amount_cents"]),
            )
            for r in cursor.fetchall()
        ]


def set_budget(category_id: int, month: int, year: int, amount: Decimal | float | int) -> None:
    """Create or update the budget of a category for a month."""
    cents = _to_cents(amount)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO budgets (category_id, month, year, amount_cents)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(category_id, month, year) DO UPDATE SET amount_cents = excluded.amount_cents
        """,
            (category_id, month, year, cents),
        )
        conn.commit()


def set_budgets_bulk(month: int, year: int, items: list[tuple[int, Decimal | float | int]]) -> None:
    """Replace the full budget state of a month.

    Every existing budget of the month is removed and the provided
    (category_id, amount) pairs are inserted. Used by the budget
    setup form.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM budgets WHERE month = ? AND year = ?", (month, year))
        for category_id, amount in items:
            cursor.execute(
                "INSERT INTO budgets (category_id, month, year, amount_cents) VALUES (?, ?, ?, ?)",
                (category_id, month, year, _to_cents(amount)),
            )
        conn.commit()


def delete_budget(category_id: int, month: int, year: int) -> None:
    """Delete the budget of a category for a month."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM budgets WHERE category_id = ? AND month = ? AND year = ?",
            (category_id, month, year),
        )
        conn.commit()


def get_monthly_plan(month: int, year: int) -> Decimal | None:
    """Return the total budget the user set for a month, if any."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT total_cents FROM monthly_plans WHERE month = ? AND year = ?",
            (month, year),
        ).fetchone()
        return _to_dec(row["total_cents"]) if row else None


def set_monthly_plan(month: int, year: int, total: Decimal | float | int) -> None:
    """Create or update the total budget of a month."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO monthly_plans (month, year, total_cents)
            VALUES (?, ?, ?)
            ON CONFLICT(month, year) DO UPDATE SET total_cents = excluded.total_cents
        """,
            (month, year, _to_cents(total)),
        )
        conn.commit()
