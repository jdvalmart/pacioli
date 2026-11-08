"""Categories and subcategories."""

from app.db.connection import _ddl, _insert_get_id, get_connection
from app.db.models import Category, Subcategory
from app.errors import IntegrityViolation


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
        sql = _ddl("INSERT INTO categories (name, type, color, icon) VALUES (?, ?, ?, ?)")
        new_id = _insert_get_id(cursor, sql, (name, cat_type, color, icon))
        conn.commit()
        return new_id


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
    """Delete a category.

    Refuses system categories (those with a ``role``, such as savings) and
    categories still referenced by transactions or budgets.
    """
    try:
        with get_connection() as conn:
            row = conn.execute("SELECT role FROM categories WHERE id = ?", (cat_id,)).fetchone()
            if row is not None and row["role"] is not None:
                raise ValueError(
                    "No se puede eliminar: es la categoría de sistema donde se agrupan tus "
                    "ahorros. Puedes cambiarle el nombre, el color o el ícono."
                )
            conn.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
            conn.commit()
    except IntegrityViolation:
        raise ValueError(
            "No se puede eliminar: la categoría tiene transacciones o presupuestos asociados."
        ) from None


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
        sql = _ddl("INSERT INTO subcategories (category_id, name, icon) VALUES (?, ?, ?)")
        new_id = _insert_get_id(cursor, sql, (category_id, name, icon))
        conn.commit()
        return new_id


def delete_subcategory(sub_id: int) -> None:
    """Delete a subcategory, detaching it from its transactions."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE transactions SET subcategory_id = NULL WHERE subcategory_id = ?", (sub_id,)
        )
        cursor.execute("DELETE FROM subcategories WHERE id = ?", (sub_id,))
        conn.commit()
