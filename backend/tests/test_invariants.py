"""Characterization tests for the ledger's cross-cutting invariants.

They pin the money rules that span several endpoints (accounts,
savings, cards, reports) so the planned refactors of ``database.py``
can move code freely: if any of these fail, behaviour changed.

One scenario covers every movement kind; the clock is frozen because
card cycles depend on "today".
"""

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

TODAY = date(2026, 10, 20)  # Inside the Oct 10 -> Nov 10 card cycle.


def _d(value: str) -> Decimal:
    return Decimal(value)


@pytest.fixture
def ledger(client: TestClient, freeze_today) -> dict[str, Any]:
    """Book one movement of every kind across September and October 2026.

    Card: cutoff 10, payment 25. The Sep 5 purchase closes on Sep 10 and
    is paid on Sep 25, in 3 interest-free installments (Sep, Oct, Nov).
    """
    freeze_today(TODAY)
    categories = client.get("/api/categories").json()
    income = next(c["id"] for c in categories if c["type"] == "income")
    expense = client.post("/api/categories", json={"name": "Mercado", "type": "expense"}).json()[
        "id"
    ]

    a = client.post(
        "/api/accounts", json={"name": "A", "type": "banco", "starting_amount": "1000000"}
    ).json()["id"]
    b = client.post(
        "/api/accounts", json={"name": "B", "type": "efectivo", "starting_amount": "0"}
    ).json()["id"]
    card = client.post(
        "/api/credit-cards",
        json={"name": "Visa", "limit": "2000000", "cutoff_day": 10, "payment_day": 25},
    ).json()["id"]
    pocket = client.post("/api/savings", json={"name": "Bolsa", "kind": "bolsillo"}).json()["id"]

    movements = [
        {"date": "2026-09-01", "amount": "500000", "kind": "ingreso", "category_id": income,
         "account_id": a},
        {"date": "2026-09-03", "amount": "100000", "kind": "gasto", "category_id": expense,
         "account_id": a},
        {"date": "2026-09-04", "amount": "200000", "kind": "transferencia", "account_id": a,
         "to_account_id": b},
        {"date": "2026-09-05", "amount": "300000", "kind": "gasto_tc", "category_id": expense,
         "card_id": card, "installments": 3},
        {"date": "2026-09-06", "amount": "50000", "kind": "ahorro", "account_id": a,
         "savings_id": pocket},
        {"date": "2026-09-07", "amount": "20000", "kind": "retiro", "account_id": a,
         "savings_id": pocket},
        {"date": "2026-10-15", "amount": "100000", "kind": "pago_tc", "account_id": a,
         "card_id": card},
    ]  # fmt: skip
    for payload in movements:
        response = client.post("/api/transactions", json=payload)
        assert response.status_code == 201, response.text

    return {"client": client, "a": a, "b": b, "card": card, "expense": expense}


def _summary(client: TestClient, month: int) -> dict[str, Any]:
    summary: dict[str, Any] = client.get(f"/api/reports/summary?month={month}&year=2026").json()
    return summary


class TestAccountBalances:
    def test_balance_formula_per_account(self, ledger: dict[str, Any]) -> None:
        """starting + ingreso - gasto - pago_tc +- transfer - ahorro + retiro."""
        balances = {a["id"]: _d(a["balance"]) for a in ledger["client"].get("/api/accounts").json()}
        assert (
            balances[ledger["a"]]
            == _d("1000000") + 500000 - 100000 - 200000 - 50000 + 20000 - 100000
        )
        assert balances[ledger["b"]] == _d("200000")

    def test_card_purchase_does_not_move_cash(self, ledger: dict[str, Any]) -> None:
        """gasto_tc only hits the accounts when the card is paid (pago_tc)."""
        total = sum(_d(a["balance"]) for a in ledger["client"].get("/api/accounts").json())
        assert total == _d("1000000") + 500000 - 100000 - 50000 + 20000 - 100000


class TestAccumulatedBalance:
    def test_equals_accounts_plus_net_savings(self, ledger: dict[str, Any]) -> None:
        """Accumulated balance = cash in accounts + net money moved to savings.

        Savings movements leave the accounts but not the accumulated
        balance (they are set aside, not spent). Savings opening balances
        are outside both.
        """
        client = ledger["client"]
        accounts = sum(_d(a["balance"]) for a in client.get("/api/accounts").json())
        net_savings = sum(
            _d(s["balance"]) - _d(s["opening"]) for s in client.get("/api/savings").json()
        )
        for month in (10, 11):
            assert _d(_summary(client, month)["accumulated_balance"]) == accounts + net_savings

    def test_months_chain(self, ledger: dict[str, Any]) -> None:
        """Each month's carryover is the previous month's accumulated balance."""
        client = ledger["client"]
        for month in (9, 10, 11):
            previous = _summary(client, month)
            following = _summary(client, month + 1)
            assert following["carryover"] == previous["accumulated_balance"]

    def test_cash_totals_exclude_card_purchases_and_transfers(self, ledger: dict[str, Any]) -> None:
        september = _summary(ledger["client"], 9)
        assert _d(september["total_income"]) == _d("500000")
        assert _d(september["total_expense"]) == _d("100000")  # gasto only
        october = _summary(ledger["client"], 10)
        assert _d(october["total_expense"]) == _d("100000")  # pago_tc


class TestCreditCard:
    def test_outstanding_and_available(self, ledger: dict[str, Any]) -> None:
        card = ledger["client"].get("/api/credit-cards").json()[0]
        assert _d(card["outstanding"]) == _d("200000")  # 300k purchased - 100k paid
        assert _d(card["available"]) == _d(card["limit"]) - _d(card["outstanding"])

    def test_installment_billed_in_open_cycle(self, ledger: dict[str, Any]) -> None:
        card = ledger["client"].get("/api/credit-cards").json()[0]
        assert card["cycle_start"] == "2026-10-10"
        assert card["cycle_end"] == "2026-11-10"
        assert card["payment_date"] == "2026-11-25"
        assert _d(card["pending"]) == _d("100000")  # 3rd of 3 installments

    def test_month_view_of_current_month_uses_today(self, ledger: dict[str, Any]) -> None:
        """?month= of the current month must match the plain listing.

        Regression: the month view used day 15 as "today", which is past
        the cutoff (10) and reported the open statement as already due.
        """
        client = ledger["client"]
        assert (
            client.get("/api/credit-cards?month=10&year=2026").json()
            == client.get("/api/credit-cards").json()
        )

    def test_past_month_view_shows_month_close(self, ledger: dict[str, Any]) -> None:
        """September as of Sep 30 ignores the Oct 15 payment: Sep cuota still owed."""
        card = ledger["client"].get("/api/credit-cards?month=9&year=2026").json()[0]
        assert card["cycle_end"] == "2026-10-10"
        assert _d(card["debt"]) == _d("100000")
        assert _d(card["outstanding"]) == _d("300000")

    def test_debt_is_unpaid_closed_statements(self, ledger: dict[str, Any]) -> None:
        """Sep and Oct statements (200k) closed; one 100k payment -> 100k due now."""
        card = ledger["client"].get("/api/credit-cards").json()[0]
        assert _d(card["debt"]) == _d("100000")


class TestReportsAgree:
    @pytest.mark.parametrize("month", [9, 10, 11])
    def test_expense_views_agree(self, ledger: dict[str, Any], month: int) -> None:
        """Summary, category spending and budget-vs-actual report the same spend."""
        client = ledger["client"]
        by_category = _summary(client, month)["by_category"]
        spending = client.get(f"/api/reports/category-spending?month={month}&year=2026").json()
        bva = client.get(f"/api/reports/budget-vs-actual?month={month}&year=2026").json()

        spending_map = {row["name"]: _d(row["total"]) for row in spending}
        # The savings goal row is not spending (role "savings").
        bva_map = {
            row["name"]: _d(row["actual"])
            for row in bva
            if _d(row["actual"]) > 0 and row["role"] != "savings"
        }
        assert spending_map == bva_map
        for name, total in spending_map.items():
            assert _d(by_category[name]) == total

    def test_installments_spread_over_their_payment_months(self, ledger: dict[str, Any]) -> None:
        """Each cuota counts in the month its statement is due (ADR 0001).

        The 300k purchase in 3 cuotas (Sep 5, cutoff 10, payment 25) is
        billed Sep, Oct and Nov: 100k per month in its category, and the
        purchase is listed once per month as cuota k/3.
        """
        client = ledger["client"]
        expected = {9: _d("200000"), 10: _d("100000"), 11: _d("100000")}  # Sep adds the 100k gasto
        for month, total in expected.items():
            spending = {
                row["name"]: _d(row["total"])
                for row in client.get(
                    f"/api/reports/category-spending?month={month}&year=2026"
                ).json()
            }
            assert spending["Mercado"] == total

            listed = [
                t
                for t in client.get(f"/api/transactions?month={month}&year=2026").json()
                if t["kind"] == "gasto_tc"
            ]
            assert len(listed) == 1
            assert listed[0]["installment_number"] == month - 8
            assert _d(listed[0]["billed_amount"]) == _d("100000")
            assert _d(listed[0]["amount"]) == _d("300000")  # editable purchase amount
