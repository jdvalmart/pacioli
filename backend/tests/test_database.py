"""Tests for the SQLite data layer."""

import os
import tempfile
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.database import (
    LEGACY_DB_PATH,
    add_category,
    add_transaction,
    delete_category,
    ensure_recurring,
    get_budget_vs_actual,
    get_budgets,
    get_categories,
    get_monthly_summary,
    get_transactions,
    init_db,
    set_budget,
    set_db_path,
)


@pytest.fixture
def temp_db() -> Iterator[str]:
    """Create a temporary database for the test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        set_db_path(db_path)
        init_db()
        yield db_path
        set_db_path(None)


@pytest.fixture
def sample_category(temp_db: str) -> int:
    """Create a sample expense category and return its id."""
    return add_category("Test", "expense", "#FF0000", "🧪")


class TestTransactions:
    """Tests for transactions."""

    def test_add_and_get_transaction(self, temp_db: str, sample_category: int) -> None:
        trans_id = add_transaction(
            date(2026, 1, 15), Decimal("100.50"), sample_category, "Test transaction"
        )
        assert trans_id > 0

        transactions = get_transactions(1, 2026)
        assert len(transactions) == 1
        assert transactions[0].amount == Decimal("100.50")
        assert transactions[0].description == "Test transaction"
        assert transactions[0].date == date(2026, 1, 15)

    def test_transaction_decimal_precision(self, temp_db: str, sample_category: int) -> None:
        add_transaction(date(2026, 1, 1), Decimal("0.10"), sample_category, "A")
        add_transaction(date(2026, 1, 2), Decimal("0.20"), sample_category, "B")

        summary = get_monthly_summary(1, 2026)
        # Must be exactly 0.30, never 0.30000000000000004
        assert summary.total_expense == Decimal("0.30")

    def test_transactions_filtered_by_month(self, temp_db: str, sample_category: int) -> None:
        add_transaction(date(2026, 1, 31), Decimal("10.00"), sample_category, "January")
        add_transaction(date(2026, 2, 1), Decimal("20.00"), sample_category, "February")

        january = get_transactions(1, 2026)
        assert len(january) == 1
        assert january[0].description == "January"


class TestBudgets:
    """Tests for budgets."""

    def test_set_and_get_budget(self, temp_db: str, sample_category: int) -> None:
        set_budget(sample_category, 1, 2026, Decimal("500.00"))
        budgets = get_budgets(1, 2026)

        assert len(budgets) == 1
        assert budgets[0].amount == Decimal("500.00")

    def test_budget_upsert(self, temp_db: str, sample_category: int) -> None:
        set_budget(sample_category, 1, 2026, Decimal("500.00"))
        set_budget(sample_category, 1, 2026, Decimal("700.00"))
        budgets = get_budgets(1, 2026)

        assert len(budgets) == 1
        assert budgets[0].amount == Decimal("700.00")

    def test_budget_vs_actual(self, temp_db: str, sample_category: int) -> None:
        set_budget(sample_category, 1, 2026, Decimal("1000.00"))
        add_transaction(date(2026, 1, 10), Decimal("250.00"), sample_category, "Spend")

        rows = get_budget_vs_actual(1, 2026)
        assert len(rows) == 1
        assert rows[0]["budget"] == Decimal("1000.00")
        assert rows[0]["actual"] == Decimal("250.00")
        assert rows[0]["remaining"] == Decimal("750.00")
        assert rows[0]["percent"] == 25.0


class TestRecurring:
    """Tests for recurring transactions."""

    def test_recurring_transaction_materialization(
        self, temp_db: str, sample_category: int
    ) -> None:
        template_id = add_transaction(
            date(2026, 1, 15),
            Decimal("1000.00"),
            sample_category,
            "Monthly rent",
            is_recurring=True,
            recurring_day=15,
        )

        created = ensure_recurring(2, 2026)
        assert created == 1

        feb_transactions = get_transactions(2, 2026)
        assert len(feb_transactions) == 1
        assert feb_transactions[0].generated_from == template_id
        assert feb_transactions[0].date == date(2026, 2, 15)

    def test_recurring_idempotency(self, temp_db: str, sample_category: int) -> None:
        add_transaction(
            date(2026, 1, 15),
            Decimal("1000.00"),
            sample_category,
            "Monthly rent",
            is_recurring=True,
            recurring_day=15,
        )

        created1 = ensure_recurring(2, 2026)
        created2 = ensure_recurring(2, 2026)

        assert created1 == 1
        assert created2 == 0

    def test_recurring_day_adjustment(self, temp_db: str, sample_category: int) -> None:
        add_transaction(
            date(2026, 1, 31),
            Decimal("500.00"),
            sample_category,
            "End of month",
            is_recurring=True,
            recurring_day=31,
        )

        # February 2026 has 28 days
        ensure_recurring(2, 2026)
        feb_transactions = get_transactions(2, 2026)

        assert len(feb_transactions) == 1
        assert feb_transactions[0].date == date(2026, 2, 28)


class TestCategories:
    """Tests for category management."""

    def test_default_categories_seeded(self, temp_db: str) -> None:
        categories = get_categories()
        names = {c.name for c in categories}
        assert "Vivienda" in names
        assert "Salario" in names

    def test_delete_category_with_transactions_raises(
        self, temp_db: str, sample_category: int
    ) -> None:
        add_transaction(date(2026, 1, 10), Decimal("100.00"), sample_category, "Keep")

        with pytest.raises(ValueError, match="No se puede eliminar"):
            delete_category(sample_category)


class TestPaths:
    """Tests for path resolution."""

    def test_legacy_db_path_points_to_repo_data_dir(self) -> None:
        """The legacy database lives at <repo>/data/budget.db.

        Regresion guard: the path is built with relative hops from the
        app package and must land inside the repository, not its parent.
        """
        repo_root = Path(__file__).resolve().parents[2]
        assert Path(LEGACY_DB_PATH) == repo_root / "data" / "budget.db"
