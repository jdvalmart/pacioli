"""Schema versioning, migrations, the Postgres schema and default seeds."""

import os
import sqlite3
from typing import Any

from app import clock
from app.db.backup import backup_database
from app.db.connection import (
    _adapt_sql,
    _ddl,
    _get_version,
    _has_column,
    _insert_get_id,
    _is_postgres,
    _set_version,
    get_backup_dir,
    get_connection,
    get_db_path,
)
from app.db.models import CATEGORY_ROLE_SAVINGS

SCHEMA_VERSION = 18


# Historical location (repo/data/budget.db); imported once if present.
LEGACY_DB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "budget.db")
)


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


# Versioned schema via PRAGMA user_version. A new DB walks the same
# path as an old one: v0 -> v1 (baseline) -> v2 (cents).


def _user_version(conn) -> int:  # type: ignore[no-untyped-def]
    return _get_version(conn)


def _migrate_v1_baseline(conn: sqlite3.Connection) -> None:
    """v0 -> v1: historical schema (idempotent on existing databases)."""
    cursor = conn.cursor()

    cursor.execute(
        _ddl("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            color TEXT DEFAULT '#3B82F6',
            icon TEXT DEFAULT '📁'
        )
    """)
    )

    cursor.execute(
        _ddl("""
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
    )

    cursor.execute(
        _ddl("""
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
    )

    cursor.execute(
        _ddl("""
        CREATE TABLE IF NOT EXISTS subcategories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '📁',
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
            UNIQUE(category_id, name)
        )
    """)
    )

    cursor.execute(
        _ddl("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL CHECK(role IN ('user', 'ai')),
            message TEXT NOT NULL,
            month INTEGER,
            year INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    )

    cursor.execute(
        _ddl("""
        CREATE TABLE IF NOT EXISTS ai_learnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            correction TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    )

    cursor.execute(
        _ddl("""
        CREATE TABLE IF NOT EXISTS desc_learnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            subcategory TEXT,
            ai_description TEXT NOT NULL,
            user_description TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    )

    if not _has_column(conn, "transactions", "subcategory_id"):
        cursor.execute("""
            ALTER TABLE transactions ADD COLUMN subcategory_id INTEGER
            REFERENCES subcategories(id)
        """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_budgets_month_year ON budgets(month, year)")

    _set_version(conn, 1)


def _migrate_v2_cents(conn: sqlite3.Connection) -> None:
    """v1 -> v2: money in INTEGER cents + recurrence support.

    Rebuilds transactions and budgets (SQLite cannot change a column
    type with ALTER), converting with ROUND(amount*100) and checking
    referential integrity at the end.
    """
    cursor = conn.cursor()
    if not _is_postgres():
        cursor.execute("PRAGMA foreign_keys = OFF")

    cursor.execute(
        _ddl("""
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
    )
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

    cursor.execute(
        _ddl("""
        CREATE TABLE budgets_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL REFERENCES categories(id),
            month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
            year INTEGER NOT NULL,
            amount_cents INTEGER NOT NULL,
            UNIQUE(category_id, month, year)
        )
    """)
    )
    cursor.execute("""
        INSERT INTO budgets_new (id, category_id, month, year, amount_cents)
        SELECT id, category_id, month, year, CAST(ROUND(amount * 100) AS INTEGER)
        FROM budgets
    """)
    cursor.execute("DROP TABLE budgets")
    cursor.execute("ALTER TABLE budgets_new RENAME TO budgets")

    cursor.execute(
        _ddl("""
        CREATE TABLE IF NOT EXISTS recurring_materialized (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
            month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
            year INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(template_id, month, year)
        )
    """)
    )

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

    _set_version(conn, 2)
    if not _is_postgres():
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
    if not _is_postgres():
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

    cursor.execute(
        _ddl("""
        CREATE TABLE subcategories_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '📁',
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
            UNIQUE(category_id, name)
        )
    """)
    )
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

    _set_version(conn, 3)
    if not _is_postgres():
        cursor.execute("PRAGMA foreign_keys = ON")


def _migrate_v4_budget_constraint(conn: sqlite3.Connection) -> None:
    """v3 -> v4: rebuild budgets with UNIQUE(category_id, month, year).

    Some desktop-era migration paths rebuilt the budgets table without
    the unique constraint, so upserts fail with an ON CONFLICT
    mismatch. The migration keeps the most recent row (highest id) of
    each duplicate group and rebuilds the table with the constraint.
    """
    cursor = conn.cursor()
    if not _is_postgres():
        cursor.execute("PRAGMA foreign_keys = OFF")

    # Last write wins: keep only the highest id per (category, month, year).
    cursor.execute("""
        DELETE FROM budgets
        WHERE id NOT IN (
            SELECT MAX(id) FROM budgets GROUP BY category_id, month, year
        )
    """)

    cursor.execute(
        _ddl("""
        CREATE TABLE budgets_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL REFERENCES categories(id),
            month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
            year INTEGER NOT NULL,
            amount_cents INTEGER NOT NULL,
            UNIQUE(category_id, month, year)
        )
    """)
    )
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

    _set_version(conn, 4)
    if not _is_postgres():
        cursor.execute("PRAGMA foreign_keys = ON")


def _migrate_v5_accounts(conn: sqlite3.Connection) -> None:
    """v4 -> v5: accounts table and transaction account linkage.

    Accounts represent where the money lives (physical wallet, digital
    wallet, savings, bank). Their balance is always derived from the
    initial balance plus the linked transactions, never edited by hand.
    """
    cursor = conn.cursor()

    cursor.execute(
        _ddl("""
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
    )

    if not _has_column(conn, "transactions", "account_id"):
        cursor.execute("""
            ALTER TABLE transactions ADD COLUMN account_id INTEGER
            REFERENCES accounts(id) ON DELETE SET NULL
        """)

    _set_version(conn, 5)


def _migrate_v6_account_starting_transactions(conn: sqlite3.Connection) -> None:
    """v5 -> v6: drop the initial_balance column from accounts.

    Starting money is now an ordinary income transaction ("Saldo
    inicial: <name>") linked to the account, so it flows naturally
    into income reports and the account balance. Any existing initial
    balance is materialized as such a transaction before the column
    is removed.
    """
    cursor = conn.cursor()
    if not _is_postgres():
        cursor.execute("PRAGMA foreign_keys = OFF")

    income_cat = cursor.execute(
        "SELECT id FROM categories WHERE type = 'income' AND name = 'Otros ingresos'"
    ).fetchone()
    if income_cat is None:
        income_cat_id = _insert_get_id(
            cursor,
            _ddl(
                "INSERT INTO categories (name, type, color, icon) VALUES ('Otros ingresos', 'income', '#065F46', '💵')"
            ),
            (),
        )
    else:
        income_cat_id = income_cat["id"]

    rows = []
    has_initial_column = _has_column(conn, "accounts", "initial_balance_cents")
    if has_initial_column:
        rows = cursor.execute(
            "SELECT id, name, initial_balance_cents, created_at FROM accounts "
            "WHERE initial_balance_cents != 0"
        ).fetchall()
    for row in rows:
        created_date = (row["created_at"] or "")[:10] or clock.today().isoformat()
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

    cursor.execute(
        _ddl("""
        CREATE TABLE accounts_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL CHECK(type IN ('efectivo', 'digital', 'ahorros', 'banco')),
            icon TEXT NOT NULL DEFAULT '💵',
            color TEXT NOT NULL DEFAULT '#10B981',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    )
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

    _set_version(conn, 6)
    if not _is_postgres():
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
    if not _is_postgres():
        cursor.execute("PRAGMA foreign_keys = OFF")

    # Safe against interrupted previous runs: a crash mid-rebuild can
    # leave the staging table behind.
    cursor.execute("DROP TABLE IF EXISTS transactions_new")

    cursor.execute(
        _ddl("""
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
    )
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

    _set_version(conn, 7)
    if not _is_postgres():
        cursor.execute("PRAGMA foreign_keys = ON")


def _migrate_v8_credit_cards(conn: sqlite3.Connection) -> None:
    """v7 -> v8: credit cards and transaction card linkage.

    Cards carry a spending limit and the billing cycle days (cutoff
    and payment). Gasto_tc transactions link to a card; the available
    credit is always derived from the limit minus the month's
    spending on that card.
    """
    cursor = conn.cursor()

    cursor.execute(
        _ddl("""
        CREATE TABLE IF NOT EXISTS credit_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            limit_cents INTEGER NOT NULL,
            cutoff_day INTEGER NOT NULL CHECK(cutoff_day BETWEEN 1 AND 31),
            payment_day INTEGER NOT NULL CHECK(payment_day BETWEEN 1 AND 31),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    )

    if not _has_column(conn, "transactions", "card_id"):
        cursor.execute("""
            ALTER TABLE transactions ADD COLUMN card_id INTEGER
            REFERENCES credit_cards(id) ON DELETE SET NULL
        """)

    _set_version(conn, 8)


def _migrate_v9_payment_kind(conn: sqlite3.Connection) -> None:
    """v8 -> v9: allow the pago_tc kind (credit card payments).

    SQLite cannot alter CHECK constraints, so the transactions table
    is rebuilt with the expanded kind list. Payments pull money from
    an account and reduce the card's debt.
    """
    cursor = conn.cursor()
    if not _is_postgres():
        cursor.execute("PRAGMA foreign_keys = OFF")

    cursor.execute("DROP TABLE IF EXISTS transactions_new")

    cursor.execute(
        _ddl("""
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
    )
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

    _set_version(conn, 9)
    if not _is_postgres():
        cursor.execute("PRAGMA foreign_keys = ON")


def _migrate_v10_savings(conn: sqlite3.Connection) -> None:
    """v9 -> v10: savings and investment items.

    Adds the savings table (bolsillo, bolsillo_programado, cdt and
    acciones) and links transactions to them through savings_id. New
    movement kinds: ahorro (account -> savings) and retiro (savings
    -> account), which never count as income or expense.
    """
    cursor = conn.cursor()
    if not _is_postgres():
        cursor.execute("PRAGMA foreign_keys = OFF")

    cursor.execute(
        _ddl("""
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
    )

    cursor.execute("DROP TABLE IF EXISTS transactions_new")

    cursor.execute(
        _ddl("""
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
    )
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

    _set_version(conn, 10)
    if not _is_postgres():
        cursor.execute("PRAGMA foreign_keys = ON")


def _migrate_v11_monthly_plan(conn: sqlite3.Connection) -> None:
    """v10 -> v11: store the month's total budget.

    The setup form lets the user set a total for the month. Category
    budgets only keep their own amounts, so the chosen total lives in
    ``monthly_plans`` and is returned to the form.
    """
    conn.execute(
        _ddl("""
        CREATE TABLE IF NOT EXISTS monthly_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
            year INTEGER NOT NULL,
            total_cents INTEGER NOT NULL,
            UNIQUE(month, year)
        )
    """)
    )
    _set_version(conn, 11)


def _migrate_v12_opening_balances(conn: sqlite3.Connection) -> None:
    """v11 -> v12: opening balances that belong to no month.

    Money that already existed when an account or savings item was
    created is stored on the row (accounts.starting_cents,
    savings.opening_cents) instead of an income/ahorro transaction, so
    it never shows up in a month's totals. Existing "Saldo inicial" and
    "Depósito inicial" transactions are folded into these columns.
    """
    cursor = conn.cursor()
    if not _has_column(conn, "accounts", "starting_cents"):
        cursor.execute("ALTER TABLE accounts ADD COLUMN starting_cents INTEGER NOT NULL DEFAULT 0")
    if not _has_column(conn, "savings", "opening_cents"):
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
    _set_version(conn, 12)


def _migrate_v13_installments(conn: sqlite3.Connection) -> None:
    """v12 -> v13: installment purchases on credit cards.

    A gasto_tc can be paid in ``installments`` cuotas with a total
    interest (``interest_bp``). One installment is due per billing cycle
    until the purchase is covered.
    """
    cursor = conn.cursor()
    if _is_postgres():
        cursor.execute(
            "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS installments INTEGER NOT NULL DEFAULT 1"
        )
        cursor.execute(
            "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS interest_bp INTEGER NOT NULL DEFAULT 0"
        )
    else:
        has_inst = _has_column(conn, "transactions", "installments")
        if not has_inst:
            cursor.execute(
                "ALTER TABLE transactions ADD COLUMN installments INTEGER NOT NULL DEFAULT 1"
            )
        has_int = _has_column(conn, "transactions", "interest_bp")
        if not has_int:
            cursor.execute(
                "ALTER TABLE transactions ADD COLUMN interest_bp INTEGER NOT NULL DEFAULT 0"
            )
    _set_version(conn, 13)


def _migrate_v14_savings_dividends(conn: sqlite3.Connection) -> None:
    """v13 -> v14: dividends received on a stock holding.

    Stocks pay no term but do pay dividends; the total is tracked on the
    item so the return can combine price growth and dividends.
    """
    cursor = conn.cursor()
    if _is_postgres():
        cursor.execute(
            "ALTER TABLE savings ADD COLUMN IF NOT EXISTS dividends_cents INTEGER NOT NULL DEFAULT 0"
        )
    elif not _has_column(conn, "savings", "dividends_cents"):
        cursor.execute("ALTER TABLE savings ADD COLUMN dividends_cents INTEGER NOT NULL DEFAULT 0")
    _set_version(conn, 14)


def _migrate_v15_savings_category(conn: sqlite3.Connection) -> None:
    """v14 -> v15: link a savings item to a budget category.

    A bolsillo can be tied to an expense category so the budget shows the
    amount set aside (a reserve) before it is actually paid.
    """
    cursor = conn.cursor()
    if _is_postgres():
        cursor.execute(
            "ALTER TABLE savings ADD COLUMN IF NOT EXISTS "
            "category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL"
        )
    elif not _has_column(conn, "savings", "category_id"):
        cursor.execute(
            "ALTER TABLE savings ADD COLUMN category_id INTEGER "
            "REFERENCES categories(id) ON DELETE SET NULL"
        )
    _set_version(conn, 15)


def _migrate_v16_category_roles(conn: sqlite3.Connection) -> None:
    """v15 -> v16: system roles for categories, starting with savings.

    Savings movements used to be grouped under the expense category
    literally named "Ahorro", so renaming it silently dropped them from
    budgets. ``categories.role`` marks that category instead; at most one
    category may hold each role. Runs on SQLite and Postgres.
    """
    cursor = conn.cursor()
    if not _has_column(conn, "categories", "role"):
        cursor.execute("ALTER TABLE categories ADD COLUMN role TEXT")
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_categories_role "
        "ON categories(role) WHERE role IS NOT NULL"
    )
    cursor.execute(
        """
        UPDATE categories SET role = ?
        WHERE id = (
            SELECT id FROM categories
            WHERE type = 'expense' AND LOWER(name) = 'ahorro'
            ORDER BY id LIMIT 1
        )
          AND NOT EXISTS (SELECT 1 FROM categories WHERE role = ?)
        """,
        (CATEGORY_ROLE_SAVINGS, CATEGORY_ROLE_SAVINGS),
    )
    _set_version(conn, 16)


AI_LEFTOVER_TABLES = ("chat_history", "ai_learnings", "desc_learnings")


def _migrate_v17_drop_ai_tables(conn: sqlite3.Connection) -> None:
    """v16 -> v17: drop the tables of the removed AI assistant.

    ``chat_history``, ``ai_learnings`` and ``desc_learnings`` were created by
    the v1 baseline for the Ollama chat, which was removed from the app; no
    code reads them. Existing SQLite data is preserved in the automatic
    pre-migration backup. Runs on SQLite and Postgres.
    """
    cursor = conn.cursor()
    for table in AI_LEFTOVER_TABLES:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
    _set_version(conn, 17)


def _migrate_v18_loans(conn: sqlite3.Connection) -> None:
    """v17 -> v18: loans (credits other than cards) and payments linked to them.

    A loan stores the balance the user confirmed with the bank (``balance_cents``
    on ``as_of``), its effective annual rate (optional), the regular installment
    and the budget category its payments count in. A payment is an ordinary
    ``gasto`` with ``transactions.loan_id`` set. Runs on SQLite and Postgres.
    """
    cursor = conn.cursor()
    cursor.execute(
        _ddl(
            """
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            balance_cents INTEGER NOT NULL,
            as_of TEXT NOT NULL,
            rate_bp INTEGER,
            installment_cents INTEGER NOT NULL,
            payment_day INTEGER CHECK(payment_day BETWEEN 1 AND 31),
            category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
        )
    )
    if not _has_column(conn, "transactions", "loan_id"):
        cursor.execute(
            "ALTER TABLE transactions ADD COLUMN loan_id INTEGER "
            "REFERENCES loans(id) ON DELETE SET NULL"
        )
    _set_version(conn, 18)


def _create_postgres_schema(conn) -> None:  # type: ignore[no-untyped-def]
    """Create the final schema on a fresh Postgres database.

    SQLite installs walk the v0->v14 migration chain; on a brand-new
    Postgres there is no legacy data to preserve, so create the final
    tables in dependency order instead.
    """
    ddl = [
        """
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            color TEXT DEFAULT '#3B82F6',
            icon TEXT DEFAULT '📁',
            role TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS subcategories (
            id SERIAL PRIMARY KEY,
            category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '📁',
            UNIQUE(category_id, name)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL CHECK(type IN ('efectivo', 'digital', 'ahorros', 'banco')),
            icon TEXT NOT NULL DEFAULT '💵',
            color TEXT NOT NULL DEFAULT '#10B981',
            starting_cents INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS budgets (
            id SERIAL PRIMARY KEY,
            category_id INTEGER NOT NULL REFERENCES categories(id),
            month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
            year INTEGER NOT NULL,
            amount_cents INTEGER NOT NULL,
            UNIQUE(category_id, month, year)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS savings (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL CHECK(kind IN ('bolsillo', 'bolsillo_programado', 'cdt', 'acciones')),
            category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
            target_cents INTEGER,
            rate_bp INTEGER,
            term_days INTEGER,
            current_value_cents INTEGER,
            dividends_cents INTEGER NOT NULL DEFAULT 0,
            scheduled_day INTEGER,
            scheduled_amount_cents INTEGER,
            source_account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
            opening_cents INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS credit_cards (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            limit_cents INTEGER NOT NULL,
            cutoff_day INTEGER NOT NULL CHECK(cutoff_day BETWEEN 1 AND 31),
            payment_day INTEGER NOT NULL CHECK(payment_day BETWEEN 1 AND 31),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
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
            card_id INTEGER,
            savings_id INTEGER REFERENCES savings(id) ON DELETE SET NULL,
            installments INTEGER NOT NULL DEFAULT 1,
            interest_bp INTEGER NOT NULL DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS monthly_plans (
            id SERIAL PRIMARY KEY,
            month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
            year INTEGER NOT NULL,
            total_cents INTEGER NOT NULL,
            UNIQUE(month, year)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS recurring_materialized (
            id SERIAL PRIMARY KEY,
            template_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
            month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
            year INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(template_id, month, year)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_generated ON transactions(generated_from)",
        "CREATE INDEX IF NOT EXISTS idx_budgets_month_year ON budgets(month, year)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_categories_role ON categories(role) WHERE role IS NOT NULL",
    ]
    # transactions REFERENCES savings, so savings must exist before
    # the transactions FK is validated only on write; order above is fine.
    for statement in ddl:
        conn.execute(_ddl(statement))
    _migrate_v18_loans(conn)


def _ensure_savings_category(cursor: Any) -> None:
    """Make sure one expense category holds the savings role.

    Savings movements are grouped under it in budgets and reports. An
    existing expense category named "Ahorro" is adopted; otherwise one is
    created. Idempotent: does nothing once a category has the role.
    """
    cursor.execute("SELECT 1 FROM categories WHERE role = ?", (CATEGORY_ROLE_SAVINGS,))
    if cursor.fetchone() is not None:
        return
    cursor.execute(
        "SELECT id FROM categories WHERE type = 'expense' AND LOWER(name) = 'ahorro' "
        "ORDER BY id LIMIT 1"
    )
    row = cursor.fetchone()
    if row is not None:
        cursor.execute(
            "UPDATE categories SET role = ? WHERE id = ?", (CATEGORY_ROLE_SAVINGS, row["id"])
        )
        return
    cursor.execute("SELECT 1 FROM categories WHERE LOWER(name) = 'ahorro'")
    name = "Ahorro" if cursor.fetchone() is None else "Ahorro e inversión"
    cursor.execute(
        "INSERT INTO categories (name, type, color, icon, role) VALUES (?, 'expense', ?, ?, ?)",
        (name, "#F59E0B", "🐷", CATEGORY_ROLE_SAVINGS),
    )


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
        if _is_postgres():
            cursor.execute(
                _adapt_sql(
                    "INSERT INTO categories (name, type, color, icon) VALUES (?, ?, ?, ?) ON CONFLICT DO NOTHING"
                ),
                (name, cat_type, color, icon),
            )
        else:
            cursor.execute(
                "INSERT OR IGNORE INTO categories (name, type, color, icon) VALUES (?, ?, ?, ?)",
                (name, cat_type, color, icon),
            )

    # Older schemas (replayed by migration tests) have no role column yet.
    if _has_column(conn, "categories", "role"):
        _ensure_savings_category(cursor)

    default_subcategories = [
        # Income
        (
            "Salario",
            [
                ("Salario mensual", "💰"),
                ("Bonos", "🎁"),
                ("Horas extra", "⏰"),
                ("Comisiones", "🤝"),
                ("Viáticos", "🚗"),
                ("Prima", "🏦"),
            ],
        ),
        (
            "Freelance",
            [
                ("Proyectos", "📁"),
                ("Servicios", "🛠️"),
                ("Clientes", "👥"),
                ("Contratos", "📝"),
                ("Honorarios", "💼"),
            ],
        ),
        (
            "Inversiones",
            [
                ("Rendimientos", "📈"),
                ("Intereses", "💹"),
                ("Dividendos", "💵"),
                ("Ganancias", "🏆"),
                ("Cripto", "🪙"),
            ],
        ),
        (
            "Otros ingresos",
            [
                ("Regalos", "🎁"),
                ("Reembolsos", "↩️"),
                ("Subsidio", "🤲"),
                ("Préstamos", "💸"),
                ("Ventas", "🏷️"),
            ],
        ),
        # Expense
        (
            "Vivienda",
            [
                ("Arriendo", "🏠"),
                ("Mantenimiento", "🔧"),
                ("Seguro", "🛡️"),
                ("Administración", "🏢"),
                ("Reparaciones", "🧰"),
                ("Impuestos", "🧾"),
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
            "Transporte",
            [
                ("Gasolina", "⛽"),
                ("Transporte público", "🚌"),
                ("Estacionamiento", "🅿️"),
                ("Uber/Taxi", "🚕"),
                ("Peajes", "🛣️"),
                ("Mantenimiento", "🔧"),
                ("SOAT", "📄"),
            ],
        ),
        (
            "Entretenimiento",
            [
                ("Cine/Streaming", "🎬"),
                ("Música", "🎵"),
                ("Salidas", "🍸"),
                ("Hobbies", "🎨"),
                ("Videojuegos", "🎮"),
                ("Eventos", "🎟️"),
            ],
        ),
        (
            "Salud",
            [
                ("Consultas", "🩺"),
                ("Medicamentos", "💊"),
                ("Seguro médico", "🛡️"),
                ("Odontología", "🦷"),
                ("Exámenes", "🔬"),
                ("Terapias", "🧘"),
            ],
        ),
        (
            "Educación",
            [
                ("Matrícula", "🎓"),
                ("Libros", "📖"),
                ("Cursos", "💻"),
                ("Útiles", "✏️"),
                ("Uniformes", "👕"),
                ("Plataformas", "🌐"),
            ],
        ),
        (
            "Compras",
            [
                ("Ropa", "👕"),
                ("Calzado", "👟"),
                ("Regalos", "🎁"),
                ("Tecnología", "📱"),
                ("Hogar", "🛋️"),
                ("Accesorios", "💍"),
            ],
        ),
        (
            "Otros gastos",
            [
                ("Imprevistos", "⚠️"),
                ("Comisiones bancarias", "🏦"),
                ("Multas", "🚨"),
                ("Ajustes", "⚖️"),
                ("Varios", "📦"),
            ],
        ),
        (
            "Diezmo",
            [
                ("Diezmo", "🙏"),
                ("Ofrendas", "🕊️"),
                ("Ayudas", "🤝"),
                ("Donaciones", "🎗️"),
                ("Primicias", "🌾"),
            ],
        ),
        (
            "Ahorro",
            [
                ("CDT", "🏦"),
                ("Fondo de emergencia", "🚨"),
                ("Meta", "🎯"),
                ("Inversión", "📈"),
                ("Bolsillo", "👝"),
            ],
        ),
    ]
    for cat_name, subs in default_subcategories:
        cursor.execute(_adapt_sql("SELECT id FROM categories WHERE name = ?"), (cat_name,))
        row = cursor.fetchone()
        if row:
            for sub_name, sub_icon in subs:
                if _is_postgres():
                    cursor.execute(
                        _adapt_sql(
                            "INSERT INTO subcategories (category_id, name, icon) VALUES (?, ?, ?) ON CONFLICT DO NOTHING"
                        ),
                        (row["id"], sub_name, sub_icon),
                    )
                else:
                    cursor.execute(
                        "INSERT OR IGNORE INTO subcategories (category_id, name, icon) VALUES (?, ?, ?)",
                        (row["id"], sub_name, sub_icon),
                    )


def _backup_before_migration(from_version: int) -> str:
    """Snapshot an existing SQLite database before migrating it.

    Kept outside the daily rotation (different prefix), so a migration can
    always be rolled back by restoring this file.
    """
    name = f"pre-migration_v{from_version}-to-v{SCHEMA_VERSION}_{clock.today().isoformat()}.db"
    dest = os.path.join(get_backup_dir(), name)
    if not os.path.exists(dest):
        backup_database(dest)
    return dest


def init_db() -> None:
    """Import legacy data if needed, apply migrations and seeds."""
    if not _is_postgres():
        _import_legacy_db()
    with get_connection() as conn:
        v = _get_version(conn)
        if not _is_postgres() and 0 < v < SCHEMA_VERSION:
            _backup_before_migration(v)
        if _is_postgres() and v == 0:
            # Fresh Postgres: build the final schema directly instead of
            # replaying the SQLite-specific table rebuilds (no legacy data).
            _create_postgres_schema(conn)
            conn.commit()
            _seed_defaults(conn)
            conn.commit()
            _set_version(conn, SCHEMA_VERSION)
            return
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
        if v < 13:
            _migrate_v13_installments(conn)
        if v < 14:
            _migrate_v14_savings_dividends(conn)
        if v < 15:
            _migrate_v15_savings_category(conn)
        if v < 16:
            _migrate_v16_category_roles(conn)
        if v < 17:
            _migrate_v17_drop_ai_tables(conn)
        if v < 18:
            _migrate_v18_loans(conn)
        conn.commit()
        _seed_defaults(conn)
        conn.commit()
