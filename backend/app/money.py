"""Money formatting and parsing helpers.

Converts between textual representations (Colombian and neutral
formats) and Decimal values for financial precision.
"""

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def fmt_cop(v: Decimal | int | float | str) -> str:
    """Format any number (Decimal/int/float) as $1.234.567 COP.

    Args:
        v: Numeric value (Decimal, int, float or convertible str).

    Returns:
        String formatted with thousands separator (dot) and a leading
        minus sign when negative. Example: "-$1.234.568".
    """
    d = v if isinstance(v, Decimal) else Decimal(str(v))
    sign = "-" if d < 0 else ""
    units = abs(d).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{sign}${units:,}".replace(",", ".")


def _resolve_single_separator(s: str, sep: str) -> str:
    """Resolve ambiguity when a single separator (dot or comma) appears.

    Rule: exactly 3 digits after the separator and a non-zero integer
    part means thousands separator; otherwise it is a decimal separator.

    Args:
        s: String with a single separator type.
        sep: The separator ('.' or ',').

    Returns:
        Normalized string with a dot as decimal separator.
    """
    parts = s.split(sep)
    if len(parts) > 2:
        return s.replace(sep, "")  # 1.234.567 -> thousands
    if len(parts) == 2 and len(parts[1]) == 3 and parts[0].isdigit() and parts[0] != "0":
        return s.replace(sep, "")  # 1.500 -> thousands (CO convention)
    return s.replace(sep, ".")  # decimal


def parse_amount(text: str) -> Decimal:
    """Convert user input to Decimal (max 2 decimal places).

    Accepts multiple formats:
    - '1500000' -> 1500000
    - '1.500.000' -> 1500000 (dots as thousands)
    - '1500000,50' -> 1500000.50 (comma as decimal)
    - '1.500.000,50' -> 1500000.50 (CO format)
    - '1,500.50' -> 1500.50 (US format)
    - '$ 2.000' -> 2000 ($ sign ignored)
    - '1.50' -> 1.50 (2 digits = decimal)
    - '1.500' -> 1500 (3 digits = thousands, CO convention)

    Args:
        text: Text to parse.

    Returns:
        Decimal quantized to 2 decimal places.

    Raises:
        ValueError: If the text is invalid, empty or negative.
    """
    s = (text or "").strip().replace("$", "").replace(" ", "").replace("\u00a0", "")
    if not s:
        raise ValueError("Ingrese un monto")
    if s.startswith("-"):
        raise ValueError("El monto no puede ser negativo")
    s = s.lstrip("+")
    if not re.fullmatch(r"[0-9.,]+", s):
        raise ValueError(f"Monto inválido: '{text.strip()}'. Ingrese un número")
    if "." in s and "," in s:
        if s.rfind(".") > s.rfind(","):
            s = s.replace(",", "")  # 1,500.50
        else:
            s = s.replace(".", "").replace(",", ".")  # 1.500,50
    elif "," in s:
        s = _resolve_single_separator(s, ",")
    elif "." in s:
        s = _resolve_single_separator(s, ".")
    try:
        d = Decimal(s)
    except InvalidOperation:
        raise ValueError(f"Monto inválido: '{text.strip()}'. Ingrese un número") from None
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
