"""Tests para funciones de base de datos."""

import pytest
import tempfile
import os
from datetime import date
from decimal import Decimal
from pacioli.data.database import (
    init_db,
    add_transaction,
    get_transactions,
    add_category,
    get_categories,
    set_budget,
    get_budgets,
    get_monthly_summary,
    ensure_recurring,
    get_connection,
)


@pytest.fixture
def temp_db():
    """Crea una base de datos temporal para tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        # Configurar path temporal
        import pacioli.data.database as db_module
        original_path = db_module.DB_PATH
        db_module.DB_PATH = db_path

        init_db()
        yield db_path

        # Restaurar path original
        db_module.DB_PATH = original_path


@pytest.fixture
def sample_category(temp_db):
    """Crea una categoría de ejemplo."""
    return add_category("Test", "expense", "#FF0000", "🧪")


class TestTransactions:
    """Tests para transacciones."""

    def test_add_and_get_transaction(self, temp_db, sample_category):
        """Test básico de agregar y obtener transacción."""
        cat_id = sample_category
        trans_date = date(2026, 1, 15)
        amount = Decimal("100.50")

        trans_id = add_transaction(trans_date, amount, cat_id, "Test transaction")
        assert trans_id > 0

        transactions = get_transactions(1, 2026)
        assert len(transactions) == 1
        assert transactions[0].amount == amount
        assert transactions[0].description == "Test transaction"

    def test_transaction_decimal_precision(self, temp_db, sample_category):
        """Test de precisión decimal (0.1 + 0.2 = 0.3)."""
        cat_id = sample_category

        add_transaction(date(2026, 1, 1), Decimal("0.10"), cat_id, "A")
        add_transaction(date(2026, 1, 2), Decimal("0.20"), cat_id, "B")

        summary = get_monthly_summary(1, 2026)
        # Debe ser exactamente 0.30, no 0.30000000000000004
        assert summary.total_expense == Decimal("0.30")


class TestBudgets:
    """Tests para presupuestos."""

    def test_set_and_get_budget(self, temp_db, sample_category):
        """Test básico de presupuesto."""
        cat_id = sample_category
        amount = Decimal("500.00")

        set_budget(cat_id, 1, 2026, amount)
        budgets = get_budgets(1, 2026)

        assert len(budgets) == 1
        assert budgets[0].amount == amount


class TestRecurring:
    """Tests para transacciones recurrentes."""

    def test_recurring_transaction_materialization(self, temp_db, sample_category):
        """Test de materialización de transacciones recurrentes."""
        cat_id = sample_category

        # Crear plantilla recurrente en enero
        template_id = add_transaction(
            date(2026, 1, 15),
            Decimal("1000.00"),
            cat_id,
            "Monthly rent",
            is_recurring=True,
            recurring_day=15
        )

        # Materializar para febrero
        created = ensure_recurring(2, 2026)
        assert created == 1

        # Verificar que se creó la instancia
        feb_transactions = get_transactions(2, 2026)
        assert len(feb_transactions) == 1
        assert feb_transactions[0].generated_from == template_id
        assert feb_transactions[0].date == "2026-02-15"

    def test_recurring_idempotency(self, temp_db, sample_category):
        """Test de idempotencia de materialización."""
        cat_id = sample_category

        add_transaction(
            date(2026, 1, 15),
            Decimal("1000.00"),
            cat_id,
            "Monthly rent",
            is_recurring=True,
            recurring_day=15
        )

        # Materializar dos veces
        created1 = ensure_recurring(2, 2026)
        created2 = ensure_recurring(2, 2026)

        assert created1 == 1
        assert created2 == 0  # No debe crear duplicados

    def test_recurring_day_adjustment(self, temp_db, sample_category):
        """Test de ajuste de día para meses cortos."""
        cat_id = sample_category

        # Plantilla con día 31
        add_transaction(
            date(2026, 1, 31),
            Decimal("500.00"),
            cat_id,
            "End of month",
            is_recurring=True,
            recurring_day=31
        )

        # Febrero 2026 tiene 28 días
        ensure_recurring(2, 2026)
        feb_transactions = get_transactions(2, 2026)

        assert len(feb_transactions) == 1
        assert feb_transactions[0].date == "2026-02-28"  # Ajustado
