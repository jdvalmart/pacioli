"""Integration tests for the Pacioli API."""

from fastapi.testclient import TestClient


def _create_category(client: TestClient, name: str = "Test") -> int:
    response = client.post(
        "/api/categories", json={"name": name, "type": "expense", "color": "#FF0000", "icon": "🧪"}
    )
    assert response.status_code == 201
    return int(response.json()["id"])


_account_counter = 0


def _create_account(client: TestClient) -> int:
    global _account_counter
    _account_counter += 1
    response = client.post(
        "/api/accounts",
        json={
            "name": f"Billetera {_account_counter}",
            "type": "efectivo",
            "starting_amount": "0.00",
        },
    )
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def _create_transaction(client: TestClient, cat_id: int, **overrides: object) -> dict:
    payload = {
        "date": "2026-01-15",
        "amount": "100.50",
        "category_id": cat_id,
        "account_id": _create_account(client),
        "description": "Test transaction",
        **overrides,
    }
    response = client.post("/api/transactions", json=payload)
    assert response.status_code == 201, response.text
    return dict(response.json())


class TestHealth:
    """Tests for the health endpoint."""

    def test_health(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestCategories:
    """Tests for category endpoints."""

    def test_list_seeded_categories(self, client: TestClient) -> None:
        response = client.get("/api/categories")
        assert response.status_code == 200
        names = {c["name"] for c in response.json()}
        assert "Vivienda" in names
        assert "Salario" in names

    def test_list_filtered_by_type(self, client: TestClient) -> None:
        response = client.get("/api/categories?type=income")
        assert response.status_code == 200
        assert all(c["type"] == "income" for c in response.json())

    def test_create_category(self, client: TestClient) -> None:
        cat_id = _create_category(client)
        assert cat_id > 0

    def test_create_duplicate_category_conflict(self, client: TestClient) -> None:
        _create_category(client, "Duplicated")
        response = client.post("/api/categories", json={"name": "Duplicated", "type": "expense"})
        assert response.status_code == 409

    def test_update_category(self, client: TestClient) -> None:
        cat_id = _create_category(client)
        response = client.put(
            f"/api/categories/{cat_id}",
            json={"name": "Renamed", "color": "#00FF00", "icon": "🔧"},
        )
        assert response.status_code == 200

        categories = client.get("/api/categories").json()
        renamed = next(c for c in categories if c["id"] == cat_id)
        assert renamed["name"] == "Renamed"

    def test_delete_category_with_transactions_fails(self, client: TestClient) -> None:
        cat_id = _create_category(client)
        _create_transaction(client, cat_id)

        response = client.delete(f"/api/categories/{cat_id}")
        assert response.status_code == 400

    def test_delete_category_ok(self, client: TestClient) -> None:
        cat_id = _create_category(client)
        response = client.delete(f"/api/categories/{cat_id}")
        assert response.status_code == 200


class TestSubcategories:
    """Tests for subcategory endpoints."""

    def test_list_subcategories_of_category(self, client: TestClient) -> None:
        servicios = next(
            c for c in client.get("/api/categories").json() if c["name"] == "Servicios"
        )
        response = client.get(f"/api/categories/{servicios['id']}/subcategories")
        assert response.status_code == 200
        names = {s["name"] for s in response.json()}
        assert "Agua" in names
        assert "Internet" in names

    def test_create_and_delete_subcategory(self, client: TestClient) -> None:
        cat_id = _create_category(client)
        response = client.post(
            f"/api/categories/{cat_id}/subcategories", json={"name": "Comida rápida"}
        )
        assert response.status_code == 201
        sub_id = response.json()["id"]

        delete_response = client.delete(f"/api/categories/subcategories/{sub_id}")
        assert delete_response.status_code == 200


class TestTransactions:
    """Tests for transaction endpoints."""

    def test_create_and_list_transaction(self, client: TestClient) -> None:
        cat_id = _create_category(client)
        _create_transaction(client, cat_id)

        response = client.get("/api/transactions?month=1&year=2026")
        assert response.status_code == 200
        transactions = response.json()
        assert len(transactions) == 1
        tx = transactions[0]
        # Amounts serialize as strings to preserve precision
        assert tx["amount"] == "100.50"
        assert tx["category_name"] == "Test"
        assert tx["date"] == "2026-01-15"

    def test_create_with_unknown_category_fails(self, client: TestClient) -> None:
        response = client.post(
            "/api/transactions",
            json={
                "date": "2026-01-15",
                "amount": "10.00",
                "category_id": 9999,
                "account_id": _create_account(client),
                "description": "Bad",
            },
        )
        assert response.status_code == 400

    def test_create_without_account_rejected(self, client: TestClient) -> None:
        cat_id = _create_category(client)
        response = client.post(
            "/api/transactions",
            json={"date": "2026-01-15", "amount": "10.00", "category_id": cat_id},
        )
        assert response.status_code == 400

    def test_create_with_negative_amount_fails(self, client: TestClient) -> None:
        cat_id = _create_category(client)
        response = client.post(
            "/api/transactions",
            json={
                "date": "2026-01-15",
                "amount": "-5.00",
                "category_id": cat_id,
                "account_id": _create_account(client),
            },
        )
        assert response.status_code == 422

    def test_update_transaction(self, client: TestClient) -> None:
        cat_id = _create_category(client)
        trans_id = _create_transaction(client, cat_id)["id"]

        response = client.put(
            f"/api/transactions/{trans_id}",
            json={
                "date": "2026-01-20",
                "amount": "200.00",
                "category_id": cat_id,
                "account_id": _create_account(client),
                "description": "Updated",
            },
        )
        assert response.status_code == 200

        tx = client.get("/api/transactions?month=1&year=2026").json()[0]
        assert tx["amount"] == "200.00"
        assert tx["description"] == "Updated"

    def test_delete_transaction(self, client: TestClient) -> None:
        cat_id = _create_category(client)
        trans_id = _create_transaction(client, cat_id)["id"]

        response = client.delete(f"/api/transactions/{trans_id}")
        assert response.status_code == 200
        assert client.get("/api/transactions?month=1&year=2026").json() == []

    def test_invalid_month_rejected(self, client: TestClient) -> None:
        response = client.get("/api/transactions?month=13&year=2026")
        assert response.status_code == 422


class TestRecurring:
    """Tests for recurring materialization."""

    def test_materialize_creates_instances_once(self, client: TestClient) -> None:
        cat_id = _create_category(client)
        _create_transaction(
            client,
            cat_id,
            date="2026-01-15",
            amount="1000.00",
            description="Monthly rent",
            is_recurring=True,
            recurring_day=15,
        )

        first = client.post("/api/transactions/materialize?month=2&year=2026")
        assert first.status_code == 200
        assert first.json() == {"created": 1}

        second = client.post("/api/transactions/materialize?month=2&year=2026")
        assert second.json() == {"created": 0}

        february = client.get("/api/transactions?month=2&year=2026").json()
        assert len(february) == 1
        assert february[0]["date"] == "2026-02-15"
        assert february[0]["is_recurring"] is False


class TestBudgets:
    """Tests for budget endpoints."""

    def test_upsert_and_list_budget(self, client: TestClient) -> None:
        cat_id = _create_category(client)

        response = client.put(
            "/api/budgets",
            json={"category_id": cat_id, "month": 1, "year": 2026, "amount": "500.00"},
        )
        assert response.status_code == 200

        budgets = client.get("/api/budgets?month=1&year=2026").json()
        assert len(budgets) == 1
        assert budgets[0]["amount"] == "500.00"

    def test_budget_upsert_overwrites(self, client: TestClient) -> None:
        cat_id = _create_category(client)
        payload = {"category_id": cat_id, "month": 1, "year": 2026}

        client.put("/api/budgets", json={**payload, "amount": "500.00"})
        client.put("/api/budgets", json={**payload, "amount": "700.00"})

        budgets = client.get("/api/budgets?month=1&year=2026").json()
        assert len(budgets) == 1
        assert budgets[0]["amount"] == "700.00"

    def test_delete_budget(self, client: TestClient) -> None:
        cat_id = _create_category(client)
        client.put(
            "/api/budgets",
            json={"category_id": cat_id, "month": 1, "year": 2026, "amount": "500.00"},
        )

        response = client.delete(f"/api/budgets?category_id={cat_id}&month=1&year=2026")
        assert response.status_code == 200
        assert client.get("/api/budgets?month=1&year=2026").json() == []


class TestReports:
    """Tests for report endpoints."""

    def test_monthly_summary(self, client: TestClient) -> None:
        expense_cat = _create_category(client, "Gasto")
        income_cat = client.post(
            "/api/categories", json={"name": "Ingreso", "type": "income"}
        ).json()["id"]

        _create_transaction(client, expense_cat, date="2026-01-05", amount="150.00")
        _create_transaction(client, income_cat, date="2026-01-10", amount="1000.00", kind="ingreso")

        response = client.get("/api/reports/summary?month=1&year=2026")
        assert response.status_code == 200
        summary = response.json()
        assert summary["total_income"] == "1000.00"
        assert summary["total_expense"] == "150.00"
        assert summary["balance"] == "850.00"
        assert summary["carryover"] == "0.00"
        assert summary["accumulated_balance"] == "850.00"

    def test_yearly_summaries(self, client: TestClient) -> None:
        response = client.get("/api/reports/monthly?year=2026")
        assert response.status_code == 200
        assert len(response.json()) == 12

    def test_category_spending(self, client: TestClient) -> None:
        cat_id = _create_category(client)
        _create_transaction(client, cat_id, amount="300.00")

        response = client.get("/api/reports/category-spending?month=1&year=2026")
        assert response.status_code == 200
        rows = response.json()
        assert rows[0]["name"] == "Test"
        assert rows[0]["total"] == "300.00"

    def test_budget_vs_actual(self, client: TestClient) -> None:
        cat_id = _create_category(client)
        client.put(
            "/api/budgets",
            json={"category_id": cat_id, "month": 1, "year": 2026, "amount": "1000.00"},
        )
        _create_transaction(client, cat_id, amount="250.00")

        response = client.get("/api/reports/budget-vs-actual?month=1&year=2026")
        assert response.status_code == 200
        rows = response.json()
        assert rows[0]["budget"] == "1000.00"
        assert rows[0]["actual"] == "250.00"
        assert rows[0]["remaining"] == "750.00"
        assert rows[0]["percent"] == 25.0

    def test_export_csv(self, client: TestClient) -> None:
        cat_id = _create_category(client)
        _create_transaction(client, cat_id, description="Comida")

        response = client.get("/api/reports/export?month=1&year=2026")
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "Comida" in response.text
        assert "Fecha" in response.text


class TestAccounts:
    """Tests for account endpoints."""

    def test_create_and_list_accounts(self, client: TestClient) -> None:
        response = client.post(
            "/api/accounts",
            json={"name": "Billetera", "type": "efectivo", "starting_amount": "200.00"},
        )
        assert response.status_code == 201

        accounts = client.get("/api/accounts").json()
        assert len(accounts) == 1
        assert accounts[0]["name"] == "Billetera"
        assert accounts[0]["icon"] == "💵"
        assert accounts[0]["balance"] == "200.00"

    def test_starting_amount_counts_as_income(self, client: TestClient) -> None:
        client.post(
            "/api/accounts",
            json={"name": "Ahorros", "type": "ahorros", "starting_amount": "500.00"},
        )

        summary = client.get("/api/reports/summary?month=9&year=2026").json()
        assert summary["total_income"] == "500.00"

        transactions = client.get("/api/transactions?month=9&year=2026").json()
        assert len(transactions) == 1
        assert transactions[0]["description"] == "Saldo inicial: Ahorros"
        assert transactions[0]["category_type"] == "income"

    def test_account_balance_reflects_transactions(self, client: TestClient) -> None:
        account_id = client.post(
            "/api/accounts",
            json={"name": "Nequi", "type": "digital", "starting_amount": "100.00"},
        ).json()["id"]
        income_cat = client.post(
            "/api/categories", json={"name": "Ingreso", "type": "income"}
        ).json()["id"]
        expense_cat = client.post(
            "/api/categories", json={"name": "Gasto", "type": "expense"}
        ).json()["id"]

        client.post(
            "/api/transactions",
            json={
                "date": "2026-09-01",
                "amount": "500.00",
                "kind": "ingreso",
                "category_id": income_cat,
                "account_id": account_id,
            },
        )
        client.post(
            "/api/transactions",
            json={
                "date": "2026-09-02",
                "amount": "150.00",
                "category_id": expense_cat,
                "account_id": account_id,
            },
        )

        accounts = client.get("/api/accounts").json()
        assert accounts[0]["balance"] == "450.00"

        transactions = client.get("/api/transactions?month=9&year=2026").json()
        linked = [t for t in transactions if t["account_id"] == account_id]
        assert len(linked) == 3  # starting amount + the two movements
        assert all(t["account_name"] == "Nequi" for t in linked)

    def test_duplicate_account_name_conflict(self, client: TestClient) -> None:
        client.post(
            "/api/accounts", json={"name": "Ahorro", "type": "ahorros", "starting_amount": "0.00"}
        )
        response = client.post(
            "/api/accounts", json={"name": "Ahorro", "type": "ahorros", "starting_amount": "0.00"}
        )
        assert response.status_code == 409

    def test_update_and_delete_account(self, client: TestClient) -> None:
        account_id = client.post(
            "/api/accounts",
            json={"name": "Banco", "type": "banco", "starting_amount": "1000.00"},
        ).json()["id"]

        response = client.put(f"/api/accounts/{account_id}", json={"name": "Banco principal"})
        assert response.status_code == 200

        accounts = client.get("/api/accounts").json()
        assert accounts[0]["name"] == "Banco principal"
        assert accounts[0]["balance"] == "1000.00"

        assert client.delete(f"/api/accounts/{account_id}").status_code == 200
        assert client.get("/api/accounts").json() == []


class TestCreditCards:
    """Tests for credit card endpoints."""

    def test_create_and_list_cards(self, client: TestClient) -> None:
        response = client.post(
            "/api/credit-cards",
            json={
                "name": "Visa Bancolombia",
                "limit": "5000000.00",
                "cutoff_day": 15,
                "payment_day": 30,
            },
        )
        assert response.status_code == 201

        cards = client.get("/api/credit-cards").json()
        assert len(cards) == 1
        assert cards[0]["name"] == "Visa Bancolombia"
        assert cards[0]["limit"] == "5000000.00"
        assert cards[0]["available"] == "5000000.00"
        assert cards[0]["spent"] == "0.00"

    def test_available_credit_reflects_tc_spending(self, client: TestClient) -> None:
        card_id = client.post(
            "/api/credit-cards",
            json={"name": "Mastercard", "limit": "1000000.00", "cutoff_day": 10, "payment_day": 25},
        ).json()["id"]
        expense_cat = client.post(
            "/api/categories", json={"name": "Gasto", "type": "expense"}
        ).json()["id"]

        client.post(
            "/api/transactions",
            json={
                "date": "2026-09-10",
                "amount": "250000.00",
                "kind": "gasto_tc",
                "category_id": expense_cat,
                "card_id": card_id,
            },
        )

        cards = client.get("/api/credit-cards").json()
        assert cards[0]["spent"] == "250000.00"
        assert cards[0]["available"] == "750000.00"

        transactions = client.get("/api/transactions?month=9&year=2026").json()
        assert transactions[0]["card_name"] == "Mastercard"

    def test_gasto_tc_without_card_rejected(self, client: TestClient) -> None:
        expense_cat = client.post(
            "/api/categories", json={"name": "Gasto", "type": "expense"}
        ).json()["id"]
        response = client.post(
            "/api/transactions",
            json={
                "date": "2026-09-10",
                "amount": "100.00",
                "kind": "gasto_tc",
                "category_id": expense_cat,
            },
        )
        assert response.status_code == 400

    def test_update_and_delete_card(self, client: TestClient) -> None:
        card_id = client.post(
            "/api/credit-cards",
            json={"name": "Visa", "limit": "1000000.00", "cutoff_day": 10, "payment_day": 25},
        ).json()["id"]

        response = client.put(
            f"/api/credit-cards/{card_id}",
            json={"name": "Visa Oro", "limit": "2000000.00", "cutoff_day": 12, "payment_day": 28},
        )
        assert response.status_code == 200

        cards = client.get("/api/credit-cards").json()
        assert cards[0]["name"] == "Visa Oro"
        assert cards[0]["limit"] == "2000000.00"

        assert client.delete(f"/api/credit-cards/{card_id}").status_code == 200
        assert client.get("/api/credit-cards").json() == []


class TestCardPayments:
    """Tests for the credit card payment flow."""

    def test_pay_card_moves_money_and_clears_debt(self, client: TestClient, monkeypatch) -> None:
        from datetime import date as _date

        class FakeDate:
            @staticmethod
            def today() -> _date:
                return _date(2026, 9, 20)

        monkeypatch.setattr("app.routers.transactions.date", FakeDate)

        card_id = client.post(
            "/api/credit-cards",
            json={"name": "Visa", "limit": "1000000.00", "cutoff_day": 15, "payment_day": 30},
        ).json()["id"]
        account_id = client.post(
            "/api/accounts",
            json={"name": "Banco", "type": "banco", "starting_amount": "3000000.00"},
        ).json()["id"]
        expense_cat = client.post(
            "/api/categories", json={"name": "Gasto", "type": "expense"}
        ).json()["id"]

        client.post(
            "/api/transactions",
            json={
                "date": "2026-09-10",
                "amount": "400000.00",
                "kind": "gasto_tc",
                "category_id": expense_cat,
                "card_id": card_id,
            },
        )

        response = client.post(
            "/api/transactions",
            json={
                "date": "2026-09-18",
                "amount": "400000.00",
                "kind": "pago_tc",
                "account_id": account_id,
                "card_id": card_id,
            },
        )
        assert response.status_code == 201, response.text

        cards = client.get("/api/credit-cards").json()
        assert cards[0]["debt"] == "0.00"
        assert cards[0]["paid"] == "400000.00"

        accounts = client.get("/api/accounts").json()
        assert accounts[0]["balance"] == "2600000.00"

    def test_payment_rejected_without_funds(self, client: TestClient, monkeypatch) -> None:
        from datetime import date as _date

        class FakeDate:
            @staticmethod
            def today() -> _date:
                return _date(2026, 9, 20)

        monkeypatch.setattr("app.routers.transactions.date", FakeDate)

        card_id = client.post(
            "/api/credit-cards",
            json={"name": "Visa", "limit": "1000000.00", "cutoff_day": 15, "payment_day": 30},
        ).json()["id"]
        account_id = client.post(
            "/api/accounts",
            json={"name": "Billetera", "type": "efectivo", "starting_amount": "0.00"},
        ).json()["id"]
        expense_cat = client.post(
            "/api/categories", json={"name": "Gasto", "type": "expense"}
        ).json()["id"]

        client.post(
            "/api/transactions",
            json={
                "date": "2026-09-10",
                "amount": "400000.00",
                "kind": "gasto_tc",
                "category_id": expense_cat,
                "card_id": card_id,
            },
        )

        response = client.post(
            "/api/transactions",
            json={
                "date": "2026-09-18",
                "amount": "400000.00",
                "kind": "pago_tc",
                "account_id": account_id,
                "card_id": card_id,
            },
        )
        assert response.status_code == 400
        assert "Insufficient balance" in response.json()["detail"]

    def test_payment_rejected_before_cutoff(self, client: TestClient, monkeypatch) -> None:
        from datetime import date as _date

        class FakeDate:
            @staticmethod
            def today() -> _date:
                return _date(2026, 9, 10)  # before the cutoff (day 15)

        monkeypatch.setattr("app.routers.transactions.date", FakeDate)

        card_id = client.post(
            "/api/credit-cards",
            json={"name": "Visa", "limit": "1000000.00", "cutoff_day": 15, "payment_day": 30},
        ).json()["id"]
        account_id = client.post(
            "/api/accounts",
            json={"name": "Banco", "type": "banco", "starting_amount": "3000000.00"},
        ).json()["id"]

        response = client.post(
            "/api/transactions",
            json={
                "date": "2026-09-10",
                "amount": "100.00",
                "kind": "pago_tc",
                "account_id": account_id,
                "card_id": card_id,
            },
        )
        assert response.status_code == 400
        assert "after the cutoff" in response.json()["detail"]

    def test_payment_exceeding_debt_rejected(self, client: TestClient, monkeypatch) -> None:
        from datetime import date as _date

        class FakeDate:
            @staticmethod
            def today() -> _date:
                return _date(2026, 9, 20)

        monkeypatch.setattr("app.routers.transactions.date", FakeDate)

        card_id = client.post(
            "/api/credit-cards",
            json={"name": "Visa", "limit": "1000000.00", "cutoff_day": 15, "payment_day": 30},
        ).json()["id"]
        account_id = client.post(
            "/api/accounts",
            json={"name": "Banco", "type": "banco", "starting_amount": "3000000.00"},
        ).json()["id"]
        expense_cat = client.post(
            "/api/categories", json={"name": "Gasto", "type": "expense"}
        ).json()["id"]

        client.post(
            "/api/transactions",
            json={
                "date": "2026-09-10",
                "amount": "100000.00",
                "kind": "gasto_tc",
                "category_id": expense_cat,
                "card_id": card_id,
            },
        )

        response = client.post(
            "/api/transactions",
            json={
                "date": "2026-09-18",
                "amount": "200000.00",
                "kind": "pago_tc",
                "account_id": account_id,
                "card_id": card_id,
            },
        )
        assert response.status_code == 400
        assert "exceeds the current debt" in response.json()["detail"]
