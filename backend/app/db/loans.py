"""Loans: credits other than cards, their payments and derived status."""

from datetime import date
from decimal import Decimal

from app import clock
from app.db.connection import _ddl, _insert_get_id, _to_cents, _to_dec, get_connection
from app.db.models import Loan
from app.domain import loans as rules


def get_loans(today: date | None = None) -> list[Loan]:
    """All loans with their balance today and payoff projection."""
    today = today or clock.today()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM loans ORDER BY created_at, id").fetchall()
        result = []
        for row in rows:
            payments = [
                rules.Payment(date.fromisoformat(p["date"]), int(p["amount_cents"]))
                for p in conn.execute(
                    "SELECT date, amount_cents FROM transactions WHERE loan_id = ? AND kind = 'gasto'",
                    (row["id"],),
                ).fetchall()
            ]
            status = rules.loan_status(
                int(row["balance_cents"]),
                date.fromisoformat(row["as_of"]),
                row["rate_bp"],
                int(row["installment_cents"]),
                payments,
                today,
            )
            result.append(
                Loan(
                    id=row["id"],
                    name=row["name"],
                    balance=_to_dec(row["balance_cents"]),
                    as_of=date.fromisoformat(row["as_of"]),
                    rate_bp=row["rate_bp"],
                    installment=_to_dec(row["installment_cents"]),
                    payment_day=row["payment_day"],
                    category_id=row["category_id"],
                    current_balance=_to_dec(status.balance_cents),
                    paid=_to_dec(status.paid_cents),
                    interest=_to_dec(status.interest_cents),
                    remaining_installments=status.remaining_installments,
                    payoff=status.payoff,
                )
            )
        return result


def add_loan(
    name: str,
    balance: Decimal,
    as_of: date,
    installment: Decimal,
    rate_bp: int | None = None,
    payment_day: int | None = None,
    category_id: int | None = None,
) -> int:
    """Create a loan from the balance confirmed with the bank on ``as_of``."""
    with get_connection() as conn:
        sql = _ddl(
            "INSERT INTO loans (name, balance_cents, as_of, rate_bp, installment_cents, "
            "payment_day, category_id) VALUES (?, ?, ?, ?, ?, ?, ?)"
        )
        new_id = _insert_get_id(
            conn.cursor(),
            sql,
            (
                name,
                _to_cents(balance),
                as_of.isoformat(),
                rate_bp,
                _to_cents(installment),
                payment_day,
                category_id,
            ),
        )
        conn.commit()
        return new_id


def update_loan(
    loan_id: int,
    name: str,
    balance: Decimal,
    as_of: date,
    installment: Decimal,
    rate_bp: int | None = None,
    payment_day: int | None = None,
    category_id: int | None = None,
) -> None:
    """Edit a loan; a new balance/as_of re-anchors it to what the bank shows."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE loans SET name = ?, balance_cents = ?, as_of = ?, rate_bp = ?, "
            "installment_cents = ?, payment_day = ?, category_id = ? WHERE id = ?",
            (
                name,
                _to_cents(balance),
                as_of.isoformat(),
                rate_bp,
                _to_cents(installment),
                payment_day,
                category_id,
                loan_id,
            ),
        )
        conn.commit()


def delete_loan(loan_id: int) -> None:
    """Delete a loan; its payments stay as ordinary expenses."""
    with get_connection() as conn:
        conn.execute("UPDATE transactions SET loan_id = NULL WHERE loan_id = ?", (loan_id,))
        conn.execute("DELETE FROM loans WHERE id = ?", (loan_id,))
        conn.commit()
