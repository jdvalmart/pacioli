"""Tests for money formatting and parsing."""

from decimal import Decimal

import pytest

from app.money import fmt_cop, parse_amount


class TestFmtCop:
    """Tests for fmt_cop."""

    def test_positive_decimal(self) -> None:
        assert fmt_cop(Decimal("1234.56")) == "$1.235"

    def test_negative_decimal(self) -> None:
        assert fmt_cop(Decimal("-1234.56")) == "-$1.235"

    def test_zero(self) -> None:
        assert fmt_cop(Decimal("0")) == "$0"

    def test_large_number(self) -> None:
        assert fmt_cop(Decimal("1234567.89")) == "$1.234.568"

    def test_int(self) -> None:
        assert fmt_cop(1000) == "$1.000"

    def test_float(self) -> None:
        assert fmt_cop(1234.56) == "$1.235"

    def test_rounding_half_up(self) -> None:
        assert fmt_cop(Decimal("0.5")) == "$1"
        assert fmt_cop(Decimal("1.5")) == "$2"


class TestParseAmount:
    """Tests for parse_amount."""

    def test_simple_integer(self) -> None:
        assert parse_amount("1000") == Decimal("1000.00")

    def test_with_decimals(self) -> None:
        assert parse_amount("1234.56") == Decimal("1234.56")

    def test_colombian_format_millions(self) -> None:
        assert parse_amount("1.500.000") == Decimal("1500000.00")

    def test_colombian_format_with_decimals(self) -> None:
        assert parse_amount("1.500.000,50") == Decimal("1500000.50")

    def test_us_format(self) -> None:
        assert parse_amount("1,500.50") == Decimal("1500.50")

    def test_with_dollar_sign(self) -> None:
        assert parse_amount("$1000") == Decimal("1000.00")

    def test_with_spaces(self) -> None:
        assert parse_amount("  1000  ") == Decimal("1000.00")

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="Ingrese un monto"):
            parse_amount("")

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="no puede ser negativo"):
            parse_amount("-1000")

    def test_invalid_characters_raises(self) -> None:
        with pytest.raises(ValueError, match="inválido"):
            parse_amount("abc")

    def test_colombian_thousands_separator(self) -> None:
        assert parse_amount("1.500") == Decimal("1500.00")

    def test_decimal_separator(self) -> None:
        assert parse_amount("1.50") == Decimal("1.50")

    def test_zero(self) -> None:
        assert parse_amount("0") == Decimal("0.00")

    def test_rounding_to_two_decimals(self) -> None:
        assert parse_amount("1.2345") == Decimal("1.23")
        assert parse_amount("1.235") == Decimal("1235.00")
        assert parse_amount("1,235") == Decimal("1235.00")
        assert parse_amount("1.234,567") == Decimal("1234.57")
