"""Unit tests for the pure credit card billing rules."""

import random
from datetime import date, timedelta

from app.domain.billing import (
    Card,
    Purchase,
    billed_in_month,
    card_status,
    cutoff_of,
    cycle_of,
    financed_cents,
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

    def test_billed_in_month(self) -> None:
        purchase = Purchase(date(2026, 9, 5), 30_000, 3)
        (item,) = billed_in_month(CARD, purchase, 2026, 10)
        assert (item.number, item.cents) == (2, 10_000)
        assert billed_in_month(CARD, purchase, 2026, 12) == []

    def test_two_installments_can_fall_due_in_the_same_month(self) -> None:
        """Cutoff 31 / payment 30: January's statement is due Feb 28 (no Feb 30)
        and February's, closing Feb 28, is due that same day."""
        card = Card(cutoff_day=31, payment_day=30)
        purchase = Purchase(date(2026, 12, 15), 300_000, 3)
        items = billed_in_month(card, purchase, 2027, 2)
        assert [(i.number, i.cents) for i in items] == [(2, 100_000), (3, 100_000)]
        assert billed_in_month(card, purchase, 2027, 3) == []


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


class TestFastPathsMatchSchedule:
    """billed_in_month and card_status skip building schedules; ``schedule``
    is the readable reference they must match exactly."""

    @staticmethod
    def _random_case(rng: random.Random) -> tuple[Card, Purchase]:
        card = Card(cutoff_day=rng.randint(1, 31), payment_day=rng.randint(1, 31))
        purchase = Purchase(
            date=date(2023, 1, 1) + timedelta(days=rng.randint(0, 5 * 365)),
            amount_cents=rng.randint(1, 50_000_000),
            installments=rng.choice([1, 2, 3, 6, 12, 18, 24, 36]),
            interest_bp=rng.choice([0, 0, 150, 1200, 2475]),
        )
        return card, purchase

    def test_billed_in_month(self) -> None:
        rng = random.Random(20261108)
        for _ in range(3000):
            card, purchase = self._random_case(rng)
            due_by_month: dict[tuple[int, int], int] = {}
            for item in schedule(card, purchase):
                key = (item.year, item.month)
                due_by_month[key] = due_by_month.get(key, 0) + item.cents
            start = purchase.date.year * 12 + purchase.date.month - 1
            for index in range(start - 1, start + purchase.installments + 3):
                year, month = divmod(index, 12)
                fast = sum(i.cents for i in billed_in_month(card, purchase, year, month + 1))
                assert fast == due_by_month.get((year, month + 1), 0), (
                    card,
                    purchase,
                    year,
                    month + 1,
                )

    def test_card_status(self) -> None:
        rng = random.Random(42)
        for _ in range(400):
            card = Card(cutoff_day=rng.randint(1, 31), payment_day=rng.randint(1, 31))
            purchases = [self._random_case(rng)[1] for _ in range(rng.randint(0, 8))]
            payments = rng.randint(0, 80_000_000)
            today = date(2023, 1, 1) + timedelta(days=rng.randint(0, 6 * 365))

            open_cycle = cycle_of(card, today)
            closed = sum(
                i.cents for p in purchases for i in schedule(card, p) if i.cycle < open_cycle
            )
            open_ = sum(
                i.cents for p in purchases for i in schedule(card, p) if i.cycle == open_cycle
            )
            financed = sum(financed_cents(p) for p in purchases)
            outstanding = max(financed - payments, 0)
            expected = (
                min(max(open_ - max(payments - closed, 0), 0), outstanding),
                max(closed - payments, 0),
                outstanding,
            )
            status = card_status(card, purchases, payments, today)
            assert (status.pending_cents, status.due_cents, status.outstanding_cents) == expected

    def test_installments_fall_due_within_the_sql_window(self) -> None:
        """The SQL prefilter (app.db.cards.CARD_CANDIDATES_SQL) keeps purchases
        whose month index p satisfies p <= due <= p + installments + 1. If this
        bound were wrong, the prefilter would silently drop real installments."""
        rng = random.Random(7)
        for _ in range(5000):
            card, purchase = self._random_case(rng)
            p = purchase.date.year * 12 + purchase.date.month - 1
            for item in schedule(card, purchase):
                due = item.year * 12 + item.month - 1
                assert p <= due <= p + purchase.installments + 1, (card, purchase, item)
