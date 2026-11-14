"""Unit tests for the pure loan rules."""

from datetime import date

from app.domain.loans import Payment, accrued, installments_left, loan_status


def test_interest_accrues_daily_at_the_effective_annual_rate() -> None:
    # A full year at 24% EA on 1.000.000 is exactly 240.000.
    assert accrued(100_000_000, 2400, 365) == 24_000_000
    assert accrued(100_000_000, None, 365) == 0
    assert accrued(100_000_000, 2400, 0) == 0


def test_without_rate_the_balance_is_start_minus_payments() -> None:
    status = loan_status(
        890_000_000, date(2026, 11, 14), None, 30_000_000,
        [Payment(date(2026, 12, 5), 30_000_000)], date(2026, 12, 20),
    )  # fmt: skip
    assert status.balance_cents == 860_000_000
    assert status.remaining_installments == 29  # 8.600.000 / 300.000 rounded up


def test_payments_cover_interest_first() -> None:
    start = date(2026, 1, 1)
    status = loan_status(
        100_000_000,
        start,
        2400,
        10_000_000,
        [Payment(date(2027, 1, 1), 34_000_000)],
        date(2027, 1, 1),
    )
    assert status.interest_cents == 24_000_000
    assert status.balance_cents == 100_000_000 + 24_000_000 - 34_000_000


def test_payments_before_the_starting_balance_are_ignored() -> None:
    status = loan_status(
        50_000_000, date(2026, 11, 14), None, 10_000_000,
        [Payment(date(2026, 11, 1), 10_000_000)], date(2026, 11, 30),
    )  # fmt: skip
    assert status.balance_cents == 50_000_000


def test_payoff_projection_matches_the_annuity_formula() -> None:
    # 8.900.000 at 24% EA paying 300.000 -> 43 installments; 700.000 -> 15.
    assert installments_left(890_000_000, 30_000_000, 2400) == 43
    assert installments_left(890_000_000, 70_000_000, 2400) == 15
    # An installment that does not cover the interest never ends.
    assert installments_left(890_000_000, 1_000_000, 2400) is None


def test_payoff_date_is_the_month_of_the_last_installment() -> None:
    status = loan_status(90_000_000, date(2026, 12, 1), None, 30_000_000, [], date(2026, 12, 1))
    assert status.remaining_installments == 3
    assert status.payoff == date(2027, 2, 1)
