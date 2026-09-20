"""SQLite data layer for Pacioli.

Design rules enforced here:

- Money is stored as INTEGER cents; Decimal is used at the domain edge.
- Schema is versioned with ``PRAGMA user_version``: a fresh database
  walks the same migration path as an old one (v0 -> v1 baseline ->
  v2 cents), so the desktop app's database works unchanged.
- Recurring templates are materialized once per month and recorded in
  ``recurring_materialized`` so instances are never duplicated, even
  if the user deletes one.
- The database lives outside the repository (XDG data dir) so it
  survives updates and packaging.
"""

import calendar
import os
import sqlite3
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2


def _default_data_dir() -> str:
    override = os.environ.get("PACIOLI_DATA_DIR")
    if override:
        return override
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share"
    )
    return os.path.join(base, "pacioli")


# Historical location (repo/data/budget.db); imported once if present.
LEGACY_DB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "budget.db")
)

DEFAULT_DB_PATH = os.path.join(_default_data_dir(), "pacioli.db")

_db_path: str | None = None


def set_db_path(path: str | Path | None) -> None:
    """Override the database location.

    Pass None to restore the default XDG path. Tests use this to
    isolate each suite on a temporary database.

    Args:
        path: New database path, or None for the default.
    """
    global _db_path
    _db_path = str(path) if path is not None else None


def get_db_path() -> str:
    """Return the active database path, creating its directory."""
    if _db_path is not None:
        return _db_path
    os.makedirs(os.path.dirname(DEFAULT_DB_PATH), exist_ok=True)
    return DEFAULT_DB_PATH


def get_backup_dir() -> str:
    """Return the backups directory, creating it if needed."""
    d = os.path.join(os.path.dirname(os.path.abspath(get_db_path())), "backups")
    os.makedirs(d, exist_ok=True)
    return d


@contextmanager
def get_connection():
    """Yield a configured sqlite3 connection (WAL, foreign keys on)."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def _import_legacy_db() -> bool:
    """Copy the legacy repo database to the XDG location, once."""
    if os.path.exists(get_db_path()) or not os.path.exists(LEGACY_DB_PATH):
        return False
    os.makedirs(os.path.dirname(get_db_path()), exist_ok=True)
    src = sqlite3.connect(LEGACY_DB_PATH)
    try:
        dst = sqlite3.connect(get_db_path())
        try:
            with dst:
                src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return True


# ── Money: INTEGER cents in DB, Decimal in the domain ─────────


def _to_cents(amount: Decimal | float | int | str) -> int:
    return int((Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _to_dec(cents: int | None) -> Decimal:
    return (Decimal(cents or 0) / 100).quantize(Decimal("0.01"))


@dataclass
class Category:
    """Expense or income category."""

    id: int | None
    name: str
    type: str  # 'income' or 'expense'
    color: str
    icon: str


@dataclass
class Subcategory:
    """Subcategory belonging to a category."""

    id: int | None
    category_id: int
    name: str
    icon: str


@dataclass
class Transaction:
    """A single transaction (or a recurring template)."""

    id: int | None
    date: date
    amount: Decimal
    category_id: int
    description: str
    is_recurring: bool
    recurring_day: int | None  # Day of month for recurring templates
    subcategory_id: int | None = None
    subcategory_name: str | None = None
    subcategory_icon: str | None = None
    generated_from: int | None = None  # Recurring template that generated it
    category_name: str | None = None  # Joined from categories
    category_type: str | None = None
    color: str | None = None
    icon: str | None = None


@dataclass
class Budget:
    """Monthly budget for a category."""

    id: int | None
    category_id: int
    month: int  # 1-12
    year: int
    amount: Decimal


@dataclass
class MonthlySummary:
    """Aggregated totals for a month."""

    month: int
    year: int
    total_income: Decimal
    total_expense: Decimal
    balance: Decimal
    by_category: dict[str, Decimal]


# ── Migrations ────────────────────────────────────────────────
# Versioned schema via PRAGMA user_version. A new DB walks the same
# path as an old one: v0 -> v1 (baseline) -> v2 (cents).


def _user_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def _migrate_v1_baseline(conn: sqlite3.Connection) -> None:
    """v0 -> v1: historical schema (idempotent on existing databases)."""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            color TEXT DEFAULT '#3B82F6',
            icon TEXT DEFAULT '📁'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            category_id INTEGER NOT NULL,
            description TEXT DEFAULT '',
            is_recurring INTEGER DEFAULT 0,
            recurring_day INTEGER,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
            year INTEGER NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            UNIQUE(category_id, month, year)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subcategories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '📁',
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
            UNIQUE(category_id, name)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL CHECK(role IN ('user', 'ai')),
            message TEXT NOT NULL,
            month INTEGER,
            year INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_learnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            correction TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS desc_learnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            subcategory TEXT,
            ai_description TEXT NOT NULL,
            user_description TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        SELECT COUNT(*) FROM pragma_table_info('transactions') WHERE name = 'subcategory_id'
    """)
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            ALTER TABLE transactions ADD COLUMN subcategory_id INTEGER
            REFERENCES subcategories(id)
        """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_budgets_month_year ON budgets(month, year)")

    cursor.execute("PRAGMA user_version = 1")


def _migrate_v2_cents(conn: sqlite3.Connection) -> None:
    """v1 -> v2: money in INTEGER cents + recurrence support.

    Rebuilds transactions and budgets (SQLite cannot change a column
    type with ALTER), converting with ROUND(amount*100) and checking
    referential integrity at the end.
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF")

    cursor.execute("""
        CREATE TABLE transactions_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            category_id INTEGER NOT NULL REFERENCES categories(id),
            description TEXT DEFAULT '',
            is_recurring INTEGER DEFAULT 0,
            recurring_day INTEGER,
            subcategory_id INTEGER REFERENCES subcategories(id),
            generated_from INTEGER REFERENCES transactions(id) ON DELETE SET NULL
        )
    """)
    cursor.execute("""
        INSERT INTO transactions_new
            (id, date, amount_cents, category_id, description,
             is_recurring, recurring_day, subcategory_id)
        SELECT id, date, CAST(ROUND(amount * 100) AS INTEGER), category_id,
               description, is_recurring, recurring_day, subcategory_id
        FROM transactions
    """)
    cursor.execute("DROP TABLE transactions")
    cursor.execute("ALTER TABLE transactions_new RENAME TO transactions")

    cursor.execute("""
        CREATE TABLE budgets_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL REFERENCES categories(id),
            month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
            year INTEGER NOT NULL,
            amount_cents INTEGER NOT NULL,
            UNIQUE(category_id, month, year)
        )
    """)
    cursor.execute("""
        INSERT INTO budgets_new (id, category_id, month, year, amount_cents)
        SELECT id, category_id, month, year, CAST(ROUND(amount * 100) AS INTEGER)
        FROM budgets
    """)
    cursor.execute("DROP TABLE budgets")
    cursor.execute("ALTER TABLE budgets_new RENAME TO budgets")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recurring_materialized (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
            month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
            year INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(template_id, month, year)
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_transactions_generated ON transactions(generated_from)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_budgets_month_year ON budgets(month, year)")

    violations = cursor.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise sqlite3.IntegrityError(
            f"Migration to v2: {len(violations)} FK violations: {violations[:5]}"
        )

    cursor.execute("PRAGMA user_version = 2")
    cursor.execute("PRAGMA foreign_keys = ON")


def _seed_defaults(conn: sqlite3.Connection) -> None:
    """Insert default categories and subcategories (idempotent)."""
    cursor = conn.cursor()

    default_categories = [
        ("Salario", "income", "#10B981", "💰"),
        ("Freelance", "income", "#059669", "💻"),
        ("Inversiones", "income", "#047857", "📈"),
        ("Otros ingresos", "income", "#065F46", "💵"),
        ("Vivienda", "expense", "#EF4444", "🏠"),
        ("Alimentación", "expense", "#F97316", "🍕"),
        ("Transporte", "expense", "#EAB308", "🚌"),
        ("Servicios", "expense", "#8B5CF6", "⚡"),
        ("Entretenimiento", "expense", "#EC4899", "🎮"),
        ("Salud", "expense", "#14B8A6", "🏥"),
        ("Educación", "expense", "#6366F1", "📚"),
        ("Compras", "expense", "#F43F5E", "🛍️"),
        ("Otros gastos", "expense", "#64748B", "📦"),
    ]

    for name, cat_type, color, icon in default_categories:
        cursor.execute(
            "INSERT OR IGNORE INTO categories (name, type, color, icon) VALUES (?, ?, ?, ?)",
            (name, cat_type, color, icon),
        )

    default_subcategories = [
        (
            "Servicios",
            [
                ("Agua", "💧"),
                ("Energía", "⚡"),
                ("Gas", "🔥"),
                ("Internet", "🌐"),
                ("Teléfono", "📱"),
                ("Televisión", "📺"),
            ],
        ),
        (
            "Alimentación",
            [
                ("Supermercado", "🛒"),
                ("Restaurantes", "🍽️"),
                ("Domicilios", "🛵"),
            ],
        ),
        (
            "Transporte",
            [
                ("Gasolina", "⛽"),
                ("Transporte público", "🚌"),
                ("Estacionamiento", "🅿️"),
                ("Uber/Taxi", "🚕"),
            ],
        ),
        (
            "Salud",
            [
                ("Consultas", "🩺"),
                ("Medicamentos", "💊"),
                ("Seguro médico", "🛡️"),
            ],
        ),
        (
            "Educación",
            [
                ("Matrícula", "🎓"),
                ("Libros", "📖"),
                ("Cursos", "💻"),
            ],
        ),
        (
            "Vivienda",
            [
                ("Arriendo", "🏠"),
                ("Mantenimiento", "🔧"),
                ("Seguro", "🛡️"),
            ],
        ),
    ]
    for cat_name, subs in default_subcategories:
        cursor.execute("SELECT id FROM categories WHERE name = ?", (cat_name,))
        row = cursor.fetchone()
        if row:
            for sub_name, sub_icon in subs:
                cursor.execute(
                    "INSERT OR IGNORE INTO subcategories (category_id, name, icon) VALUES (?, ?, ?)",
                    (row["id"], sub_name, sub_icon),
                )


def init_db() -> None:
    """Import legacy data if needed, apply migrations and seeds."""
    _import_legacy_db()
    with get_connection() as conn:
        v = _user_version(conn)
        if v < 1:
            _migrate_v1_baseline(conn)
        if v < 2:
            _migrate_v2_cents(conn)
        conn.commit()
        _seed_defaults(conn)
        conn.commit()


# ── Categories ────────────────────────────────────────────────


def get_categories(cat_type: str | None = None) -> list[Category]:
    """Return categories, optionally filtered by type."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if cat_type:
            cursor.execute("SELECT * FROM categories WHERE type = ? ORDER BY name", (cat_type,))
        else:
            cursor.execute("SELECT * FROM categories ORDER BY type, name")
        return [Category(**dict(row)) for row in cursor.fetchall()]


def add_category(name: str, cat_type: str, color: str = "#3B82F6", icon: str = "📁") -> int:
    """Create a category and return its id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO categories (name, type, color, icon) VALUES (?, ?, ?, ?)",
            (name, cat_type, color, icon),
        )
        conn.commit()
        return int(cursor.lastrowid)


def update_category(cat_id: int, name: str, color: str, icon: str) -> None:
    """Update a category's name, color and icon."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE categories SET name = ?, color = ?, icon = ? WHERE id = ?",
            (name, color, icon, cat_id),
        )
        conn.commit()


def delete_category(cat_id: int) -> None:
    """Delete a category, refusing if transactions or budgets reference it."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
            conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(
                "No se puede eliminar: la categoría tiene transacciones o presupuestos asociados."
            ) from None


# ── Subcategories ─────────────────────────────────────────────


def get_subcategories(category_id: int) -> list[Subcategory]:
    """Return subcategories for a category."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM subcategories WHERE category_id = ? ORDER BY name", (category_id,)
        )
        return [Subcategory(**dict(row)) for row in cursor.fetchall()]


def get_all_subcategories() -> list[Subcategory]:
    """Return all subcategories."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subcategories ORDER BY category_id, name")
        return [Subcategory(**dict(row)) for row in cursor.fetchall()]


def add_subcategory(category_id: int, name: str, icon: str = "📁") -> int:
    """Create a subcategory and return its id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO subcategories (category_id, name, icon) VALUES (?, ?, ?)",
            (category_id, name, icon),
        )
        conn.commit()
        return int(cursor.lastrowid)


def delete_subcategory(sub_id: int) -> None:
    """Delete a subcategory, detaching it from its transactions."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE transactions SET subcategory_id = NULL WHERE subcategory_id = ?", (sub_id,)
        )
        cursor.execute("DELETE FROM subcategories WHERE id = ?", (sub_id,))
        conn.commit()


# ── Transactions ──────────────────────────────────────────────

_TX_KEYS = {f.name for f in Transaction.__dataclass_fields__.values()}


def _month_window(month: int, year: int) -> tuple[str, str]:
    """Return the [start, end) ISO date range covering a month."""
    start = f"{year}-{month:02d}-01"
    end = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
    return start, end


def _row_to_tx(row: sqlite3.Row) -> Transaction:
    data = dict(row)
    data["amount"] = _to_dec(data.pop("amount_cents"))
    data["date"] = date.fromisoformat(data["date"])
    return Transaction(**{k: v for k, v in data.items() if k in _TX_KEYS})


def get_transactions(month: int, year: int) -> list[Transaction]:
    """Return all transactions of a month, newest first."""
    with get_connection() as conn:
        cursor = conn.cursor()
        start_date, end_date = _month_window(month, year)
        cursor.execute(
            """
            SELECT t.*, c.name as category_name, c.type as category_type, c.color, c.icon,
                   s.name as subcategory_name, s.icon as subcategory_icon
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            LEFT JOIN subcategories s ON t.subcategory_id = s.id
            WHERE t.date >= ? AND t.date < ?
            ORDER BY t.date DESC
        """,
            (start_date, end_date),
        )
        return [_row_to_tx(row) for row in cursor.fetchall()]


def add_transaction(
    date_val: date,
    amount: Decimal | float | int,
    category_id: int,
    description: str = "",
    is_recurring: bool = False,
    recurring_day: int | None = None,
    subcategory_id: int | None = None,
) -> int:
    """Create a transaction and return its id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO transactions (date, amount_cents, category_id, description, is_recurring, recurring_day, subcategory_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                date_val.isoformat(),
                _to_cents(amount),
                category_id,
                description,
                int(is_recurring),
                recurring_day,
                subcategory_id,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def update_transaction(
    trans_id: int,
    date_val: date,
    amount: Decimal | float | int,
    category_id: int,
    description: str,
    is_recurring: bool = False,
    recurring_day: int | None = None,
    subcategory_id: int | None = None,
) -> None:
    """Update an existing transaction."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE transactions
            SET date = ?, amount_cents = ?, category_id = ?, description = ?, is_recurring = ?, recurring_day = ?, subcategory_id = ?
            WHERE id = ?
        """,
            (
                date_val.isoformat(),
                _to_cents(amount),
                category_id,
                description,
                int(is_recurring),
                recurring_day,
                subcategory_id,
                trans_id,
            ),
        )
        conn.commit()


def delete_transaction(trans_id: int) -> None:
    """Delete a transaction by id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE id = ?", (trans_id,))
        conn.commit()


# ── Recurring transactions ────────────────────────────────────
# A transaction with is_recurring=1 and generated_from NULL is a
# "template". When navigating to a later month, ensure_recurring()
# creates that month's instance (day clamped to the last day of the
# month when needed) and records it in recurring_materialized so it
# is never duplicated, even if the user deletes the instance.


def ensure_recurring(month: int, year: int) -> int:
    """Materialize recurring templates for the given month.

    Returns:
        Number of new transactions created.
    """
    last_day = calendar.monthrange(year, month)[1]
    created = 0
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, date, amount_cents, category_id, description,
                   recurring_day, subcategory_id
            FROM transactions
            WHERE is_recurring = 1 AND generated_from IS NULL
              AND recurring_day IS NOT NULL
        """)
        templates = cursor.fetchall()
        for t in templates:
            t_year, t_month = int(t["date"][:4]), int(t["date"][5:7])
            if (year, month) <= (t_year, t_month):
                continue
            cursor.execute(
                "SELECT 1 FROM recurring_materialized WHERE template_id = ? AND month = ? AND year = ?",
                (t["id"], month, year),
            )
            if cursor.fetchone():
                continue
            day = min(t["recurring_day"], last_day)
            cursor.execute(
                """
                INSERT INTO transactions
                    (date, amount_cents, category_id, description,
                     is_recurring, recurring_day, subcategory_id, generated_from)
                VALUES (?, ?, ?, ?, 0, NULL, ?, ?)
            """,
                (
                    f"{year:04d}-{month:02d}-{day:02d}",
                    t["amount_cents"],
                    t["category_id"],
                    t["description"],
                    t["subcategory_id"],
                    t["id"],
                ),
            )
            cursor.execute(
                "INSERT INTO recurring_materialized (template_id, month, year) VALUES (?, ?, ?)",
                (t["id"], month, year),
            )
            created += 1
        conn.commit()
    return created


# ── Budgets ───────────────────────────────────────────────────


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


def delete_budget(category_id: int, month: int, year: int) -> None:
    """Delete the budget of a category for a month."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM budgets WHERE category_id = ? AND month = ? AND year = ?",
            (category_id, month, year),
        )
        conn.commit()


# ── Aggregations ──────────────────────────────────────────────


def get_monthly_summary(month: int, year: int) -> MonthlySummary:
    """Return income/expense/balance totals for a month."""
    with get_connection() as conn:
        cursor = conn.cursor()
        start_date, end_date = _month_window(month, year)

        cursor.execute(
            """
            SELECT c.type, c.name, SUM(t.amount_cents) as total_cents
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.date >= ? AND t.date < ?
            GROUP BY c.type, c.name
        """,
            (start_date, end_date),
        )

        by_category: dict[str, Decimal] = {}
        total_income = Decimal("0.00")
        total_expense = Decimal("0.00")
        for row in cursor.fetchall():
            total = _to_dec(row["total_cents"])
            by_category[row["name"]] = total
            if row["type"] == "income":
                total_income += total
            else:
                total_expense += total

        return MonthlySummary(
            month=month,
            year=year,
            total_income=total_income,
            total_expense=total_expense,
            balance=total_income - total_expense,
            by_category=by_category,
        )


def get_monthly_summaries(year: int) -> list[MonthlySummary]:
    """Return the monthly summary for every month of a year."""
    return [get_monthly_summary(m, year) for m in range(1, 13)]


def get_category_spending(
    month: int, year: int, cat_type: str = "expense"
) -> list[tuple[str, Decimal, str, str]]:
    """Return (name, total, color, icon) spending by category."""
    with get_connection() as conn:
        cursor = conn.cursor()
        start_date, end_date = _month_window(month, year)
        cursor.execute(
            """
            SELECT c.name, SUM(t.amount_cents) as total_cents, c.color, c.icon
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE c.type = ? AND t.date >= ? AND t.date < ?
            GROUP BY c.id
            ORDER BY total_cents DESC
        """,
            (cat_type, start_date, end_date),
        )
        return [
            (row["name"], _to_dec(row["total_cents"]), row["color"], row["icon"])
            for row in cursor.fetchall()
        ]


def get_budget_vs_actual(month: int, year: int) -> list[dict[str, Any]]:
    """Return budget vs actual spending per expense category."""
    with get_connection() as conn:
        cursor = conn.cursor()
        start_date, end_date = _month_window(month, year)

        cursor.execute(
            """
            SELECT c.id, c.name, c.color, c.icon,
                   COALESCE(b.amount_cents, 0) as budget_cents,
                   COALESCE(SUM(t.amount_cents), 0) as actual_cents
            FROM categories c
            LEFT JOIN budgets b ON c.id = b.category_id AND b.month = ? AND b.year = ?
            LEFT JOIN transactions t ON c.id = t.category_id AND t.date >= ? AND t.date < ?
            WHERE c.type = 'expense'
            GROUP BY c.id
            HAVING budget_cents > 0 OR actual_cents > 0
            ORDER BY c.name
        """,
            (month, year, start_date, end_date),
        )

        result = []
        for row in cursor.fetchall():
            budget = _to_dec(row["budget_cents"])
            actual = _to_dec(row["actual_cents"])
            result.append(
                {
                    "category_id": row["id"],
                    "name": row["name"],
                    "color": row["color"],
                    "icon": row["icon"],
                    "budget": budget,
                    "actual": actual,
                    "remaining": budget - actual if budget > 0 else -actual,
                    "percent": float(actual / budget * 100) if budget > 0 else 0.0,
                }
            )
        return result


# ── Chat history ──────────────────────────────────────────────


def save_chat_message(role: str, message: str, month: int, year: int) -> None:
    """Persist a chat message for a month."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_history (role, message, month, year) VALUES (?, ?, ?, ?)",
            (role, message, month, year),
        )
        conn.commit()


def get_chat_history(month: int, year: int, limit: int = 50) -> list[dict[str, Any]]:
    """Return the most recent chat messages of a month, oldest first."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, message, created_at FROM chat_history "
            "WHERE month = ? AND year = ? ORDER BY created_at DESC, id DESC LIMIT ?",
            (month, year, limit),
        )
        return [dict(row) for row in reversed(cursor.fetchall())]


def clear_chat_history(month: int, year: int) -> None:
    """Delete all chat messages of a month."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_history WHERE month = ? AND year = ?", (month, year))
        conn.commit()


# ── AI learnings ──────────────────────────────────────────────


def save_learning(topic: str, correction: str) -> None:
    """Persist a user correction for the AI assistant."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO ai_learnings (topic, correction) VALUES (?, ?)",
            (topic, correction),
        )
        conn.commit()


def get_learnings(limit: int = 20) -> list[dict[str, Any]]:
    """Return the most recent AI learnings."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT topic, correction, created_at FROM ai_learnings "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_recent_chat_context(month: int, year: int, turns: int = 10) -> str:
    """Build a prompt-ready string with the recent chat of a month."""
    history = get_chat_history(month, year, limit=turns)
    if not history:
        return ""
    lines = []
    for h in history:
        tag = "Usuario" if h["role"] == "user" else "IA"
        lines.append(f"{tag}: {h['message']}")
    return "\n".join(lines)


def get_learnings_context() -> str:
    """Build a prompt-ready string with the stored learnings."""
    learnings = get_learnings(limit=15)
    if not learnings:
        return ""
    lines = ["Aprendizajes del usuario (correcciones previas):"]
    for item in learnings:
        lines.append(f"- [{item['topic']}] {item['correction']}")
    return "\n".join(lines)


# ── Description learnings ─────────────────────────────────────


def save_desc_learning(category: str, subcategory: str, ai_desc: str, user_desc: str) -> None:
    """Persist a description correction made by the user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO desc_learnings (category, subcategory, ai_description, user_description) "
            "VALUES (?, ?, ?, ?)",
            (category, subcategory or "", ai_desc, user_desc),
        )
        conn.commit()


def get_desc_learnings(category: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return the most recent description learnings for a category."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT ai_description, user_description FROM desc_learnings "
            "WHERE category = ? ORDER BY created_at DESC LIMIT ?",
            (category, limit),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_desc_learnings_context(category: str) -> str:
    """Build a prompt-ready string with description learnings."""
    learnings = get_desc_learnings(category, limit=5)
    if not learnings:
        return ""
    lines = [f"Correciones previas de descripciones en '{category}':"]
    for item in learnings:
        lines.append(
            f'  IA dijo: "{item["ai_description"]}" → Usuario corrigió: "{item["user_description"]}"'
        )
    return "\n".join(lines)


# ── CSV export ────────────────────────────────────────────────


def transactions_to_csv(month: int, year: int) -> str:
    """Build the CSV content of the transactions of a month."""
    import csv
    import io

    txns = get_transactions(month, year)
    cat_map = {c.id: c for c in get_categories()}
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["Fecha", "Categoría", "Subcategoría", "Tipo", "Monto", "Descripción", "Recurrente"]
    )
    for t in txns:
        cat = cat_map.get(t.category_id)
        cat_name = cat.name if cat else "—"
        cat_type = cat.type if cat else "—"
        sub_name = t.subcategory_name or ""
        writer.writerow(
            [
                t.date,
                cat_name,
                sub_name,
                cat_type,
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


# ── Automatic backups ─────────────────────────────────────────

BACKUP_KEEP = 10


def backup_database(dest_path: str) -> None:
    """Hot-copy the database safely using the sqlite3 backup API.

    Unlike shutil.copy, this is consistent even with WAL active or
    concurrent writes.
    """
    src = sqlite3.connect(get_db_path())
    try:
        dst = sqlite3.connect(dest_path)
        try:
            with dst:
                src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def auto_backup(keep: int = BACKUP_KEEP) -> str | None:
    """Run the daily automatic backup with rotation.

    Returns:
        The path of the created backup, or None if one already exists.
    """
    if not os.path.exists(get_db_path()):
        return None
    today = date.today()
    dest = os.path.join(get_backup_dir(), f"pacioli_{today.isoformat()}.db")
    created = None
    if not os.path.exists(dest):
        backup_database(dest)
        created = dest
    if keep > 0:
        backups = sorted(
            f
            for f in os.listdir(get_backup_dir())
            if f.startswith("pacioli_") and f.endswith(".db")
        )
        for old in backups[: max(0, len(backups) - keep)]:
            with suppress(OSError):
                os.remove(os.path.join(get_backup_dir(), old))
    return created
