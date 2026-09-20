"""Tests for the SQLite data layer."""

import os
import sqlite3
import tempfile
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.database import (
    LEGACY_DB_PATH,
    _migrate_v1_baseline,
    _migrate_v2_cents,
    _seed_defaults,
    add_account,
    add_category,
    add_transaction,
    delete_account,
    delete_category,
    ensure_recurring,
    get_accounts,
    get_budget_vs_actual,
    get_budgets,
    get_categories,
    get_connection,
    get_monthly_summary,
    get_subcategories,
    get_transactions,
    init_db,
    set_budget,
    set_db_path,
    update_account,
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

    def test_recurring_inherits_account(self, temp_db: str, sample_category: int) -> None:
        account_id = add_account("Arriendo cuenta", "banco", Decimal("0.00"))
        add_transaction(
            date(2026, 1, 15),
            Decimal("1000.00"),
            sample_category,
            "Monthly rent",
            is_recurring=True,
            recurring_day=15,
            account_id=account_id,
        )

        ensure_recurring(2, 2026)
        feb_transactions = get_transactions(2, 2026)
        assert feb_transactions[0].account_id == account_id
        assert feb_transactions[0].account_name == "Arriendo cuenta"

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

    def test_default_subcategories_seeded(self, temp_db: str) -> None:
        categories = get_categories()
        alimentacion = next(c for c in categories if c.name == "Alimentación")
        subs = {s.name for s in get_subcategories(alimentacion.id or 0)}
        assert {"Supermercado", "No perecederos", "Verduras", "Carne", "Aseo"} <= subs

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


class TestMigrationV3:
    """Tests for the subcategory dedupe migration."""

    def _build_legacy_db(self, db_path: Path) -> None:
        """Build a desktop-era database with duplicated subcategories."""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        _migrate_v1_baseline(conn)
        _migrate_v2_cents(conn)
        conn.commit()

        # Rebuild subcategories without the UNIQUE constraint, as the
        # pre-v1 desktop schema had it.
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("""
            CREATE TABLE subcategories_legacy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                icon TEXT DEFAULT '📁',
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            )
        """)
        conn.execute("INSERT INTO subcategories_legacy SELECT * FROM subcategories")
        conn.execute("DROP TABLE subcategories")
        conn.execute("ALTER TABLE subcategories_legacy RENAME TO subcategories")
        conn.execute("PRAGMA foreign_keys = ON")

        # Two extra seeds reproduce the duplicated rows of legacy DBs.
        _seed_defaults(conn)
        _seed_defaults(conn)
        conn.execute("PRAGMA user_version = 2")
        conn.commit()
        conn.close()

    def test_dedupes_and_restores_constraint(self, tmp_path: Path) -> None:
        db_path = tmp_path / "legacy.db"
        set_db_path(db_path)
        self._build_legacy_db(db_path)

        init_db()

        with get_connection() as conn:
            dupes = conn.execute("""
                SELECT COUNT(*) FROM (
                    SELECT 1 FROM subcategories
                    GROUP BY category_id, name HAVING COUNT(*) > 1
                )
            """).fetchone()[0]
            assert dupes == 0

            schema = conn.execute(
                "SELECT sql FROM sqlite_master WHERE name='subcategories'"
            ).fetchone()[0]
            assert "UNIQUE(category_id, name)" in schema
            assert conn.execute("PRAGMA user_version").fetchone()[0] == 7
        set_db_path(None)

    def test_repoints_transactions_to_canonical_subcategory(self, tmp_path: Path) -> None:
        db_path = tmp_path / "legacy.db"
        set_db_path(db_path)
        self._build_legacy_db(db_path)

        # Point a transaction at a duplicate id (the highest one).
        conn = sqlite3.connect(db_path)
        row = conn.execute("""
            SELECT category_id, name, MAX(id) as dup, MIN(id) as keep
            FROM subcategories
            GROUP BY category_id, name
            HAVING COUNT(*) > 1
            LIMIT 1
        """).fetchone()
        conn.execute(
            """
            INSERT INTO transactions (date, amount_cents, category_id, description, subcategory_id)
            VALUES ('2026-01-01', 1000, ?, 'test', ?)
        """,
            (row[0], row[2]),
        )
        conn.commit()
        conn.close()

        init_db()

        with get_connection() as conn:
            subcategory_id = conn.execute("""
                SELECT subcategory_id FROM transactions WHERE description = 'test'
            """).fetchone()[0]
            assert subcategory_id == row[3]  # canonical (lowest) id
        set_db_path(None)


class TestMigrationV4:
    """Tests for the budget constraint migration."""

    def test_restores_budget_constraint_and_keeps_last_write(self, tmp_path: Path) -> None:
        db_path = tmp_path / "legacy.db"
        set_db_path(db_path)
        init_db()

        # Simulate the broken desktop-era budgets table: no UNIQUE
        # constraint, duplicates for the same (category, month, year).
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("""
            CREATE TABLE budgets_broken (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                month INTEGER NOT NULL,
                year INTEGER NOT NULL,
                amount_cents INTEGER NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        """)
        conn.execute("INSERT INTO budgets_broken SELECT * FROM budgets")
        conn.execute("DROP TABLE budgets")
        conn.execute("ALTER TABLE budgets_broken RENAME TO budgets")
        cat_id = conn.execute(
            "SELECT id FROM categories WHERE type = 'expense' LIMIT 1"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO budgets (category_id, month, year, amount_cents) VALUES (?, 9, 2026, 1000)",
            (cat_id,),
        )
        conn.execute(
            "INSERT INTO budgets (category_id, month, year, amount_cents) VALUES (?, 9, 2026, 2000)",
            (cat_id,),
        )
        conn.execute("PRAGMA user_version = 3")
        conn.commit()
        conn.close()

        init_db()

        with get_connection() as conn:
            assert conn.execute("PRAGMA user_version").fetchone()[0] == 7
            schema = conn.execute("SELECT sql FROM sqlite_master WHERE name='budgets'").fetchone()[
                0
            ]
            assert "UNIQUE(category_id, month, year)" in schema

            rows = conn.execute(
                "SELECT amount_cents FROM budgets WHERE category_id = ? AND month = 9 AND year = 2026",
                (cat_id,),
            ).fetchall()
            assert len(rows) == 1
            assert rows[0][0] == 2000  # last write wins

        # Upserts must work again after the migration.
        set_budget(cat_id, 9, 2026, Decimal("3000.00"))
        assert len(get_budgets(9, 2026)) == 1
        assert get_budgets(9, 2026)[0].amount == Decimal("3000.00")
        set_db_path(None)


class TestCarryover:
    """Tests for the running balance (carryover) in monthly summaries."""

    def test_carryover_accumulates_previous_months(
        self, temp_db: str, sample_category: int
    ) -> None:
        income_cat = add_category("Ingreso test", "income")

        # September: income 1000, expense 300 -> balance 700
        add_transaction(date(2026, 9, 10), Decimal("1000.00"), income_cat, "Salary", kind="ingreso")
        add_transaction(date(2026, 9, 15), Decimal("300.00"), sample_category, "Rent")

        # October: expense 500 -> balance -500
        add_transaction(date(2026, 10, 5), Decimal("500.00"), sample_category, "Food")

        september = get_monthly_summary(9, 2026)
        assert september.carryover == Decimal("0.00")
        assert september.accumulated_balance == Decimal("700.00")

        october = get_monthly_summary(10, 2026)
        assert october.carryover == Decimal("700.00")
        assert october.balance == Decimal("-500.00")
        assert october.accumulated_balance == Decimal("200.00")

    def test_carryover_with_negative_balance(self, temp_db: str, sample_category: int) -> None:
        add_transaction(date(2026, 9, 1), Decimal("100.00"), sample_category, "Debt")

        october = get_monthly_summary(10, 2026)
        assert october.carryover == Decimal("-100.00")
        assert october.accumulated_balance == Decimal("-100.00")


class TestAccounts:
    """Tests for the accounts feature."""

    def test_account_starting_amount_becomes_income_transaction(
        self, temp_db: str, sample_category: int
    ) -> None:
        income_cat = add_category("Ingreso test", "income")
        account_id = add_account("Billetera", "efectivo", Decimal("200.00"))

        add_transaction(
            date(2026, 9, 1),
            Decimal("1000.00"),
            income_cat,
            "Salary",
            account_id=account_id,
            kind="ingreso",
        )
        add_transaction(
            date(2026, 9, 2), Decimal("300.00"), sample_category, "Rent", account_id=account_id
        )
        # A transaction not linked to the account must not affect it.
        add_transaction(date(2026, 9, 3), Decimal("999.00"), sample_category, "Other")

        accounts = get_accounts()
        assert len(accounts) == 1
        # Starting 200 (income) + 1000 income - 300 expense = 900
        assert accounts[0].balance == Decimal("900.00")

        # The starting money is a real transaction in Otros ingresos.
        summary = get_monthly_summary(9, 2026)
        assert summary.total_income == Decimal("1200.00")

    def test_account_without_starting_amount(self, temp_db: str) -> None:
        account_id = add_account("Nequi", "digital", Decimal("0.00"))
        accounts = get_accounts()
        account = next(a for a in accounts if a.id == account_id)
        assert account.icon == "📱"
        assert account.color == "#3B82F6"
        assert account.balance == Decimal("0.00")

    def test_update_and_delete_account(self, temp_db: str) -> None:
        account_id = add_account("Ahorro", "ahorros", Decimal("50.00"))
        update_account(account_id, "Ahorro grande")

        accounts = get_accounts()
        assert accounts[0].name == "Ahorro grande"
        assert accounts[0].balance == Decimal("50.00")

        delete_account(account_id)
        assert get_accounts() == []


class TestTransfers:
    """Tests for transfer semantics between accounts."""

    def test_transfer_moves_money_between_accounts(self, temp_db: str) -> None:
        savings = add_account("Ahorros", "ahorros", Decimal("1000.00"))
        wallet = add_account("Billetera", "efectivo", Decimal("0.00"))

        add_transaction(
            date(2026, 9, 10),
            Decimal("300.00"),
            account_id=savings,
            to_account_id=wallet,
            kind="transferencia",
            description="Saco para el mercado",
        )

        accounts = {a.name: a for a in get_accounts()}
        assert accounts["Ahorros"].balance == Decimal("700.00")
        assert accounts["Billetera"].balance == Decimal("300.00")

    def test_transfer_does_not_affect_summary(self, temp_db: str) -> None:
        income_cat = add_category("Ingreso test", "income")
        savings = add_account("Ahorros", "ahorros", Decimal("0.00"))
        wallet = add_account("Billetera", "efectivo", Decimal("0.00"))

        add_transaction(
            date(2026, 9, 1),
            Decimal("1000.00"),
            income_cat,
            "Salary",
            kind="ingreso",
            account_id=savings,
        )
        add_transaction(
            date(2026, 9, 10),
            Decimal("300.00"),
            account_id=savings,
            to_account_id=wallet,
            kind="transferencia",
        )

        summary = get_monthly_summary(9, 2026)
        assert summary.total_income == Decimal("1000.00")
        assert summary.total_expense == Decimal("0.00")
        assert summary.balance == Decimal("1000.00")

    def test_gasto_tc_does_not_touch_accounts(self, temp_db: str, sample_category: int) -> None:
        add_account("Ahorros", "ahorros", Decimal("1000.00"))

        add_transaction(
            date(2026, 9, 10),
            Decimal("150.00"),
            sample_category,
            "Compras TC",
            kind="gasto_tc",
        )

        accounts = {a.name: a for a in get_accounts()}
        assert accounts["Ahorros"].balance == Decimal("1000.00")

        summary = get_monthly_summary(9, 2026)
        assert summary.total_expense == Decimal("150.00")


class TestMigrationV7:
    """Tests for the transaction kinds migration."""

    def test_backfills_kinds_by_category_type(self, tmp_path: Path) -> None:
        db_path = tmp_path / "legacy.db"
        set_db_path(db_path)
        init_db()

        income_cat = add_category("Ingreso test", "income")
        add_transaction(date(2026, 9, 1), Decimal("500.00"), income_cat, "Salary")
        add_transaction(
            date(2026, 9, 2),
            Decimal("100.00"),
            next(c for c in get_categories() if c.type == "expense").id or 0,
            "Rent",
        )

        # Simulate a v6 database by hiding the kind column semantics:
        # rebuild transactions without the kind/to_account columns and
        # force the migration to run again.
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("""
            CREATE TABLE transactions_v6 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount_cents INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                description TEXT DEFAULT '',
                is_recurring INTEGER DEFAULT 0,
                recurring_day INTEGER,
                subcategory_id INTEGER,
                account_id INTEGER
            )
        """)
        conn.execute(
            "INSERT INTO transactions_v6 (id, date, amount_cents, category_id, description, is_recurring, recurring_day, subcategory_id, account_id) "
            "SELECT id, date, amount_cents, category_id, description, is_recurring, recurring_day, subcategory_id, account_id FROM transactions"
        )
        conn.execute("DROP TABLE transactions")
        conn.execute("ALTER TABLE transactions_v6 RENAME TO transactions")
        conn.execute("PRAGMA user_version = 6")
        conn.commit()
        conn.close()

        init_db()

        with get_connection() as conn:
            assert conn.execute("PRAGMA user_version").fetchone()[0] == 7
            rows = conn.execute("SELECT kind FROM transactions ORDER BY id").fetchall()
            assert [r[0] for r in rows] == ["ingreso", "gasto"]
        set_db_path(None)
