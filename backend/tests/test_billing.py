"""Unit tests for the pure credit card billing rules."""

from datetime import date

from app.domain.billing import (
    Card,
    Purchase,
    card_status,
    cutoff_of,
    cycle_of,
    financed_cents,
    installment_in_month,
    payment_date_of,
    schedule,
)

CARD = Card(cutoff_day=10, payment_day=25)


class TestCycles:
    def test_purchase_on_cutoff_day_closes_that_day(self) -> None:
        assert cutoff_of(CARD, cycle_of(CARD, date(2026, 9, 10))) == date(2026, 9, 10)

    def test_purchase_after_cutoff_goes_to_next_cycle(self) -> None:
        assert cutoff_of(CARD, cycle_of(CARD, date(2026, 9, 11))) == date(2026, 10, 10)

    def test_cutoff_31_is_clamped_in_february(self) -> None:
        card = Card(cutoff_day=31, payment_day=15)
        assert cutoff_of(card, cycle_of(card, date(2026, 2, 20))) == date(2026, 2, 28)

    def test_payment_before_cutoff_day_falls_next_month(self) -> None:
        card = Card(cutoff_day=25, payment_day=10)
        assert payment_date_of(card, cycle_of(card, date(2026, 9, 1))) == date(2026, 10, 10)

    def test_year_rollover(self) -> None:
        cycle = cycle_of(CARD, date(2026, 12, 20))
        assert cutoff_of(CARD, cycle) == date(2027, 1, 10)
        assert payment_date_of(CARD, cycle) == date(2027, 1, 25)


class TestAmounts:
    def test_single_installment_ignores_interest(self) -> None:
        assert financed_cents(Purchase(date(2026, 9, 5), 100_000, 1, 2_000)) == 100_000

    def test_interest_rounds_half_up_to_the_cent(self) -> None:
        # 333 cents * 1.015 = 337.995 -> 338
        assert financed_cents(Purchase(date(2026, 9, 5), 333, 3, 150)) == 338

    def test_installments_add_up_exactly_with_leftover_first(self) -> None:
        items = schedule(CARD, Purchase(date(2026, 9, 5), 10_000, 3))
        assert [i.cents for i in items] == [3_334, 3_333, 3_333]
        assert sum(i.cents for i in items) == 10_000

    def test_schedule_months_follow_payment_dates(self) -> None:
        items = schedule(CARD, Purchase(date(2026, 9, 5), 300_00, 3, 1_200))
        assert [(i.number, i.year, i.month) for i in items] == [
            (1, 2026, 9),
            (2, 2026, 10),
            (3, 2026, 11),
        ]
        assert sum(i.cents for i in items) == 33_600  # 300.00 + 12%

    def test_installment_in_month(self) -> None:
        purchase = Purchase(date(2026, 9, 5), 30_000, 3)
        item = installment_in_month(CARD, purchase, 2026, 10)
        assert item is not None and (item.number, item.cents) == (2, 10_000)
        assert installment_in_month(CARD, purchase, 2026, 12) is None


class TestCardStatus:
    PURCHASE = Purchase(date(2026, 9, 5), 300_000, 3)  # 100k per cycle: Sep, Oct, Nov

    def test_unpaid_previous_statement_is_due(self) -> None:
        """Paid September; October's statement (closed Oct 10) is still owed."""
        status = card_status(CARD, [self.PURCHASE], 100_000, date(2026, 10, 20))
        assert status.due_cents == 100_000
        assert status.pending_cents == 100_000
        assert status.outstanding_cents == 200_000

    def test_overdue_statements_accumulate(self) -> None:
        status = card_status(CARD, [self.PURCHASE], 0, date(2026, 10, 20))
        assert status.due_cents == 200_000

    def test_prepayment_reduces_open_cycle(self) -> None:
        status = card_status(CARD, [self.PURCHASE], 250_000, date(2026, 10, 20))
        assert status.due_cents == 0
        assert status.pending_cents == 50_000
        assert status.outstanding_cents == 50_000

    def test_fully_paid(self) -> None:
        status = card_status(CARD, [self.PURCHASE], 300_000, date(2026, 10, 20))
        assert (status.due_cents, status.pending_cents, status.outstanding_cents) == (0, 0, 0)

    def test_cycle_dates(self) -> None:
        status = card_status(CARD, [], 0, date(2026, 10, 20))
        assert status.cycle_start == date(2026, 10, 10)
        assert status.cycle_end == date(2026, 11, 10)
        assert status.payment_date == date(2026, 11, 25)
