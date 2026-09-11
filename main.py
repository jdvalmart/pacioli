#!/usr/bin/env python3
"""Pacioli - Aplicación de escritorio para gestión de finanzas personales."""

import sys
import os

# Agregar el directorio actual al path para imports
base = os.path.dirname(os.path.abspath(__file__))
if base not in sys.path:
    sys.path.insert(0, base)

from pacioli.ui.app import main


if __name__ == '__main__':
    main()
