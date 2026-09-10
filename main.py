#!/usr/bin/env python3
"""Pacioli - Aplicación de escritorio para gestión de finanzas personales."""
import sys
import os

base = os.path.dirname(os.path.abspath(sys.argv[0]))
src = os.path.join(base, 'src')
if os.path.isdir(src) and src not in sys.path:
    sys.path.insert(0, src)

from app import main


if __name__ == '__main__':
    main()
