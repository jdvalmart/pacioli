"""Tests para funciones de formato y parseo de dinero."""

import pytest
from decimal import Decimal
from pacioli.core.money import fmt_cop, parse_amount


class TestFmtCop:
    """Tests para fmt_cop."""

    def test_positive_decimal(self):
        assert fmt_cop(Decimal("1234.56")) == "$1.235"

    def test_negative_decimal(self):
        assert fmt_cop(Decimal("-1234.56")) == "-$1.235"

    def test_zero(self):
        assert fmt_cop(Decimal("0")) == "$0"

    def test_large_number(self):
        assert fmt_cop(Decimal("1234567.89")) == "$1.234.568"

    def test_int(self):
        assert fmt_cop(1000) == "$1.000"

    def test_float(self):
        assert fmt_cop(1234.56) == "$1.235"

    def test_rounding_half_up(self):
        # 0.5 debe redondear hacia arriba
        assert fmt_cop(Decimal("0.5")) == "$1"
        assert fmt_cop(Decimal("1.5")) == "$2"


class TestParseAmount:
    """Tests para parse_amount."""

    def test_simple_integer(self):
        assert parse_amount("1000") == Decimal("1000.00")

    def test_with_decimals(self):
        assert parse_amount("1234.56") == Decimal("1234.56")

    def test_colombian_format_millions(self):
        # 1.500.000 en formato colombiano = 1500000
        assert parse_amount("1.500.000") == Decimal("1500000.00")

    def test_colombian_format_with_decimals(self):
        # 1.500.000,50 en formato colombiano = 1500000.50
        assert parse_amount("1.500.000,50") == Decimal("1500000.50")

    def test_us_format(self):
        # 1,500.50 en formato US = 1500.50
        assert parse_amount("1,500.50") == Decimal("1500.50")

    def test_with_dollar_sign(self):
        assert parse_amount("$1000") == Decimal("1000.00")

    def test_with_spaces(self):
        assert parse_amount("  1000  ") == Decimal("1000.00")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="Ingrese un monto"):
            parse_amount("")

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="no puede ser negativo"):
            parse_amount("-1000")

    def test_invalid_characters_raises(self):
        with pytest.raises(ValueError, match="inválido"):
            parse_amount("abc")

    def test_colombian_thousands_separator(self):
        # 1.500 con 3 dígitos = miles (convención CO)
        assert parse_amount("1.500") == Decimal("1500.00")

    def test_decimal_separator(self):
        # 1.50 con 2 dígitos = decimal
        assert parse_amount("1.50") == Decimal("1.50")

    def test_zero(self):
        assert parse_amount("0") == Decimal("0.00")

    def test_rounding_to_two_decimals(self):
        # Más de 2 decimales se redondean
        assert parse_amount("1.2345") == Decimal("1.23")
        # 1.235 en formato colombiano = 1235 (3 dígitos = miles)
        assert parse_amount("1.235") == Decimal("1235.00")
        # Para probar redondeo decimal, usar formato con coma decimal
        assert parse_amount("1,235") == Decimal("1235.00")  # también miles
        # Formato mixto: punto miles, coma decimal
        assert parse_amount("1.234,567") == Decimal("1234.57")  # round half up
