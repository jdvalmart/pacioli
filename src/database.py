import sqlite3
import os
from datetime import date, datetime
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass
from contextlib import contextmanager


DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'budget.db')


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
    amount: float
    category_id: int
    description: str
    is_recurring: bool
    recurring_day: Optional[int]  # Day of month for recurring
    subcategory_id: Optional[int] = None
    subcategory_name: Optional[str] = None
    subcategory_icon: Optional[str] = None


@dataclass
class Budget:
    id: Optional[int]
    category_id: int
    month: int  # 1-12
    year: int
    amount: float


@dataclass
class MonthlySummary:
    month: int
    year: int
    total_income: float
    total_expense: float
    balance: float
    by_category: Dict[str, float]


def get_db_path() -> str:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return DB_PATH


@contextmanager
def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
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

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_budgets_month_year ON budgets(month, year)
        ''')

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
        cursor.execute('DELETE FROM categories WHERE id = ?', (cat_id,))
        conn.commit()


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


def get_all_transactions() -> List[Transaction]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT t.*, c.name as category_name, c.type as category_type, c.color, c.icon,
                   s.name as subcategory_name, s.icon as subcategory_icon
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            LEFT JOIN subcategories s ON t.subcategory_id = s.id
            ORDER BY t.date DESC
        ''')
        return [_row_to_tx(row) for row in cursor.fetchall()]


def add_transaction(date_val: date, amount: float, category_id: int,
                    description: str = '', is_recurring: bool = False,
                    recurring_day: Optional[int] = None,
                    subcategory_id: Optional[int] = None) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (date, amount, category_id, description, is_recurring, recurring_day, subcategory_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (date_val.isoformat(), amount, category_id, description, int(is_recurring), recurring_day, subcategory_id))
        conn.commit()
        return cursor.lastrowid


def update_transaction(trans_id: int, date_val: date, amount: float,
                       category_id: int, description: str,
                       is_recurring: bool = False, recurring_day: Optional[int] = None,
                       subcategory_id: Optional[int] = None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE transactions
            SET date = ?, amount = ?, category_id = ?, description = ?, is_recurring = ?, recurring_day = ?, subcategory_id = ?
            WHERE id = ?
        ''', (date_val.isoformat(), amount, category_id, description, int(is_recurring), recurring_day, subcategory_id, trans_id))
        conn.commit()


def delete_transaction(trans_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM transactions WHERE id = ?', (trans_id,))
        conn.commit()


def get_budgets(month: int, year: int) -> List[Budget]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, c.name as category_name, c.color, c.icon
            FROM budgets b
            JOIN categories c ON b.category_id = c.id
            WHERE b.month = ? AND b.year = ?
        ''', (month, year))
        return [Budget(**dict(row)) for row in cursor.fetchall()]


def set_budget(category_id: int, month: int, year: int, amount: float):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO budgets (category_id, month, year, amount)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(category_id, month, year) DO UPDATE SET amount = excluded.amount
        ''', (category_id, month, year, amount))
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
            SELECT c.type, c.name, SUM(t.amount) as total
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.date >= ? AND t.date < ?
            GROUP BY c.type, c.name
        ''', (start_date, end_date))

        by_category = {}
        total_income = 0.0
        total_expense = 0.0
        for row in cursor.fetchall():
            by_category[row['name']] = row['total']
            if row['type'] == 'income':
                total_income += row['total']
            else:
                total_expense += row['total']

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


def get_available_months() -> List[Tuple[int, int]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT strftime('%Y', date) as year, strftime('%m', date) as month
            FROM transactions
            ORDER BY year DESC, month DESC
        ''')
        return [(int(row['month']), int(row['year'])) for row in cursor.fetchall()]


def get_category_spending(month: int, year: int, cat_type: str = 'expense') -> List[Tuple[str, float, str, str]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        start_date = f'{year}-{month:02d}-01'
        if month == 12:
            end_date = f'{year + 1}-01-01'
        else:
            end_date = f'{year}-{month + 1:02d}-01'
        cursor.execute('''
            SELECT c.name, SUM(t.amount) as total, c.color, c.icon
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE c.type = ? AND t.date >= ? AND t.date < ?
            GROUP BY c.id
            ORDER BY total DESC
        ''', (cat_type, start_date, end_date))
        return [(row['name'], row['total'], row['color'], row['icon']) for row in cursor.fetchall()]


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
                   COALESCE(b.amount, 0) as budget,
                   COALESCE(SUM(t.amount), 0) as actual
            FROM categories c
            LEFT JOIN budgets b ON c.id = b.category_id AND b.month = ? AND b.year = ?
            LEFT JOIN transactions t ON c.id = t.category_id AND t.date >= ? AND t.date < ?
            WHERE c.type = 'expense'
            GROUP BY c.id
            HAVING budget > 0 OR actual > 0
            ORDER BY c.name
        ''', (month, year, start_date, end_date))

        result = []
        for row in cursor.fetchall():
            budget = row['budget']
            actual = row['actual']
            result.append({
                'category_id': row['id'],
                'name': row['name'],
                'color': row['color'],
                'icon': row['icon'],
                'budget': budget,
                'actual': actual,
                'remaining': budget - actual if budget > 0 else -actual,
                'percent': (actual / budget * 100) if budget > 0 else 0
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