"""Funciones de formato y parseo de dinero.

Maneja la conversión entre representaciones textuales (formato colombiano
y neutro) y valores Decimal para precisión financiera.
"""

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def fmt_cop(v) -> str:
    """Formatea cualquier número (Decimal/int/float) como $1.234.567 COP.

    Args:
        v: Valor numérico (Decimal, int, float o str convertible)

    Returns:
        String formateado con separador de miles (punto) y signo negativo
        si aplica. Ejemplo: "-$1.234.568"
    """
    d = v if isinstance(v, Decimal) else Decimal(str(v))
    sign = "-" if d < 0 else ""
    units = abs(d).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return f"{sign}${units:,}".replace(",", ".")


def _resolve_single_separator(s: str, sep: str) -> str:
    """Resuelve ambigüedad cuando hay un solo separador (punto o coma).

    Regla: si hay exactamente 3 dígitos después del separador y la parte
    anterior es un número > 0, se interpreta como separador de miles.
    Si no, se interpreta como separador decimal.

    Args:
        s: String con un solo tipo de separador
        sep: El separador ('.' o ',')

    Returns:
        String normalizado con punto como separador decimal
    """
    parts = s.split(sep)
    if len(parts) > 2:
        return s.replace(sep, '')  # 1.234.567 → miles
    if len(parts) == 2 and len(parts[1]) == 3 and parts[0].isdigit() and parts[0] != '0':
        return s.replace(sep, '')  # 1.500 → miles (convención CO)
    return s.replace(sep, '.')     # decimal


def parse_amount(text: str) -> Decimal:
    """Convierte texto del usuario a Decimal (2 decimales máx.).

    Acepta múltiples formatos:
    - '1500000' → 1500000
    - '1.500.000' → 1500000 (puntos como miles)
    - '1500000,50' → 1500000.50 (coma como decimal)
    - '1.500.000,50' → 1500000.50 (formato CO)
    - '1,500.50' → 1500.50 (formato US)
    - '$ 2.000' → 2000 (símbolo $ ignorado)
    - '1.50' → 1.50 (2 dígitos = decimal)
    - '1.500' → 1500 (3 dígitos = miles, convención CO)

    Args:
        text: Texto a parsear

    Returns:
        Decimal con 2 decimales de precisión

    Raises:
        ValueError: Si el texto es inválido, vacío o negativo
    """
    s = (text or "").strip().replace("$", "").replace(" ", "").replace("\u00a0", "")
    if not s:
        raise ValueError("Ingrese un monto")
    if s.startswith('-'):
        raise ValueError("El monto no puede ser negativo")
    s = s.lstrip('+')
    if not re.fullmatch(r'[0-9.,]+', s):
        raise ValueError(f"Monto inválido: '{text.strip()}'. Ingrese un número")
    if '.' in s and ',' in s:
        if s.rfind('.') > s.rfind(','):
            s = s.replace(',', '')                     # 1,500.50
        else:
            s = s.replace('.', '').replace(',', '.')   # 1.500,50
    elif ',' in s:
        s = _resolve_single_separator(s, ',')
    elif '.' in s:
        s = _resolve_single_separator(s, '.')
    try:
        d = Decimal(s)
    except InvalidOperation:
        raise ValueError(f"Monto inválido: '{text.strip()}'. Ingrese un número")
    return d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
