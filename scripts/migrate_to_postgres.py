#!/usr/bin/env python3
"""Migrate the local SQLite DB to the Postgres instance in DATABASE_URL.

Usage:
  DATABASE_URL=postgresql://pacioli:pacioli@localhost:5433/pacioli python scripts/migrate_to_postgres.py
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import psycopg
from psycopg.rows import dict_row


SRC = os.path.expanduser("~/.local/share/pacioli/pacioli.db")
DST_URL = os.getenv("DATABASE_URL")

if not DST_URL or not DST_URL.startswith("postgres"):
    print("Set DATABASE_URL, e.g.:", file=sys.stderr)
    print(
        "  DATABASE_URL=postgresql://pacioli:pacioli@localhost:5433/pacioli"
        " python scripts/migrate_to_postgres.py",
        file=sys.stderr,
    )
    sys.exit(1)

if not os.path.exists(SRC):
    print(f"SQLite DB not found at {SRC}", file=sys.stderr)
    sys.exit(1)

# Ensure the Postgres schema exists (run the app's migrations once)
print("→ Inicializando esquema en Postgres...")
from app.database import init_db  # noqa: E402

init_db()

src = sqlite3.connect(SRC)
src.row_factory = sqlite3.Row

dst = psycopg.connect(DST_URL, row_factory=dict_row)

# Tables in dependency order (parents first)
TABLES = [
    "categories",
    "accounts",
    "credit_cards",
    "savings",
    "subcategories",
    "transactions",
    "budgets",
    "monthly_plans",
    "recurring_materialized",
    "pacioli_schema_version",
]

# Wipe Postgres tables first (keep schema)
with dst.cursor() as cur:
    cur.execute(
        "TRUNCATE transactions, recurring_materialized, budgets, monthly_plans,"
        " savings, credit_cards, subcategories, categories RESTART IDENTITY CASCADE"
    )
    try:
        cur.execute("DELETE FROM pacioli_schema_version")
    except Exception:
        pass
dst.commit()

for table in TABLES:
    try:
        rows = list(src.execute(f"SELECT * FROM {table}"))
    except sqlite3.OperationalError as e:
        print(f"→ {table}: no existe en SQLite ({e}), se omite")
        continue
    if not rows:
        print(f"→ {table}: 0 filas")
        continue
    cols = [c[0] for c in src.execute(f"SELECT * FROM {table} LIMIT 0").description]
    placeholders = ", ".join(["%s"] * len(cols))
    col_list = ", ".join(cols)
    print(f"→ {table}: {len(rows)} filas → {col_list}")
    with dst.cursor() as cur:
        for r in rows:
            vals = [r[c] for c in cols]
            cur.execute(
                f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING",
                vals,
            )
    dst.commit()
    # Re-sync the SERIAL sequence after explicit-id inserts
    with dst.cursor() as cur:
        cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), (SELECT MAX(id) FROM {table}))")
    dst.commit()

# Copy the SQLite user_version into Postgres
try:
    v = src.execute("PRAGMA user_version").fetchone()[0]
    with dst.cursor() as cur:
        cur.execute(
            "INSERT INTO pacioli_schema_version (id, version) VALUES (1, %s) "
            "ON CONFLICT (id) DO UPDATE SET version=%s",
            (v, v),
        )
    dst.commit()
    print(f"→ versión del esquema: {v}")
except Exception as e:
    print(f"versión no copiada: {e}")

src.close()
dst.close()
print("✓ Migración completa. Iniciá la app con DATABASE_URL y abrí Postgres en VS Code.")
