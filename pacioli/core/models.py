"""Modelos de dominio de Pacioli.

Dataclasses que representan las entidades del sistema financiero:
categorías, transacciones, presupuestos y resúmenes mensuales.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional


@dataclass
class Category:
    """Categoría de transacción (ingreso o gasto)."""

    id: Optional[int]
    name: str
    type: str  # 'income' or 'expense'
    color: str
    icon: str


@dataclass
class Subcategory:
    """Subcategoría dentro de una categoría."""

    id: Optional[int]
    category_id: int
    name: str
    icon: str


@dataclass
class Transaction:
    """Transacción financiera individual."""

    id: Optional[int]
    date: str  # ISO format: YYYY-MM-DD
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
    """Presupuesto mensual para una categoría."""

    id: Optional[int]
    category_id: int
    month: int  # 1-12
    year: int
    amount: Decimal


@dataclass
class MonthlySummary:
    """Resumen consolidado de un mes."""

    month: int
    year: int
    total_income: Decimal
    total_expense: Decimal
    balance: Decimal
    by_category: Dict[str, Decimal]
