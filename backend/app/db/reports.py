"""Monthly aggregations and CSV export."""

from decimal import Decimal
from typing import Any

from app.db.cards import _billed_in
from app.db.categories import get_categories
from app.db.connection import _to_dec, get_connection
from app.db.models import MonthlySummary
from app.db.savings import _savings_category, _savings_net_for_month
from app.db.transactions import _month_window, get_transactions
from app.domain.kinds import TxKind


def get_monthly_summary(month: int, year: int) -> MonthlySummary:
    """Return income/expense/balance totals for a month.

    Transfers never count as income or expense. A credit card purchase
    (gasto_tc) does not move money on the purchase date: it only becomes
    an expense when the card is paid (pago_tc), at which point the money
    leaves the chosen account. This keeps the accumulated balance equal
    to the sum of the accounts.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        start_date, end_date = _month_window(month, year)

        # Spending by category (informational): real expenses plus card
        # purchases, so the user still sees where the money went. Card
        # purchases count in the month their statement is paid.
        cursor.execute(
            """
            SELECT c.name, t.kind, SUM(t.amount_cents) as total_cents
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.date >= ? AND t.date < ?
              AND t.kind IN ('ingreso', 'gasto')
            GROUP BY c.name, t.kind
        """,
            (start_date, end_date),
        )

        by_category: dict[str, Decimal] = {}
        for row in cursor.fetchall():
            name = row["name"]
            by_category[name] = by_category.get(name, Decimal("0.00")) + _to_dec(row["total_cents"])

        # Card purchases billed in this month, attributed by payment date.
        cursor.execute(
            """
            SELECT c.name, t.amount_cents, t.date, t.installments, t.interest_bp,
                   cc.cutoff_day, cc.payment_day
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            LEFT JOIN credit_cards cc ON t.card_id = cc.id
            WHERE t.kind = 'gasto_tc'
        """
        )
        for row in cursor.fetchall():
            billed = _billed_in(row, year, month)
            if billed is not None:
                name = row["name"]
                by_category[name] = by_category.get(name, Decimal("0.00")) + _to_dec(billed[1])

        # Savings movements feed the "Ahorro" category (net of withdrawals)
        # without counting as cash expenses.
        savings_cat = _savings_category(conn)
        if savings_cat is not None:
            net = _savings_net_for_month(conn, month, year)
            if net != 0:
                name = savings_cat["name"]
                by_category[name] = by_category.get(name, Decimal("0.00")) + net

        # Cash totals: expenses are actual outflows. A card payment is
        # an outflow; the card purchase itself is not (yet).
        totals = cursor.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN kind = 'ingreso' THEN amount_cents ELSE 0 END), 0) as income_cents,
                COALESCE(SUM(CASE WHEN kind IN ('gasto', 'pago_tc') THEN amount_cents ELSE 0 END), 0) as expense_cents
            FROM transactions
            WHERE date >= ? AND date < ?
        """,
            (start_date, end_date),
        ).fetchone()
        total_income = _to_dec(totals["income_cents"])
        total_expense = _to_dec(totals["expense_cents"])

        # Running balance: everything recorded before this month.
        carryover = cursor.execute(
            """
            SELECT COALESCE(SUM(
                CASE WHEN kind = 'ingreso' THEN amount_cents
                     WHEN kind IN ('gasto', 'pago_tc') THEN -amount_cents
                     ELSE 0 END
            ), 0) as cents
            FROM transactions
            WHERE date < ?
        """,
            (start_date,),
        ).fetchone()
        carryover_dec = _to_dec(carryover["cents"])
        # Opening balances belong to no month: they sit before all time
        # so the accumulated balance still equals the sum of accounts.
        opening = cursor.execute(
            "SELECT COALESCE(SUM(starting_cents), 0) as cents FROM accounts"
        ).fetchone()
        carryover_dec += _to_dec(opening["cents"])
        balance = total_income - total_expense

        return MonthlySummary(
            month=month,
            year=year,
            total_income=total_income,
            total_expense=total_expense,
            balance=balance,
            carryover=carryover_dec,
            accumulated_balance=carryover_dec + balance,
            by_category=by_category,
        )


def get_monthly_summaries(year: int) -> list[MonthlySummary]:
    """Return the monthly summary for every month of a year."""
    return [get_monthly_summary(m, year) for m in range(1, 13)]


def get_category_spending(
    month: int, year: int, cat_type: str = "expense"
) -> list[tuple[str, Decimal, str, str]]:
    """Return (name, total, color, icon) spending by category.

    Expenses include gasto and gasto_tc kinds; income only ingreso.
    Card purchases are counted in the month their statement is paid.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        start_date, end_date = _month_window(month, year)

        if cat_type == "income":
            cursor.execute(
                """
                SELECT c.name, SUM(t.amount_cents) as total_cents, c.color, c.icon
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE t.kind = 'ingreso' AND t.date >= ? AND t.date < ?
                GROUP BY c.id
                ORDER BY total_cents DESC
            """,
                (start_date, end_date),
            )
            return [
                (row["name"], _to_dec(row["total_cents"]), row["color"], row["icon"])
                for row in cursor.fetchall()
            ]

        # Expense: real expenses by purchase date, plus card purchases
        # attributed to their statement's payment month.
        cursor.execute(
            """
            SELECT c.id, c.name, SUM(t.amount_cents) as total_cents, c.color, c.icon
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.kind = 'gasto' AND t.date >= ? AND t.date < ?
            GROUP BY c.id
        """,
            (start_date, end_date),
        )
        agg: dict[int, list[Any]] = {}
        for row in cursor.fetchall():
            agg[row["id"]] = [row["name"], _to_dec(row["total_cents"]), row["color"], row["icon"]]

        cursor.execute(
            """
            SELECT t.category_id, t.amount_cents, t.date, t.installments, t.interest_bp,
                   cc.cutoff_day, cc.payment_day, c.name, c.color, c.icon
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            LEFT JOIN credit_cards cc ON t.card_id = cc.id
            WHERE t.kind = 'gasto_tc'
        """
        )
        for row in cursor.fetchall():
            billed = _billed_in(row, year, month)
            if billed is None:
                continue
            cat_id = row["category_id"]
            if cat_id in agg:
                agg[cat_id][1] += _to_dec(billed[1])
            else:
                agg[cat_id] = [row["name"], _to_dec(billed[1]), row["color"], row["icon"]]

        # Savings movements count in the "Ahorro" category, net of
        # withdrawals, without being cash expenses.
        savings_cat = _savings_category(conn)
        if savings_cat is not None:
            net = _savings_net_for_month(conn, month, year)
            if net != 0:
                cat_id = savings_cat["id"]
                if cat_id in agg:
                    agg[cat_id][1] += net
                else:
                    agg[cat_id] = [
                        savings_cat["name"],
                        net,
                        savings_cat["color"],
                        savings_cat["icon"],
                    ]

        result = [(v[0], v[1], v[2], v[3]) for v in agg.values() if v[1] > 0]
        result.sort(key=lambda item: item[1], reverse=True)
        return result


def get_budget_vs_actual(month: int, year: int) -> list[dict[str, Any]]:
    """Return budget vs actual spending per expense category.

    Card purchases count towards the budget of the month their statement
    is paid, not the purchase month.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        start_date, end_date = _month_window(month, year)

        cursor.execute(
            """
            SELECT c.id, c.name, c.color, c.icon,
                   COALESCE(MAX(b.amount_cents), 0) as budget_cents,
                   COALESCE(SUM(t.amount_cents), 0) as actual_cents
            FROM categories c
            LEFT JOIN budgets b ON c.id = b.category_id AND b.month = ? AND b.year = ?
            LEFT JOIN transactions t ON c.id = t.category_id AND t.date >= ? AND t.date < ?
                AND t.kind = 'gasto'
            WHERE c.type = 'expense'
            GROUP BY c.id, c.name, c.color, c.icon
        """,
            (month, year, start_date, end_date),
        )

        rows: dict[int, dict[str, Any]] = {}
        for row in cursor.fetchall():
            rows[row["id"]] = {
                "category_id": row["id"],
                "name": row["name"],
                "color": row["color"],
                "icon": row["icon"],
                "budget": _to_dec(row["budget_cents"]),
                "actual": _to_dec(row["actual_cents"]),
                "reserved": Decimal("0.00"),
            }

        # Card purchases billed in this month, attributed by payment date.
        cursor.execute(
            """
            SELECT t.category_id, t.amount_cents, t.date, t.installments, t.interest_bp,
                   cc.cutoff_day, cc.payment_day
            FROM transactions t
            LEFT JOIN credit_cards cc ON t.card_id = cc.id
            WHERE t.kind = 'gasto_tc'
        """
        )
        for row in cursor.fetchall():
            billed = _billed_in(row, year, month)
            if billed is None:
                continue
            cat = rows.get(row["category_id"])
            if cat is not None:
                cat["actual"] += _to_dec(billed[1])

        # Savings movements fill the "Ahorro" category, net of withdrawals.
        savings_cat = _savings_category(conn)
        if savings_cat is not None:
            cat = rows.get(savings_cat["id"])
            if cat is not None:
                cat["actual"] += _savings_net_for_month(conn, month, year)

        # Money set aside in bolsillos linked to a category (reserves).
        cursor.execute(
            """
            SELECT sv.category_id,
                   SUM(CASE WHEN t.kind = 'ahorro' THEN t.amount_cents
                            WHEN t.kind = 'retiro' THEN -t.amount_cents
                            ELSE 0 END) as cents
            FROM transactions t
            JOIN savings sv ON sv.id = t.savings_id
            WHERE t.kind IN ('ahorro', 'retiro')
              AND sv.category_id IS NOT NULL
              AND t.date >= ? AND t.date < ?
            GROUP BY sv.category_id
        """,
            (start_date, end_date),
        )
        for row in cursor.fetchall():
            cat = rows.get(row["category_id"])
            if cat is not None:
                cat["reserved"] = _to_dec(row["cents"])

        result = []
        for cat in rows.values():
            budget = cat["budget"]
            actual = cat["actual"]
            reserved = cat["reserved"]
            if budget <= 0 and actual <= 0 and reserved <= 0:
                continue
            result.append(
                {
                    "category_id": cat["category_id"],
                    "name": cat["name"],
                    "color": cat["color"],
                    "icon": cat["icon"],
                    "budget": budget,
                    "actual": actual,
                    "reserved": reserved,
                    "remaining": budget - actual if budget > 0 else -actual,
                    "percent": float(actual / budget * 100) if budget > 0 else 0.0,
                }
            )
        result.sort(key=lambda item: item["name"])
        return result


def transactions_to_csv(month: int, year: int) -> str:
    """Build the CSV content of the transactions of a month."""
    import csv
    import io

    txns = get_transactions(month, year)
    cat_map = {c.id: c for c in get_categories()}
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "Fecha",
            "Categoría",
            "Subcategoría",
            "Tipo",
            "Cuenta",
            "Cuenta destino",
            "Monto",
            "Descripción",
            "Recurrente",
        ]
    )
    for t in txns:
        cat = cat_map.get(t.category_id)
        cat_name = cat.name if cat else "—"
        sub_name = t.subcategory_name or ""
        writer.writerow(
            [
                t.date,
                cat_name,
                sub_name,
                TxKind(t.kind).label,
                t.account_name or "",
                t.to_account_name or "",
                str(t.amount),
                t.description or "",
                "Sí" if (t.is_recurring or t.generated_from) else "No",
            ]
        )
    return buffer.getvalue()


def export_transactions_csv(month: int, year: int, filepath: str) -> None:
    """Write the transactions of a month to a CSV file."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        f.write(transactions_to_csv(month, year))
