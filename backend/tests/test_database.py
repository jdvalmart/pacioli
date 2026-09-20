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
    add_category,
    add_transaction,
    delete_category,
    ensure_recurring,
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
            assert conn.execute("PRAGMA user_version").fetchone()[0] == 4
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
            assert conn.execute("PRAGMA user_version").fetchone()[0] == 4
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
