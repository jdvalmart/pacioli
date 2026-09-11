import calendar
import sqlite3
import os
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Tuple, Dict, Any, Union
from dataclasses import dataclass
from contextlib import contextmanager


# ── Rutas (XDG) ──────────────────────────────────────────────
# La BD vive fuera del repo/instalación para sobrevivir actualizaciones
# y funcionar con PyInstaller (un directorio relativo al código se
# resuelve dentro del temporal _MEIPASS y los datos se perderían).

def _default_data_dir() -> str:
    override = os.environ.get('PACIOLI_DATA_DIR')
    if override:
        return override
    base = os.environ.get('XDG_DATA_HOME') or os.path.join(
        os.path.expanduser('~'), '.local', 'share')
    return os.path.join(base, 'pacioli')


# Ubicación histórica (repo/data/budget.db); se importa una sola vez.
LEGACY_DB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'data', 'budget.db'))

DB_PATH = os.path.join(_default_data_dir(), 'pacioli.db')

SCHEMA_VERSION = 2


# ── Dinero: centavos INTEGER en BD, Decimal en el dominio ────

def _to_cents(amount: Union[Decimal, float, int, str]) -> int:
    return int((Decimal(str(amount)) * 100).quantize(
        Decimal('1'), rounding=ROUND_HALF_UP))


def _to_dec(cents: Optional[int]) -> Decimal:
    return (Decimal(cents or 0) / 100).quantize(Decimal('0.01'))


@dataclass
class Category:
    id: Optional[int]
    name: str
    type: str  # 'income' or 'expense'
    color: str
    icon: str


@dataclass
class Subcategory:
    id: Optional[int]
    category_id: int
    name: str
    icon: str


@dataclass
class Transaction:
    id: Optional[int]
    date: date
    amount: Decimal
    category_id: int
    description: str
    is_recurring: bool
    recurring_day: Optional[int]  # Day of month for recurring
    subcategory_id: Optional[int] = None
    subcategory_name: Optional[str] = None
    subcategory_icon: Optional[str] = None
    generated_from: Optional[int] = None  # plantilla recurrente que la generó


@dataclass
class Budget:
    id: Optional[int]
    category_id: int
    month: int  # 1-12
    year: int
    amount: Decimal


@dataclass
class MonthlySummary:
    month: int
    year: int
    total_income: Decimal
    total_expense: Decimal
    balance: Decimal
    by_category: Dict[str, Decimal]


def get_db_path() -> str:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return DB_PATH


def get_backup_dir() -> str:
    d = os.path.join(os.path.dirname(os.path.abspath(get_db_path())), 'backups')
    os.makedirs(d, exist_ok=True)
    return d


@contextmanager
def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode = WAL')
    conn.execute('PRAGMA foreign_keys = ON')
    try:
        yield conn
    finally:
        conn.close()


def _import_legacy_db() -> bool:
    """Copia la BD legacy del repo a la ubicación XDG una sola vez."""
    if os.path.exists(DB_PATH) or not os.path.exists(LEGACY_DB_PATH):
        return False
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    src = sqlite3.connect(LEGACY_DB_PATH)
    try:
        dst = sqlite3.connect(DB_PATH)
        try:
            with dst:
                src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return True


# ── Migraciones ──────────────────────────────────────────────
# Esquema versionado con PRAGMA user_version. Una BD nueva recorre
# el mismo camino que una antigua: v0 → v1 (baseline) → v2 (centavos).

def _user_version(conn) -> int:
    return conn.execute('PRAGMA user_version').fetchone()[0]


def _migrate_v1_baseline(conn):
    """v0 → v1: esquema histórico (idempotente sobre BDs existentes)."""
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            color TEXT DEFAULT '#3B82F6',
            icon TEXT DEFAULT '📁'
        )
    ''')

    cursor.execute('''
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
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
            year INTEGER NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            UNIQUE(category_id, month, year)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subcategories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '📁',
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
            UNIQUE(category_id, name)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL CHECK(role IN ('user', 'ai')),
            message TEXT NOT NULL,
            month INTEGER,
            year INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_learnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            correction TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS desc_learnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            subcategory TEXT,
            ai_description TEXT NOT NULL,
            user_description TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        SELECT COUNT(*) FROM pragma_table_info('transactions') WHERE name = 'subcategory_id'
    ''')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            ALTER TABLE transactions ADD COLUMN subcategory_id INTEGER
            REFERENCES subcategories(id)
        ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_budgets_month_year ON budgets(month, year)')

    cursor.execute('PRAGMA user_version = 1')


def _migrate_v2_cents(conn):
    """v1 → v2: dinero en centavos INTEGER + soporte de recurrencias.

    Reconstruye transactions y budgets (SQLite no permite cambiar el
    tipo de una columna con ALTER), usando ROUND(amount*100) para la
    conversión y verificando integridad referencial al final.
    """
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = OFF')

    cursor.execute('''
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
    ''')
    cursor.execute('''
        INSERT INTO transactions_new
            (id, date, amount_cents, category_id, description,
             is_recurring, recurring_day, subcategory_id)
        SELECT id, date, CAST(ROUND(amount * 100) AS INTEGER), category_id,
               description, is_recurring, recurring_day, subcategory_id
        FROM transactions
    ''')
    cursor.execute('DROP TABLE transactions')
    cursor.execute('ALTER TABLE transactions_new RENAME TO transactions')

    cursor.execute('''
        CREATE TABLE budgets_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL REFERENCES categories(id),
            month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
            year INTEGER NOT NULL,
            amount_cents INTEGER NOT NULL,
            UNIQUE(category_id, month, year)
        )
    ''')
    cursor.execute('''
        INSERT INTO budgets_new (id, category_id, month, year, amount_cents)
        SELECT id, category_id, month, year, CAST(ROUND(amount * 100) AS INTEGER)
        FROM budgets
    ''')
    cursor.execute('DROP TABLE budgets')
    cursor.execute('ALTER TABLE budgets_new RENAME TO budgets')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recurring_materialized (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
            month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
            year INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(template_id, month, year)
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_generated ON transactions(generated_from)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_budgets_month_year ON budgets(month, year)')

    violations = cursor.execute('PRAGMA foreign_key_check').fetchall()
    if violations:
        raise sqlite3.IntegrityError(
            f'Migración a v2: {len(violations)} violaciones de FK: {violations[:5]}')

    cursor.execute('PRAGMA user_version = 2')
    cursor.execute('PRAGMA foreign_keys = ON')


def _seed_defaults(conn):
    """Categorías y subcategorías por defecto (idempotente)."""
    cursor = conn.cursor()

    default_categories = [
        ('Salario', 'income', '#10B981', '💰'),
        ('Freelance', 'income', '#059669', '💻'),
        ('Inversiones', 'income', '#047857', '📈'),
        ('Otros ingresos', 'income', '#065F46', '💵'),
        ('Vivienda', 'expense', '#EF4444', '🏠'),
        ('Alimentación', 'expense', '#F97316', '🍕'),
        ('Transporte', 'expense', '#EAB308', '🚌'),
        ('Servicios', 'expense', '#8B5CF6', '⚡'),
        ('Entretenimiento', 'expense', '#EC4899', '🎮'),
        ('Salud', 'expense', '#14B8A6', '🏥'),
        ('Educación', 'expense', '#6366F1', '📚'),
        ('Compras', 'expense', '#F43F5E', '🛍️'),
        ('Otros gastos', 'expense', '#64748B', '📦'),
    ]

    for name, cat_type, color, icon in default_categories:
        cursor.execute(
            'INSERT OR IGNORE INTO categories (name, type, color, icon) VALUES (?, ?, ?, ?)',
            (name, cat_type, color, icon)
        )

    default_subcategories = [
        ('Servicios', [
            ('Agua', '💧'),
            ('Energía', '⚡'),
            ('Gas', '🔥'),
            ('Internet', '🌐'),
            ('Teléfono', '📱'),
            ('Televisión', '📺'),
        ]),
        ('Alimentación', [
            ('Supermercado', '🛒'),
            ('Restaurantes', '🍽️'),
            ('Domicilios', '🛵'),
        ]),
        ('Transporte', [
            ('Gasolina', '⛽'),
            ('Transporte público', '🚌'),
            ('Estacionamiento', '🅿️'),
            ('Uber/Taxi', '🚕'),
        ]),
        ('Salud', [
            ('Consultas', '🩺'),
            ('Medicamentos', '💊'),
            ('Seguro médico', '🛡️'),
        ]),
        ('Educación', [
            ('Matrícula', '🎓'),
            ('Libros', '📖'),
            ('Cursos', '💻'),
        ]),
        ('Vivienda', [
            ('Arriendo', '🏠'),
            ('Mantenimiento', '🔧'),
            ('Seguro', '🛡️'),
        ]),
    ]
    for cat_name, subs in default_subcategories:
        cursor.execute('SELECT id FROM categories WHERE name = ?', (cat_name,))
        row = cursor.fetchone()
        if row:
            for sub_name, sub_icon in subs:
                cursor.execute(
                    'INSERT OR IGNORE INTO subcategories (category_id, name, icon) VALUES (?, ?, ?)',
                    (row['id'], sub_name, sub_icon)
                )


def init_db():
    """Importa datos legacy si hace falta, aplica migraciones y seeds."""
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


def get_categories(cat_type: Optional[str] = None) -> List[Category]:
    with get_connection() as conn:
        cursor = conn.cursor()
        if cat_type:
            cursor.execute('SELECT * FROM categories WHERE type = ? ORDER BY name', (cat_type,))
        else:
            cursor.execute('SELECT * FROM categories ORDER BY type, name')
        return [Category(**dict(row)) for row in cursor.fetchall()]


def add_category(name: str, cat_type: str, color: str = '#3B82F6', icon: str = '📁') -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO categories (name, type, color, icon) VALUES (?, ?, ?, ?)',
            (name, cat_type, color, icon)
        )
        conn.commit()
        return cursor.lastrowid


def update_category(cat_id: int, name: str, color: str, icon: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE categories SET name = ?, color = ?, icon = ? WHERE id = ?',
            (name, color, icon, cat_id)
        )
        conn.commit()


def delete_category(cat_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM categories WHERE id = ?', (cat_id,))
            conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(
                'No se puede eliminar: la categoría tiene transacciones o presupuestos asociados.'
            )


def get_subcategories(category_id: int) -> List[Subcategory]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM subcategories WHERE category_id = ? ORDER BY name',
            (category_id,)
        )
        return [Subcategory(**dict(row)) for row in cursor.fetchall()]


def get_all_subcategories() -> List[Subcategory]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM subcategories ORDER BY category_id, name')
        return [Subcategory(**dict(row)) for row in cursor.fetchall()]


def add_subcategory(category_id: int, name: str, icon: str = '📁') -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO subcategories (category_id, name, icon) VALUES (?, ?, ?)',
            (category_id, name, icon)
        )
        conn.commit()
        return cursor.lastrowid


def delete_subcategory(sub_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE transactions SET subcategory_id = NULL WHERE subcategory_id = ?', (sub_id,))
        cursor.execute('DELETE FROM subcategories WHERE id = ?', (sub_id,))
        conn.commit()


_TX_KEYS = {f.name for f in Transaction.__dataclass_fields__.values()}


def _row_to_tx(row) -> Transaction:
    d = dict(row)
    d['amount'] = _to_dec(d.pop('amount_cents'))
    return Transaction(**{k: v for k, v in d.items() if k in _TX_KEYS})


def get_transactions(month: int, year: int) -> List[Transaction]:
    with get_connection() as conn:
        cursor = conn.cursor()
        start_date = f'{year}-{month:02d}-01'
        if month == 12:
            end_date = f'{year + 1}-01-01'
        else:
            end_date = f'{year}-{month + 1:02d}-01'
        cursor.execute('''
            SELECT t.*, c.name as category_name, c.type as category_type, c.color, c.icon,
                   s.name as subcategory_name, s.icon as subcategory_icon
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            LEFT JOIN subcategories s ON t.subcategory_id = s.id
            WHERE t.date >= ? AND t.date < ?
            ORDER BY t.date DESC
        ''', (start_date, end_date))
        return [_row_to_tx(row) for row in cursor.fetchall()]


def add_transaction(date_val: date, amount: Union[Decimal, float, int], category_id: int,
                    description: str = '', is_recurring: bool = False,
                    recurring_day: Optional[int] = None,
                    subcategory_id: Optional[int] = None) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (date, amount_cents, category_id, description, is_recurring, recurring_day, subcategory_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (date_val.isoformat(), _to_cents(amount), category_id, description,
              int(is_recurring), recurring_day, subcategory_id))
        conn.commit()
        return cursor.lastrowid


def update_transaction(trans_id: int, date_val: date, amount: Union[Decimal, float, int],
                       category_id: int, description: str,
                       is_recurring: bool = False, recurring_day: Optional[int] = None,
                       subcategory_id: Optional[int] = None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE transactions
            SET date = ?, amount_cents = ?, category_id = ?, description = ?, is_recurring = ?, recurring_day = ?, subcategory_id = ?
            WHERE id = ?
        ''', (date_val.isoformat(), _to_cents(amount), category_id, description,
              int(is_recurring), recurring_day, subcategory_id, trans_id))
        conn.commit()


def delete_transaction(trans_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM transactions WHERE id = ?', (trans_id,))
        conn.commit()


# ── Recurrencias ─────────────────────────────────────────────
# Una transacción con is_recurring=1 y generated_from NULL es una
# "plantilla". Al navegar a un mes posterior, ensure_recurring() crea
# la instancia de ese mes (día ajustado al último día del mes si hace
# falta) y la registra en recurring_materialized para que no se
# duplique jamás, incluso si el usuario borra la instancia.

def ensure_recurring(month: int, year: int) -> int:
    """Materializa las plantillas recurrentes para el mes dado.

    Retorna cuántas transacciones nuevas creó.
    """
    last_day = calendar.monthrange(year, month)[1]
    created = 0
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, date, amount_cents, category_id, description,
                   recurring_day, subcategory_id
            FROM transactions
            WHERE is_recurring = 1 AND generated_from IS NULL
              AND recurring_day IS NOT NULL
        ''')
        templates = cursor.fetchall()
        for t in templates:
            t_year, t_month = int(t['date'][:4]), int(t['date'][5:7])
            if (year, month) <= (t_year, t_month):
                continue
            cursor.execute(
                'SELECT 1 FROM recurring_materialized WHERE template_id = ? AND month = ? AND year = ?',
                (t['id'], month, year)
            )
            if cursor.fetchone():
                continue
            day = min(t['recurring_day'], last_day)
            cursor.execute('''
                INSERT INTO transactions
                    (date, amount_cents, category_id, description,
                     is_recurring, recurring_day, subcategory_id, generated_from)
                VALUES (?, ?, ?, ?, 0, NULL, ?, ?)
            ''', (f'{year:04d}-{month:02d}-{day:02d}', t['amount_cents'],
                  t['category_id'], t['description'], t['subcategory_id'], t['id']))
            cursor.execute(
                'INSERT INTO recurring_materialized (template_id, month, year) VALUES (?, ?, ?)',
                (t['id'], month, year)
            )
            created += 1
        conn.commit()
    return created


def get_budgets(month: int, year: int) -> List[Budget]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, category_id, month, year, amount_cents FROM budgets WHERE month = ? AND year = ?',
            (month, year)
        )
        return [Budget(id=r['id'], category_id=r['category_id'], month=r['month'],
                       year=r['year'], amount=_to_dec(r['amount_cents']))
                for r in cursor.fetchall()]


def set_budget(category_id: int, month: int, year: int, amount: Union[Decimal, float, int]):
    cents = _to_cents(amount)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO budgets (category_id, month, year, amount_cents)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(category_id, month, year) DO UPDATE SET amount_cents = excluded.amount_cents
        ''', (category_id, month, year, cents))
        conn.commit()


def delete_budget(category_id: int, month: int, year: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM budgets WHERE category_id = ? AND month = ? AND year = ?',
                       (category_id, month, year))
        conn.commit()


def get_monthly_summary(month: int, year: int) -> MonthlySummary:
    with get_connection() as conn:
        cursor = conn.cursor()
        start_date = f'{year}-{month:02d}-01'
        if month == 12:
            end_date = f'{year + 1}-01-01'
        else:
            end_date = f'{year}-{month + 1:02d}-01'

        cursor.execute('''
            SELECT c.type, c.name, SUM(t.amount_cents) as total_cents
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.date >= ? AND t.date < ?
            GROUP BY c.type, c.name
        ''', (start_date, end_date))

        by_category: Dict[str, Decimal] = {}
        total_income = Decimal('0.00')
        total_expense = Decimal('0.00')
        for row in cursor.fetchall():
            total = _to_dec(row['total_cents'])
            by_category[row['name']] = total
            if row['type'] == 'income':
                total_income += total
            else:
                total_expense += total

        return MonthlySummary(
            month=month,
            year=year,
            total_income=total_income,
            total_expense=total_expense,
            balance=total_income - total_expense,
            by_category=by_category
        )


def get_monthly_summaries(year: int) -> List[MonthlySummary]:
    return [get_monthly_summary(m, year) for m in range(1, 13)]


def get_category_spending(month: int, year: int, cat_type: str = 'expense') -> List[Tuple[str, Decimal, str, str]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        start_date = f'{year}-{month:02d}-01'
        if month == 12:
            end_date = f'{year + 1}-01-01'
        else:
            end_date = f'{year}-{month + 1:02d}-01'
        cursor.execute('''
            SELECT c.name, SUM(t.amount_cents) as total_cents, c.color, c.icon
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE c.type = ? AND t.date >= ? AND t.date < ?
            GROUP BY c.id
            ORDER BY total_cents DESC
        ''', (cat_type, start_date, end_date))
        return [(row['name'], _to_dec(row['total_cents']), row['color'], row['icon'])
                for row in cursor.fetchall()]


def get_budget_vs_actual(month: int, year: int) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        start_date = f'{year}-{month:02d}-01'
        if month == 12:
            end_date = f'{year + 1}-01-01'
        else:
            end_date = f'{year}-{month + 1:02d}-01'

        cursor.execute('''
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
        ''', (month, year, start_date, end_date))

        result = []
        for row in cursor.fetchall():
            budget = _to_dec(row['budget_cents'])
            actual = _to_dec(row['actual_cents'])
            result.append({
                'category_id': row['id'],
                'name': row['name'],
                'color': row['color'],
                'icon': row['icon'],
                'budget': budget,
                'actual': actual,
                'remaining': budget - actual if budget > 0 else -actual,
                'percent': float(actual / budget * 100) if budget > 0 else 0.0
            })
        return result


# ── Chat History ─────────────────────────────────────────────

def save_chat_message(role: str, message: str, month: int, year: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO chat_history (role, message, month, year) VALUES (?, ?, ?, ?)',
            (role, message, month, year)
        )
        conn.commit()


def get_chat_history(month: int, year: int, limit: int = 50) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT role, message, created_at FROM chat_history '
            'WHERE month = ? AND year = ? ORDER BY created_at DESC LIMIT ?',
            (month, year, limit)
        )
        return [dict(row) for row in reversed(cursor.fetchall())]


def clear_chat_history(month: int, year: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM chat_history WHERE month = ? AND year = ?', (month, year))
        conn.commit()


# ── AI Learnings ─────────────────────────────────────────────

def save_learning(topic: str, correction: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO ai_learnings (topic, correction) VALUES (?, ?)',
            (topic, correction)
        )
        conn.commit()


def get_learnings(limit: int = 20) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT topic, correction, created_at FROM ai_learnings '
            'ORDER BY created_at DESC LIMIT ?',
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_recent_chat_context(month: int, year: int, turns: int = 10) -> str:
    history = get_chat_history(month, year, limit=turns)
    if not history:
        return ""
    lines = []
    for h in history:
        tag = "Usuario" if h['role'] == 'user' else "IA"
        lines.append(f"{tag}: {h['message']}")
    return "\n".join(lines)


def get_learnings_context() -> str:
    learnings = get_learnings(limit=15)
    if not learnings:
        return ""
    lines = ["Aprendizajes del usuario (correcciones previas):"]
    for l in learnings:
        lines.append(f"- [{l['topic']}] {l['correction']}")
    return "\n".join(lines)


# ── Description Learnings ────────────────────────────────────

def save_desc_learning(category: str, subcategory: str, ai_desc: str, user_desc: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO desc_learnings (category, subcategory, ai_description, user_description) '
            'VALUES (?, ?, ?, ?)',
            (category, subcategory or '', ai_desc, user_desc)
        )
        conn.commit()


def get_desc_learnings(category: str, limit: int = 5) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT ai_description, user_description FROM desc_learnings '
            'WHERE category = ? ORDER BY created_at DESC LIMIT ?',
            (category, limit)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_desc_learnings_context(category: str) -> str:
    learnings = get_desc_learnings(category, limit=5)
    if not learnings:
        return ""
    lines = [f"Correciones previas de descripciones en '{category}':"]
    for l in learnings:
        lines.append(f'  IA dijo: "{l["ai_description"]}" → Usuario corrigió: "{l["user_description"]}"')
    return "\n".join(lines)


# ── Export CSV ───────────────────────────────────────────────

def export_transactions_csv(month: int, year: int, filepath: str):
    """Exporta transacciones del mes a CSV."""
    import csv
    txns = get_transactions(month, year)
    cat_map = {c.id: c for c in get_categories()}
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Fecha', 'Categoría', 'Subcategoría', 'Tipo', 'Monto', 'Descripción', 'Recurrente'])
        for t in txns:
            cat = cat_map.get(t.category_id)
            cat_name = cat.name if cat else '—'
            cat_type = cat.type if cat else '—'
            sub_name = t.subcategory_name or ''
            writer.writerow([
                t.date, cat_name, sub_name, cat_type,
                str(t.amount), t.description or '',
                'Sí' if (t.is_recurring or t.generated_from) else 'No'
            ])


# ── Auto Backup ─────────────────────────────────────────────

BACKUP_KEEP = 10


def backup_database(dest_path: str):
    """Copia en caliente segura usando la API de backup de sqlite3.

    A diferencia de shutil.copy, es consistente incluso con WAL activo
    o escrituras concurrentes.
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


def auto_backup(keep: int = BACKUP_KEEP) -> Optional[str]:
    """Backup diario automático con rotación. Retorna la ruta creada o None."""
    if not os.path.exists(get_db_path()):
        return None
    today = date.today()
    dest = os.path.join(get_backup_dir(), f'pacioli_{today.isoformat()}.db')
    created = None
    if not os.path.exists(dest):
        backup_database(dest)
        created = dest
    if keep > 0:
        backups = sorted(
            f for f in os.listdir(get_backup_dir())
            if f.startswith('pacioli_') and f.endswith('.db')
        )
        for old in backups[:max(0, len(backups) - keep)]:
            try:
                os.remove(os.path.join(get_backup_dir(), old))
            except OSError:
                pass
    return created