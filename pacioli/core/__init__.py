"""Módulo core: lógica de negocio y modelos de dominio.

Contiene las entidades fundamentales del sistema (modelos) y las funciones
de formato/parseo de dinero que no dependen de infraestructura externa.
"""

from .models import Budget, Category, MonthlySummary, Subcategory, Transaction
from .money import fmt_cop, parse_amount

__all__ = [
    'Budget',
    'Category',
    'MonthlySummary',
    'Subcategory',
    'Transaction',
    'fmt_cop',
    'parse_amount',
]
