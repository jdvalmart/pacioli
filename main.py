#!/usr/bin/env python3
"""Presupuesto Mensual - Aplicación de escritorio para gestión de finanzas personales."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from src.database import init_db
from src.app import BudgetApp


def main():
    init_db()
    app = BudgetApp()
    app.mainloop()


if __name__ == '__main__':
    main()
