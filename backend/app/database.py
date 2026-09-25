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

SCHEMA_VERSION = 12


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
    """A single transaction (or a recurring template).

    ``kind`` is ingreso, gasto, transferencia (moves money between
    two of the user's accounts) or gasto_tc (credit card expense).
    Transfers have no category and carry a ``to_account_id``.
    """

    id: int | None
    date: date
    amount: Decimal
    category_id: int | None
    description: str
    is_recurring: bool
    recurring_day: int | None  # Day of month for recurring templates
    kind: str = "gasto"
    subcategory_id: int | None = None
    subcategory_name: str | None = None
    subcategory_icon: str | None = None
    generated_from: int | None = None  # Recurring template that generated it
    category_name: str | None = None  # Joined from categories
    category_type: str | None = None
    color: str | None = None
    icon: str | None = None
    account_id: int | None = None  # Where the money moved from/into
    account_name: str | None = None
    account_icon: str | None = None
    to_account_id: int | None = None  # Transfer destination
    to_account_name: str | None = None
    to_account_icon: str | None = None
    card_id: int | None = None  # Credit card for gasto_tc
    card_name: str | None = None
    savings_id: int | None = None  # Savings/investment item for ahorro/retiro
    savings_name: str | None = None


@dataclass
class Budget:
    """Monthly budget for a category."""

    id: int | None
    category_id: int
    month: int  # 1-12
    year: int
    amount: Decimal


@dataclass
class Account:
    """A place where money lives (wallet, savings, bank...).

    ``starting`` is the opening balance that already existed when the
    account was created; it belongs to no month. ``balance`` is that
    opening amount plus the net of the account's linked transactions.
    """

    id: int | None
    name: str
    type: str  # 'efectivo' | 'digital' | 'ahorros' | 'banco'
    icon: str
    color: str
    starting: Decimal | None = None
    balance: Decimal | None = None


ACCOUNT_TYPE_DEFAULTS = {
    "efectivo": ("💵", "#10B981"),
    "digital": ("📱", "#3B82F6"),
    "ahorros": ("🐷", "#8B5CF6"),
    "banco": ("🏦", "#64748B"),
}


@dataclass
class CreditCard:
    """A credit card with a spending limit and billing cycle days.

    ``spent`` and ``paid`` are the current month's totals; ``debt`` is
    the net of the closed billing cycle (only payable after the cutoff
    day) and ``available`` is the remaining credit.
    """

    id: int | None
    name: str
    limit: Decimal
    cutoff_day: int
    payment_day: int
    spent: Decimal | None = None
    paid: Decimal | None = None
    debt: Decimal | None = None
    available: Decimal | None = None


@dataclass
class SavingsItem:
    """A savings or investment bucket.

    Bolsillos hold money moved from accounts; a bolsillo_programado
    additionally schedules a recurring deposit; CDTs carry an
    interest rate and term; acciones track invested capital against a
    manually updated market value. ``balance`` is the net of ahorro
    minus retiro movements.
    """

    id: int | None
    name: str
    kind: str  # 'bolsillo' | 'bolsillo_programado' | 'cdt' | 'acciones'
    target: Decimal | None = None
    rate_bp: int | None = None
    term_days: int | None = None
    current_value: Decimal | None = None
    scheduled_day: int | None = None
    scheduled_amount: Decimal | None = None
    source_account_id: int | None = None
    opening: Decimal | None = None
    balance: Decimal | None = None
    invested: Decimal | None = None


SAVINGS_KIND_ICONS = {
    "bolsillo": "👝",
    "bolsillo_programado": "📆",
    "cdt": "🏦",
    "acciones": "📈",
}


@dataclass
class MonthlySummary:
    """Aggregated totals for a month.

    ``balance`` is the month-only result; ``carryover`` is the
    accumulated balance of all previous months (from the first
    recorded transaction) and ``accumulated_balance`` is the sum of
    both, i.e. the running balance at the end of the month.
    """

    month: int
    year: int
    total_income: Decimal
    total_expense: Decimal
    balance: Decimal
    carryover: Decimal
    accumulated_balance: Decimal
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


def _migrate_v3_subcategory_dedup(conn: sqlite3.Connection) -> None:
    """v2 -> v3: dedupe subcategories and enforce UNIQUE(category_id, name).

    Desktop-era databases predate the unique constraint (their
    ``subcategories`` table was created before the v1 baseline, which
    ``CREATE TABLE IF NOT EXISTS`` never repaired). Every desktop
    launch re-seeded the defaults, so legacy databases accumulate one
    duplicate per launch.

    The migration keeps the lowest id of each (category_id, name)
    pair, repoints transactions from the duplicates to the canonical
    row, deletes the duplicates and rebuilds the table with the
    constraint.
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF")

    duplicates = cursor.execute("""
        SELECT category_id, name, GROUP_CONCAT(id) as ids
        FROM subcategories
        GROUP BY category_id, name
        HAVING COUNT(*) > 1
    """).fetchall()
    for row in duplicates:
        ids = [int(x) for x in row["ids"].split(",")]
        keep = min(ids)
        for dup in ids:
            if dup == keep:
                continue
            cursor.execute(
                "UPDATE transactions SET subcategory_id = ? WHERE subcategory_id = ?",
                (keep, dup),
            )
            cursor.execute("DELETE FROM subcategories WHERE id = ?", (dup,))

    cursor.execute("""
        CREATE TABLE subcategories_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '📁',
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
            UNIQUE(category_id, name)
        )
    """)
    cursor.execute(
        "INSERT INTO subcategories_new (id, category_id, name, icon) "
        "SELECT id, category_id, name, icon FROM subcategories"
    )
    cursor.execute("DROP TABLE subcategories")
    cursor.execute("ALTER TABLE subcategories_new RENAME TO subcategories")

    violations = cursor.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise sqlite3.IntegrityError(
            f"Migration to v3: {len(violations)} FK violations: {violations[:5]}"
        )

    cursor.execute("PRAGMA user_version = 3")
    cursor.execute("PRAGMA foreign_keys = ON")


def _migrate_v4_budget_constraint(conn: sqlite3.Connection) -> None:
    """v3 -> v4: rebuild budgets with UNIQUE(category_id, month, year).

    Some desktop-era migration paths rebuilt the budgets table without
    the unique constraint, so upserts fail with an ON CONFLICT
    mismatch. The migration keeps the most recent row (highest id) of
    each duplicate group and rebuilds the table with the constraint.
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF")

    # Last write wins: keep only the highest id per (category, month, year).
    cursor.execute("""
        DELETE FROM budgets
        WHERE id NOT IN (
            SELECT MAX(id) FROM budgets GROUP BY category_id, month, year
        )
    """)

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
    cursor.execute(
        "INSERT INTO budgets_new (id, category_id, month, year, amount_cents) "
        "SELECT id, category_id, month, year, amount_cents FROM budgets"
    )
    cursor.execute("DROP TABLE budgets")
    cursor.execute("ALTER TABLE budgets_new RENAME TO budgets")

    violations = cursor.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise sqlite3.IntegrityError(
            f"Migration to v4: {len(violations)} FK violations: {violations[:5]}"
        )

    cursor.execute("PRAGMA user_version = 4")
    cursor.execute("PRAGMA foreign_keys = ON")


def _migrate_v5_accounts(conn: sqlite3.Connection) -> None:
    """v4 -> v5: accounts table and transaction account linkage.

    Accounts represent where the money lives (physical wallet, digital
    wallet, savings, bank). Their balance is always derived from the
    initial balance plus the linked transactions, never edited by hand.
    """
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL CHECK(type IN ('efectivo', 'digital', 'ahorros', 'banco')),
            icon TEXT NOT NULL DEFAULT '💵',
            color TEXT NOT NULL DEFAULT '#10B981',
            initial_balance_cents INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        SELECT COUNT(*) FROM pragma_table_info('transactions') WHERE name = 'account_id'
    """)
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            ALTER TABLE transactions ADD COLUMN account_id INTEGER
            REFERENCES accounts(id) ON DELETE SET NULL
        """)

    cursor.execute("PRAGMA user_version = 5")


def _migrate_v6_account_starting_transactions(conn: sqlite3.Connection) -> None:
    """v5 -> v6: drop the initial_balance column from accounts.

    Starting money is now an ordinary income transaction ("Saldo
    inicial: <name>") linked to the account, so it flows naturally
    into income reports and the account balance. Any existing initial
    balance is materialized as such a transaction before the column
    is removed.
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF")

    income_cat = cursor.execute(
        "SELECT id FROM categories WHERE type = 'income' AND name = 'Otros ingresos'"
    ).fetchone()
    if income_cat is None:
        cursor.execute(
            "INSERT INTO categories (name, type, color, icon) "
            "VALUES ('Otros ingresos', 'income', '#065F46', '💵')"
        )
        assert cursor.lastrowid is not None
        income_cat_id = cursor.lastrowid
    else:
        income_cat_id = income_cat["id"]

    rows = []
    has_initial_column = cursor.execute(
        "SELECT COUNT(*) FROM pragma_table_info('accounts') WHERE name = 'initial_balance_cents'"
    ).fetchone()[0]
    if has_initial_column:
        rows = cursor.execute(
            "SELECT id, name, initial_balance_cents, created_at FROM accounts "
            "WHERE initial_balance_cents != 0"
        ).fetchall()
    for row in rows:
        created_date = (row["created_at"] or "")[:10] or date.today().isoformat()
        cursor.execute(
            """
            INSERT INTO transactions
                (date, amount_cents, category_id, description, is_recurring, recurring_day, subcategory_id, account_id)
            VALUES (?, ?, ?, ?, 0, NULL, NULL, ?)
            """,
            (
                created_date,
                row["initial_balance_cents"],
                income_cat_id,
                f"Saldo inicial: {row['name']}",
                row["id"],
            ),
        )

    cursor.execute("""
        CREATE TABLE accounts_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL CHECK(type IN ('efectivo', 'digital', 'ahorros', 'banco')),
            icon TEXT NOT NULL DEFAULT '💵',
            color TEXT NOT NULL DEFAULT '#10B981',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(
        "INSERT INTO accounts_new (id, name, type, icon, color, created_at) "
        "SELECT id, name, type, icon, color, created_at FROM accounts"
    )
    cursor.execute("DROP TABLE accounts")
    cursor.execute("ALTER TABLE accounts_new RENAME TO accounts")

    violations = cursor.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise sqlite3.IntegrityError(
            f"Migration to v6: {len(violations)} FK violations: {violations[:5]}"
        )

    cursor.execute("PRAGMA user_version = 6")
    cursor.execute("PRAGMA foreign_keys = ON")


def _migrate_v7_transaction_kinds(conn: sqlite3.Connection) -> None:
    """v6 -> v7: explicit transaction kinds.

    The movement type stops being derived from the category type and
    becomes an explicit column: ingreso, gasto, transferencia (money
    moving between two of the user's accounts) and gasto_tc (credit
    card expense, tracked as debt later). Transfers gain a destination
    account (to_account_id) and have no category, so category_id
    becomes nullable. Existing rows are backfilled from their category
    type.
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF")

    # Safe against interrupted previous runs: a crash mid-rebuild can
    # leave the staging table behind.
    cursor.execute("DROP TABLE IF EXISTS transactions_new")

    cursor.execute("""
        CREATE TABLE transactions_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            category_id INTEGER REFERENCES categories(id),
            account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
            to_account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
            kind TEXT NOT NULL DEFAULT 'gasto'
                CHECK(kind IN ('ingreso', 'gasto', 'transferencia', 'gasto_tc')),
            description TEXT DEFAULT '',
            is_recurring INTEGER DEFAULT 0,
            recurring_day INTEGER,
            subcategory_id INTEGER REFERENCES subcategories(id),
            generated_from INTEGER REFERENCES transactions(id) ON DELETE SET NULL
        )
    """)
    # Some desktop-era transaction tables lack generated_from; treat
    # the column as optional and copy NULL when it does not exist.
    source_columns = {
        row["name"] for row in cursor.execute("PRAGMA table_info(transactions)").fetchall()
    }
    generated_expr = "t.generated_from" if "generated_from" in source_columns else "NULL"

    cursor.execute(f"""
        INSERT INTO transactions_new
            (id, date, amount_cents, category_id, account_id, kind,
             description, is_recurring, recurring_day, subcategory_id, generated_from)
        SELECT t.id, t.date, t.amount_cents, t.category_id, t.account_id,
               CASE WHEN c.type = 'income' THEN 'ingreso' ELSE 'gasto' END,
               t.description, t.is_recurring, t.recurring_day, t.subcategory_id,
               {generated_expr}
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
    """)
    cursor.execute("DROP TABLE transactions")
    cursor.execute("ALTER TABLE transactions_new RENAME TO transactions")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_transactions_generated ON transactions(generated_from)"
    )

    violations = cursor.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise sqlite3.IntegrityError(
            f"Migration to v7: {len(violations)} FK violations: {violations[:5]}"
        )

    cursor.execute("PRAGMA user_version = 7")
    cursor.execute("PRAGMA foreign_keys = ON")


def _migrate_v8_credit_cards(conn: sqlite3.Connection) -> None:
    """v7 -> v8: credit cards and transaction card linkage.

    Cards carry a spending limit and the billing cycle days (cutoff
    and payment). Gasto_tc transactions link to a card; the available
    credit is always derived from the limit minus the month's
    spending on that card.
    """
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS credit_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            limit_cents INTEGER NOT NULL,
            cutoff_day INTEGER NOT NULL CHECK(cutoff_day BETWEEN 1 AND 31),
            payment_day INTEGER NOT NULL CHECK(payment_day BETWEEN 1 AND 31),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        SELECT COUNT(*) FROM pragma_table_info('transactions') WHERE name = 'card_id'
    """)
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            ALTER TABLE transactions ADD COLUMN card_id INTEGER
            REFERENCES credit_cards(id) ON DELETE SET NULL
        """)

    cursor.execute("PRAGMA user_version = 8")


def _migrate_v9_payment_kind(conn: sqlite3.Connection) -> None:
    """v8 -> v9: allow the pago_tc kind (credit card payments).

    SQLite cannot alter CHECK constraints, so the transactions table
    is rebuilt with the expanded kind list. Payments pull money from
    an account and reduce the card's debt.
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF")

    cursor.execute("DROP TABLE IF EXISTS transactions_new")

    cursor.execute("""
        CREATE TABLE transactions_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            category_id INTEGER REFERENCES categories(id),
            account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
            to_account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
            kind TEXT NOT NULL DEFAULT 'gasto'
                CHECK(kind IN ('ingreso', 'gasto', 'transferencia', 'gasto_tc', 'pago_tc')),
            description TEXT DEFAULT '',
            is_recurring INTEGER DEFAULT 0,
            recurring_day INTEGER,
            subcategory_id INTEGER REFERENCES subcategories(id),
            generated_from INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
            card_id INTEGER REFERENCES credit_cards(id) ON DELETE SET NULL
        )
    """)
    cursor.execute("""
        INSERT INTO transactions_new
            (id, date, amount_cents, category_id, account_id, to_account_id, kind,
             description, is_recurring, recurring_day, subcategory_id, generated_from, card_id)
        SELECT id, date, amount_cents, category_id, account_id, to_account_id, kind,
               description, is_recurring, recurring_day, subcategory_id, generated_from, card_id
        FROM transactions
    """)
    cursor.execute("DROP TABLE transactions")
    cursor.execute("ALTER TABLE transactions_new RENAME TO transactions")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_transactions_generated ON transactions(generated_from)"
    )

    violations = cursor.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise sqlite3.IntegrityError(
            f"Migration to v9: {len(violations)} FK violations: {violations[:5]}"
        )

    cursor.execute("PRAGMA user_version = 9")
    cursor.execute("PRAGMA foreign_keys = ON")


def _migrate_v10_savings(conn: sqlite3.Connection) -> None:
    """v9 -> v10: savings and investment items.

    Adds the savings table (bolsillo, bolsillo_programado, cdt and
    acciones) and links transactions to them through savings_id. New
    movement kinds: ahorro (account -> savings) and retiro (savings
    -> account), which never count as income or expense.
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS savings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL CHECK(kind IN ('bolsillo', 'bolsillo_programado', 'cdt', 'acciones')),
            target_cents INTEGER,
            rate_bp INTEGER,
            term_days INTEGER,
            current_value_cents INTEGER,
            scheduled_day INTEGER,
            scheduled_amount_cents INTEGER,
            source_account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("DROP TABLE IF EXISTS transactions_new")

    cursor.execute("""
        CREATE TABLE transactions_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            category_id INTEGER REFERENCES categories(id),
            account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
            to_account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
            kind TEXT NOT NULL DEFAULT 'gasto'
                CHECK(kind IN ('ingreso', 'gasto', 'transferencia', 'gasto_tc', 'pago_tc',
                               'ahorro', 'retiro')),
            description TEXT DEFAULT '',
            is_recurring INTEGER DEFAULT 0,
            recurring_day INTEGER,
            subcategory_id INTEGER REFERENCES subcategories(id),
            generated_from INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
            card_id INTEGER REFERENCES credit_cards(id) ON DELETE SET NULL,
            savings_id INTEGER REFERENCES savings(id) ON DELETE SET NULL
        )
    """)
    cursor.execute("""
        INSERT INTO transactions_new
            (id, date, amount_cents, category_id, account_id, to_account_id, kind,
             description, is_recurring, recurring_day, subcategory_id, generated_from,
             card_id, savings_id)
        SELECT id, date, amount_cents, category_id, account_id, to_account_id, kind,
               description, is_recurring, recurring_day, subcategory_id, generated_from,
               card_id, NULL
        FROM transactions
    """)
    cursor.execute("DROP TABLE transactions")
    cursor.execute("ALTER TABLE transactions_new RENAME TO transactions")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_transactions_generated ON transactions(generated_from)"
    )

    violations = cursor.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise sqlite3.IntegrityError(
            f"Migration to v10: {len(violations)} FK violations: {violations[:5]}"
        )

    cursor.execute("PRAGMA user_version = 10")
    cursor.execute("PRAGMA foreign_keys = ON")


def _migrate_v11_monthly_plan(conn: sqlite3.Connection) -> None:
    """v10 -> v11: store the month's total budget.

    The setup form lets the user set a total for the month. Category
    budgets only keep their own amounts, so the chosen total lives in
    ``monthly_plans`` and is returned to the form.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS monthly_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
            year INTEGER NOT NULL,
            total_cents INTEGER NOT NULL,
            UNIQUE(month, year)
        )
    """)
    conn.execute("PRAGMA user_version = 11")


def _migrate_v12_opening_balances(conn: sqlite3.Connection) -> None:
    """v11 -> v12: opening balances that belong to no month.

    Money that already existed when an account or savings item was
    created is stored on the row (accounts.starting_cents,
    savings.opening_cents) instead of an income/ahorro transaction, so
    it never shows up in a month's totals. Existing "Saldo inicial" and
    "Depósito inicial" transactions are folded into these columns.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM pragma_table_info('accounts') WHERE name = 'starting_cents'"
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute("ALTER TABLE accounts ADD COLUMN starting_cents INTEGER NOT NULL DEFAULT 0")
    cursor.execute("SELECT COUNT(*) FROM pragma_table_info('savings') WHERE name = 'opening_cents'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("ALTER TABLE savings ADD COLUMN opening_cents INTEGER NOT NULL DEFAULT 0")

    cursor.execute("""
        UPDATE accounts SET starting_cents = COALESCE((
            SELECT SUM(t.amount_cents) FROM transactions t
            WHERE t.account_id = accounts.id AND t.kind = 'ingreso'
              AND t.description = 'Saldo inicial: ' || accounts.name
        ), 0)
    """)
    cursor.execute(
        "DELETE FROM transactions WHERE kind = 'ingreso' AND description LIKE 'Saldo inicial: %'"
    )
    cursor.execute("""
        UPDATE savings SET opening_cents = COALESCE((
            SELECT SUM(t.amount_cents) FROM transactions t
            WHERE t.savings_id = savings.id AND t.kind = 'ahorro'
              AND t.description = 'Depósito inicial: ' || savings.name
        ), 0)
    """)
    cursor.execute(
        "DELETE FROM transactions WHERE kind = 'ahorro' AND description LIKE 'Depósito inicial: %'"
    )
    cursor.execute("PRAGMA user_version = 12")


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
                ("No perecederos", "🥫"),
                ("Verduras", "🥦"),
                ("Carne", "🥩"),
                ("Aseo", "🧼"),
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
        if v < 3:
            _migrate_v3_subcategory_dedup(conn)
        if v < 4:
            _migrate_v4_budget_constraint(conn)
        if v < 5:
            _migrate_v5_accounts(conn)
        if v < 6:
            _migrate_v6_account_starting_transactions(conn)
        if v < 7:
            _migrate_v7_transaction_kinds(conn)
        if v < 8:
            _migrate_v8_credit_cards(conn)
        if v < 9:
            _migrate_v9_payment_kind(conn)
        if v < 10:
            _migrate_v10_savings(conn)
        if v < 11:
            _migrate_v11_monthly_plan(conn)
        if v < 12:
            _migrate_v12_opening_balances(conn)
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
                   s.name as subcategory_name, s.icon as subcategory_icon,
                   a.name as account_name, a.icon as account_icon,
                   a2.name as to_account_name, a2.icon as to_account_icon,
                   cc.name as card_name,
                   sv.name as savings_name
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN subcategories s ON t.subcategory_id = s.id
            LEFT JOIN accounts a ON t.account_id = a.id
            LEFT JOIN accounts a2 ON t.to_account_id = a2.id
            LEFT JOIN credit_cards cc ON t.card_id = cc.id
            LEFT JOIN savings sv ON t.savings_id = sv.id
            WHERE t.date >= ? AND t.date < ?
            ORDER BY t.date DESC
        """,
            (start_date, end_date),
        )
        return [_row_to_tx(row) for row in cursor.fetchall()]


def add_transaction(
    date_val: date,
    amount: Decimal | float | int,
    category_id: int | None = None,
    description: str = "",
    is_recurring: bool = False,
    recurring_day: int | None = None,
    subcategory_id: int | None = None,
    account_id: int | None = None,
    kind: str = "gasto",
    to_account_id: int | None = None,
    card_id: int | None = None,
    savings_id: int | None = None,
) -> int:
    """Create a transaction and return its id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO transactions
                (date, amount_cents, category_id, description, is_recurring,
                 recurring_day, subcategory_id, account_id, kind, to_account_id, card_id, savings_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                date_val.isoformat(),
                _to_cents(amount),
                category_id,
                description,
                int(is_recurring),
                recurring_day,
                subcategory_id,
                account_id,
                kind,
                to_account_id,
                card_id,
                savings_id,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def update_transaction(
    trans_id: int,
    date_val: date,
    amount: Decimal | float | int,
    category_id: int | None,
    description: str,
    is_recurring: bool = False,
    recurring_day: int | None = None,
    subcategory_id: int | None = None,
    account_id: int | None = None,
    kind: str = "gasto",
    to_account_id: int | None = None,
    card_id: int | None = None,
    savings_id: int | None = None,
) -> None:
    """Update an existing transaction."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE transactions
            SET date = ?, amount_cents = ?, category_id = ?, description = ?,
                is_recurring = ?, recurring_day = ?, subcategory_id = ?,
                account_id = ?, kind = ?, to_account_id = ?, card_id = ?, savings_id = ?
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
                account_id,
                kind,
                to_account_id,
                card_id,
                savings_id,
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

    Only months up to the current one are materialized: future months
    have not happened yet, so creating their movements now would inflate
    the current balances.

    Returns:
        Number of new transactions created.
    """
    today = date.today()
    if (year, month) > (today.year, today.month):
        return 0
    last_day = calendar.monthrange(year, month)[1]
    created = 0
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, date, amount_cents, category_id, description,
                   recurring_day, subcategory_id, account_id, kind, to_account_id, card_id, savings_id
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
                     is_recurring, recurring_day, subcategory_id, generated_from, account_id, kind, to_account_id, card_id, savings_id)
                VALUES (?, ?, ?, ?, 0, NULL, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    f"{year:04d}-{month:02d}-{day:02d}",
                    t["amount_cents"],
                    t["category_id"],
                    t["description"],
                    t["subcategory_id"],
                    t["id"],
                    t["account_id"],
                    t["kind"],
                    t["to_account_id"],
                    t["card_id"],
                    t["savings_id"],
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


def set_budgets_bulk(month: int, year: int, items: list[tuple[int, Decimal | float | int]]) -> None:
    """Replace the full budget state of a month.

    Every existing budget of the month is removed and the provided
    (category_id, amount) pairs are inserted. Used by the budget
    setup form.
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
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM budgets WHERE category_id = ? AND month = ? AND year = ?",
            (category_id, month, year),
        )
        conn.commit()


def get_monthly_plan(month: int, year: int) -> Decimal | None:
    """Return the total budget the user set for a month, if any."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT total_cents FROM monthly_plans WHERE month = ? AND year = ?",
            (month, year),
        ).fetchone()
        return _to_dec(row["total_cents"]) if row else None


def set_monthly_plan(month: int, year: int, total: Decimal | float | int) -> None:
    """Create or update the total budget of a month."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO monthly_plans (month, year, total_cents)
            VALUES (?, ?, ?)
            ON CONFLICT(month, year) DO UPDATE SET total_cents = excluded.total_cents
        """,
            (month, year, _to_cents(total)),
        )
        conn.commit()


# ── Accounts ──────────────────────────────────────────────────
# An account represents where the money lives. Its balance is always
# derived from the net (income minus expense) of its linked
# transactions. Money that already existed when the account was
# created is a regular income transaction ("Saldo inicial: ...").


def _ensure_income_category(conn: sqlite3.Connection) -> int:
    """Return the id of the 'Otros ingresos' income category, creating it if missing."""
    row = conn.execute(
        "SELECT id FROM categories WHERE type = 'income' AND name = 'Otros ingresos'"
    ).fetchone()
    if row:
        return int(row["id"])
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO categories (name, type, color, icon) "
        "VALUES ('Otros ingresos', 'income', '#065F46', '💵')"
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def _row_to_account(row: sqlite3.Row) -> Account:
    return Account(
        id=row["id"],
        name=row["name"],
        type=row["type"],
        icon=row["icon"],
        color=row["color"],
        starting=_to_dec(row["starting_cents"]),
        balance=_to_dec(row["balance_cents"]),
    )


def get_accounts() -> list[Account]:
    """Return all accounts with their computed balance, oldest first.

    The balance starts from the account's opening amount and then adds
    ingresos, subtracts gastos, moves transfers between two accounts and
    treats savings movements (ahorro/retiro) as allocations that do not
    change the cash. Gastos_tc never touch cash.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.*,
                   a.starting_cents + COALESCE((
                       SELECT SUM(
                           CASE
                               WHEN t.kind = 'ingreso' THEN t.amount_cents
                               WHEN t.kind IN ('gasto', 'pago_tc') THEN -t.amount_cents
                               WHEN t.kind = 'transferencia' THEN
                                   CASE WHEN t.account_id = a.id THEN -t.amount_cents
                                        WHEN t.to_account_id = a.id THEN t.amount_cents
                                        ELSE 0 END
                               ELSE 0
                           END
                       )
                       FROM transactions t
                       WHERE t.account_id = a.id OR t.to_account_id = a.id
                   ), 0) as balance_cents
            FROM accounts a
            ORDER BY a.created_at, a.id
        """)
        return [_row_to_account(row) for row in cursor.fetchall()]


def add_account(
    name: str,
    acct_type: str,
    starting_amount: Decimal | float | int,
    icon: str | None = None,
    color: str | None = None,
) -> int:
    """Create an account and return its id.

    ``starting_amount`` is the opening balance: money that already
    existed before using the app. It belongs to no month and is stored
    on the account, not as a transaction.
    """
    default_icon, default_color = ACCOUNT_TYPE_DEFAULTS.get(acct_type, ("💵", "#10B981"))
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO accounts (name, type, icon, color, starting_cents)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                acct_type,
                icon or default_icon,
                color or default_color,
                _to_cents(starting_amount),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def update_account(
    account_id: int,
    name: str,
    acct_type: str | None = None,
    starting_amount: Decimal | float | int | None = None,
) -> None:
    """Update an account's name, type and opening balance."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if acct_type is not None:
            icon, color = ACCOUNT_TYPE_DEFAULTS.get(acct_type, ("💵", "#10B981"))
            cursor.execute(
                "UPDATE accounts SET name = ?, type = ?, icon = ?, color = ? WHERE id = ?",
                (name, acct_type, icon, color, account_id),
            )
        else:
            cursor.execute("UPDATE accounts SET name = ? WHERE id = ?", (name, account_id))
        if starting_amount is not None:
            cursor.execute(
                "UPDATE accounts SET starting_cents = ? WHERE id = ?",
                (_to_cents(starting_amount), account_id),
            )
        conn.commit()


def delete_account(account_id: int) -> None:
    """Delete an account, leaving its transactions unlinked."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        conn.commit()


# ── Credit cards ──────────────────────────────────────────────
# A card has a spending limit and billing cycle days. Its spent and
# available amounts are always derived from the current month's
# gasto_tc transactions linked to it.


def _closed_cycle_window(cutoff_day: int, today: date) -> tuple[date, date] | None:
    """Return the (start, end] dates of the closed billing cycle.

    The cycle runs from the previous cutoff (exclusive) to the current
    cutoff (inclusive). None means the cycle is still open (today is
    before this month's cutoff day).
    """
    current_days = calendar.monthrange(today.year, today.month)[1]
    cutoff_this = date(today.year, today.month, min(cutoff_day, current_days))
    if today < cutoff_this:
        return None
    if today.month == 1:
        prev_year, prev_month = today.year - 1, 12
    else:
        prev_year, prev_month = today.year, today.month - 1
    prev_days = calendar.monthrange(prev_year, prev_month)[1]
    prev_cutoff = date(prev_year, prev_month, min(cutoff_day, prev_days))
    return (prev_cutoff, cutoff_this)


def _card_debt(conn: sqlite3.Connection, card_id: int, cutoff_day: int, today: date) -> Decimal:
    """Return the net debt of a card in its closed cycle.

    Spending belongs to the cycle that just closed (previous cutoff,
    current cutoff]; payments made after the current cutoff reduce
    that cycle's debt.
    """
    window = _closed_cycle_window(cutoff_day, today)
    if window is None:
        return Decimal("0.00")
    prev_cutoff, cutoff_this = window
    row = conn.execute(
        """
        SELECT COALESCE(SUM(
            CASE WHEN kind = 'gasto_tc' AND date > ? AND date <= ? THEN amount_cents
                 WHEN kind = 'pago_tc' AND date > ? THEN -amount_cents
                 ELSE 0 END
        ), 0) as cents
        FROM transactions
        WHERE card_id = ? AND kind IN ('gasto_tc', 'pago_tc')
    """,
        (
            prev_cutoff.isoformat(),
            cutoff_this.isoformat(),
            cutoff_this.isoformat(),
            card_id,
        ),
    ).fetchone()
    return _to_dec(row["cents"])


def _row_to_card(row: sqlite3.Row, conn: sqlite3.Connection, today: date) -> CreditCard:
    limit = _to_dec(row["limit_cents"])
    spent = _to_dec(row["spent_cents"])
    paid = _to_dec(row["paid_cents"])
    debt = _card_debt(conn, row["id"], row["cutoff_day"], today)
    return CreditCard(
        id=row["id"],
        name=row["name"],
        limit=limit,
        cutoff_day=row["cutoff_day"],
        payment_day=row["payment_day"],
        spent=spent,
        paid=paid,
        debt=debt,
        available=limit - spent + paid,
    )


def get_credit_cards(today: date | None = None) -> list[CreditCard]:
    """Return all credit cards with spending, payments, debt and available credit."""
    today = today or date.today()
    with get_connection() as conn:
        cursor = conn.cursor()
        start_date, end_date = _month_window(today.month, today.year)
        cursor.execute(
            """
            SELECT cc.*,
                   COALESCE((
                       SELECT SUM(t.amount_cents)
                       FROM transactions t
                       WHERE t.card_id = cc.id
                         AND t.kind = 'gasto_tc'
                         AND t.date >= ? AND t.date < ?
                   ), 0) as spent_cents,
                   COALESCE((
                       SELECT SUM(t.amount_cents)
                       FROM transactions t
                       WHERE t.card_id = cc.id
                         AND t.kind = 'pago_tc'
                         AND t.date >= ? AND t.date < ?
                   ), 0) as paid_cents
            FROM credit_cards cc
            ORDER BY cc.created_at, cc.id
        """,
            (start_date, end_date, start_date, end_date),
        )
        return [_row_to_card(row, conn, today) for row in cursor.fetchall()]


def add_credit_card(
    name: str,
    limit: Decimal | float | int,
    cutoff_day: int,
    payment_day: int,
) -> int:
    """Create a credit card and return its id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO credit_cards (name, limit_cents, cutoff_day, payment_day)
            VALUES (?, ?, ?, ?)
            """,
            (name, _to_cents(limit), cutoff_day, payment_day),
        )
        conn.commit()
        return int(cursor.lastrowid)


def update_credit_card(
    card_id: int,
    name: str,
    limit: Decimal | float | int,
    cutoff_day: int,
    payment_day: int,
) -> None:
    """Update a credit card."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE credit_cards
            SET name = ?, limit_cents = ?, cutoff_day = ?, payment_day = ?
            WHERE id = ?
            """,
            (name, _to_cents(limit), cutoff_day, payment_day, card_id),
        )
        conn.commit()


def delete_credit_card(card_id: int) -> None:
    """Delete a credit card, leaving its transactions unlinked."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM credit_cards WHERE id = ?", (card_id,))
        conn.commit()


# ── Savings and investments ───────────────────────────────────
# Bolsillos hold money moved from accounts. Their balance is always
# derived from ahorro (deposit) minus retiro (withdrawal) movements.
# A bolsillo_programado adds a recurring ahorro template that the
# recurring engine materializes every month.


def _row_to_savings(row: sqlite3.Row) -> SavingsItem:
    balance = _to_dec(row["balance_cents"])
    current_value = (
        _to_dec(row["current_value_cents"]) if row["current_value_cents"] is not None else None
    )
    return SavingsItem(
        id=row["id"],
        name=row["name"],
        kind=row["kind"],
        target=_to_dec(row["target_cents"]) if row["target_cents"] is not None else None,
        rate_bp=row["rate_bp"],
        term_days=row["term_days"],
        current_value=current_value,
        scheduled_day=row["scheduled_day"],
        scheduled_amount=(
            _to_dec(row["scheduled_amount_cents"])
            if row["scheduled_amount_cents"] is not None
            else None
        ),
        source_account_id=row["source_account_id"],
        opening=_to_dec(row["opening_cents"]),
        balance=balance,
        invested=balance,
    )


def get_savings() -> list[SavingsItem]:
    """Return all savings items with their computed balance.

    ``opening`` is money that already existed when the item was created
    (e.g. an existing CDT) and belongs to no month; the balance is that
    opening amount plus the net of ahorro minus retiro movements.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*,
                   s.opening_cents + COALESCE((
                       SELECT SUM(CASE WHEN t.kind = 'ahorro' THEN t.amount_cents
                                       WHEN t.kind = 'retiro' THEN -t.amount_cents
                                       ELSE 0 END)
                       FROM transactions t
                       WHERE t.savings_id = s.id
                   ), 0) as balance_cents
            FROM savings s
            ORDER BY s.created_at, s.id
        """)
        return [_row_to_savings(row) for row in cursor.fetchall()]


def add_savings(
    name: str,
    kind: str,
    target: Decimal | float | int | None = None,
    rate_bp: int | None = None,
    term_days: int | None = None,
    current_value: Decimal | float | int | None = None,
    scheduled_day: int | None = None,
    scheduled_amount: Decimal | float | int | None = None,
    source_account_id: int | None = None,
    initial_amount: Decimal | float | int | None = None,
    initial_account_id: int | None = None,
) -> int:
    """Create a savings item and return its id.

    ``initial_amount`` is the opening balance: money that already
    existed before using the app (e.g. an existing CDT). It belongs to
    no month and is stored on the item, not as an ahorro movement.
    A bolsillo_programado also creates a recurring ahorro template that
    materializes every month on the scheduled day.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO savings
                (name, kind, target_cents, rate_bp, term_days, current_value_cents,
                 scheduled_day, scheduled_amount_cents, source_account_id, opening_cents)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                kind,
                _to_cents(target) if target is not None else None,
                rate_bp,
                term_days,
                _to_cents(current_value) if current_value is not None else None,
                scheduled_day,
                _to_cents(scheduled_amount) if scheduled_amount is not None else None,
                source_account_id,
                _to_cents(initial_amount) if initial_amount is not None else 0,
            ),
        )
        item_id = int(cursor.lastrowid)

        if kind == "bolsillo_programado" and scheduled_day is not None:
            template_date = date(date.today().year, date.today().month, scheduled_day)
            cursor.execute(
                """
                INSERT INTO transactions
                    (date, amount_cents, category_id, description, is_recurring,
                     recurring_day, subcategory_id, account_id, kind, to_account_id, card_id, savings_id)
                VALUES (?, ?, NULL, ?, 1, ?, NULL, ?, 'ahorro', NULL, NULL, ?)
                """,
                (
                    template_date.isoformat(),
                    _to_cents(scheduled_amount) if scheduled_amount is not None else 0,
                    f"Ahorro programado: {name}",
                    scheduled_day,
                    source_account_id,
                    item_id,
                ),
            )

        conn.commit()
        return item_id


def update_savings(
    item_id: int,
    name: str,
    kind: str,
    target: Decimal | float | int | None = None,
    rate_bp: int | None = None,
    term_days: int | None = None,
    current_value: Decimal | float | int | None = None,
    scheduled_day: int | None = None,
    scheduled_amount: Decimal | float | int | None = None,
    source_account_id: int | None = None,
) -> None:
    """Update a savings item, keeping its recurring template in sync."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE savings
            SET name = ?, kind = ?, target_cents = ?, rate_bp = ?, term_days = ?,
                current_value_cents = ?, scheduled_day = ?, scheduled_amount_cents = ?,
                source_account_id = ?
            WHERE id = ?
            """,
            (
                name,
                kind,
                _to_cents(target) if target is not None else None,
                rate_bp,
                term_days,
                _to_cents(current_value) if current_value is not None else None,
                scheduled_day,
                _to_cents(scheduled_amount) if scheduled_amount is not None else None,
                source_account_id,
                item_id,
            ),
        )
        if kind == "bolsillo_programado" and scheduled_day is not None:
            template_date = date(date.today().year, date.today().month, scheduled_day)
            cursor.execute(
                """
                UPDATE transactions
                SET date = ?, amount_cents = ?, account_id = ?, recurring_day = ?
                WHERE is_recurring = 1 AND generated_from IS NULL
                  AND kind = 'ahorro' AND savings_id = ?
                """,
                (
                    template_date.isoformat(),
                    _to_cents(scheduled_amount) if scheduled_amount is not None else 0,
                    source_account_id,
                    scheduled_day,
                    item_id,
                ),
            )
        conn.commit()


def delete_savings(item_id: int) -> None:
    """Delete a savings item and its recurring template."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM transactions WHERE is_recurring = 1 AND generated_from IS NULL "
            "AND kind = 'ahorro' AND savings_id = ?",
            (item_id,),
        )
        cursor.execute("DELETE FROM savings WHERE id = ?", (item_id,))
        conn.commit()


# ── Aggregations ──────────────────────────────────────────────


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
        # purchases, so the user still sees where the money went.
        cursor.execute(
            """
            SELECT c.name, t.kind, SUM(t.amount_cents) as total_cents
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.date >= ? AND t.date < ?
              AND t.kind IN ('ingreso', 'gasto', 'gasto_tc')
            GROUP BY c.name, t.kind
        """,
            (start_date, end_date),
        )

        by_category: dict[str, Decimal] = {}
        for row in cursor.fetchall():
            name = row["name"]
            by_category[name] = by_category.get(name, Decimal("0.00")) + _to_dec(row["total_cents"])

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
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        start_date, end_date = _month_window(month, year)
        kind_filter = (
            "t.kind = 'ingreso'" if cat_type == "income" else "t.kind IN ('gasto', 'gasto_tc')"
        )
        cursor.execute(
            f"""
            SELECT c.name, SUM(t.amount_cents) as total_cents, c.color, c.icon
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE {kind_filter} AND t.date >= ? AND t.date < ?
            GROUP BY c.id
            ORDER BY total_cents DESC
        """,
            (start_date, end_date),
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
                AND t.kind IN ('gasto', 'gasto_tc')
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


KIND_LABELS = {
    "ingreso": "Ingreso",
    "gasto": "Gasto",
    "transferencia": "Transferencia",
    "gasto_tc": "Gasto TC",
    "pago_tc": "Pago TC",
    "ahorro": "Ahorro",
    "retiro": "Retiro",
}


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
                KIND_LABELS.get(t.kind, t.kind),
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
