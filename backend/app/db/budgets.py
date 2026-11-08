"""Monthly budgets per category and the monthly plan total.

Budgets carry over: a month is *defined* once its budget is saved (it has a
``monthly_plans`` row or budget rows, even if every amount is 0). A month
that was never defined inherits the budgets and the total of the latest
defined month before it, so a new month never starts without a budget.
Saving a month (``set_budgets_bulk`` + ``set_monthly_plan``) defines it.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.db.connection import _to_cents, _to_dec, get_connection
from app.db.models import Budget
from app.domain.kinds import BudgetPlanSource as PlanSource


@dataclass
class BudgetPlan:
    """The total budget of a month and where it comes from."""

    total: Decimal | None
    source: PlanSource


def _index(month: int, year: int) -> int:
    return year * 12 + (month - 1)


def _effective_month(conn: Any, month: int, year: int) -> tuple[int, int] | None:
    """(month, year) whose budgets apply to ``(month, year)``: itself if it was
    defined, else the latest defined month before it, else None."""
    row = conn.execute(
        """
        SELECT d.month, d.year FROM (
            SELECT month, year FROM monthly_plans
            UNION
            SELECT month, year FROM budgets
        ) d
        WHERE d.year * 12 + d.month - 1 <= ?
        ORDER BY d.year DESC, d.month DESC
        LIMIT 1
        """,
        (_index(month, year),),
    ).fetchone()
    return (row["month"], row["year"]) if row else None


def effective_budget_month(month: int, year: int) -> tuple[int, int] | None:
    """Public form of ``_effective_month`` (used by reports)."""
    with get_connection() as conn:
        return _effective_month(conn, month, year)


def get_budgets(month: int, year: int) -> list[Budget]:
    """Budgets that apply to a month, inherited when the month was never defined."""
    with get_connection() as conn:
        source = _effective_month(conn, month, year)
        if source is None:
            return []
        rows = conn.execute(
            "SELECT id, category_id, amount_cents FROM budgets WHERE month = ? AND year = ?",
            source,
        ).fetchall()
        inherited = source != (month, year)
        return [
            Budget(
                id=r["id"],
                category_id=r["category_id"],
                month=month,
                year=year,
                amount=_to_dec(r["amount_cents"]),
                inherited=inherited,
            )
            for r in rows
        ]


def _define_month(conn: Any, month: int, year: int) -> None:
    """Copy inherited budgets (and total) into a month before editing one category,
    so editing a single budget never silently drops the inherited ones."""
    source = _effective_month(conn, month, year)
    if source is None or source == (month, year):
        return
    conn.execute(
        """
        INSERT INTO budgets (category_id, month, year, amount_cents)
        SELECT category_id, ?, ?, amount_cents FROM budgets WHERE month = ? AND year = ?
        """,
        (month, year, *source),
    )
    plan = conn.execute(
        "SELECT total_cents FROM monthly_plans WHERE month = ? AND year = ?", source
    ).fetchone()
    if plan is not None:
        conn.execute(
            "INSERT INTO monthly_plans (month, year, total_cents) VALUES (?, ?, ?)",
            (month, year, plan["total_cents"]),
        )


def set_budget(category_id: int, month: int, year: int, amount: Decimal | float | int) -> None:
    """Create or update the budget of a category for a month."""
    cents = _to_cents(amount)
    with get_connection() as conn:
        _define_month(conn, month, year)
        conn.execute(
            """
            INSERT INTO budgets (category_id, month, year, amount_cents)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(category_id, month, year) DO UPDATE SET amount_cents = excluded.amount_cents
            """,
            (category_id, month, year, cents),
        )
        conn.commit()


def set_budgets_bulk(month: int, year: int, items: list[tuple[int, Decimal | float | int]]) -> None:
    """Replace the full budget state of a month (the budget setup form).

    Every existing budget of the month is removed and the provided
    (category_id, amount) pairs are inserted.
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
        _define_month(conn, month, year)
        conn.execute(
            "DELETE FROM budgets WHERE category_id = ? AND month = ? AND year = ?",
            (category_id, month, year),
        )
        conn.commit()


def get_monthly_plan(month: int, year: int) -> Decimal | None:
    """Return the total budget saved for exactly this month, if any."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT total_cents FROM monthly_plans WHERE month = ? AND year = ?",
            (month, year),
        ).fetchone()
        return _to_dec(row["total_cents"]) if row else None


def get_budget_plan(month: int, year: int) -> BudgetPlan:
    """The total budget of a month, with a sensible default.

    In order: the total saved for the month; the latest total saved before
    it (inherited); the average income of the last three months that had
    income; nothing.
    """
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT month, year, total_cents FROM monthly_plans
            WHERE year * 12 + month - 1 <= ?
            ORDER BY year DESC, month DESC
            LIMIT 1
            """,
            (_index(month, year),),
        ).fetchone()
        if row is not None:
            source: PlanSource = (
                "saved" if (row["month"], row["year"]) == (month, year) else "inherited"
            )
            return BudgetPlan(total=_to_dec(row["total_cents"]), source=source)

        start = f"{year}-{month:02d}-01"
        incomes = conn.execute(
            """
            SELECT SUBSTR(date, 1, 7) AS ym, SUM(amount_cents) AS cents
            FROM transactions
            WHERE kind = 'ingreso' AND date < ?
            GROUP BY SUBSTR(date, 1, 7)
            ORDER BY ym DESC
            LIMIT 3
            """,
            (start,),
        ).fetchall()
        if incomes:
            average = sum(int(r["cents"]) for r in incomes) // len(incomes)
            return BudgetPlan(total=_to_dec(average), source="income_average")
        return BudgetPlan(total=None, source="none")


def set_monthly_plan(month: int, year: int, total: Decimal | float | int) -> None:
    """Create or update the total budget of a month (this defines the month)."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO monthly_plans (month, year, total_cents)
            VALUES (?, ?, ?)
            ON CONFLICT(month, year) DO UPDATE SET total_cents = excluded.total_cents
            """,
            (month, year, _to_cents(total)),
        )
        conn.commit()
