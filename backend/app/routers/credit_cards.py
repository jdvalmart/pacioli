"""Credit card endpoints."""

import calendar
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, HTTPException

from app import clock
from app.db import cards as cards_db
from app.errors import IntegrityViolation
from app.schemas import CreatedOut, CreditCardIn, CreditCardOut, MessageOut

router = APIRouter(prefix="/credit-cards", tags=["credit-cards"])


def _reference_date(month: int | None, year: int | None) -> date:
    today = clock.today()
    if month is None or year is None or not 1 <= month <= 12:
        return today
    if (year, month) == (today.year, today.month):
        return today
    return date(year, month, calendar.monthrange(year, month)[1])


@router.get("", response_model=list[CreditCardOut])
def list_cards(
    month: int | None = None,
    year: int | None = None,
) -> list[CreditCardOut]:
    """List all credit cards with spending, payments, debt and available credit.

    Amounts are computed as of a reference date: today for the current
    month (or when no month is given), and the month's last day for any
    other month, so a past month shows how the card closed it. A fixed
    mid-month day would move the cycle past today's cutoff and report the
    still-open statement as already due.
    """
    cards = cards_db.get_credit_cards(today=_reference_date(month, year))
    return [
        CreditCardOut(
            id=c.id or 0,
            name=c.name,
            limit=c.limit,
            cutoff_day=c.cutoff_day,
            payment_day=c.payment_day,
            pending=c.pending or Decimal("0.00"),
            debt=c.debt or Decimal("0.00"),
            outstanding=c.outstanding or Decimal("0.00"),
            available=c.available if c.available is not None else c.limit,
            cycle_start=c.cycle_start or clock.today(),
            cycle_end=c.cycle_end or clock.today(),
            payment_date=c.payment_date or clock.today(),
        )
        for c in cards
    ]


@router.post("", response_model=CreatedOut, status_code=201)
def create_card(payload: CreditCardIn) -> CreatedOut:
    """Create a credit card."""
    try:
        card_id = cards_db.add_credit_card(
            name=payload.name,
            limit=payload.limit,
            cutoff_day=payload.cutoff_day,
            payment_day=payload.payment_day,
        )
    except IntegrityViolation:
        raise HTTPException(
            status_code=409, detail="A card with that name already exists"
        ) from None
    return CreatedOut(id=card_id)


@router.put("/{card_id}", response_model=MessageOut)
def update_card(card_id: int, payload: CreditCardIn) -> MessageOut:
    """Update a credit card."""
    cards_db.update_credit_card(
        card_id=card_id,
        name=payload.name,
        limit=payload.limit,
        cutoff_day=payload.cutoff_day,
        payment_day=payload.payment_day,
    )
    return MessageOut(message="Credit card updated")


@router.delete("/{card_id}", response_model=MessageOut)
def delete_card(card_id: int) -> MessageOut:
    """Delete a credit card, leaving its transactions unlinked."""
    cards_db.delete_credit_card(card_id)
    return MessageOut(message="Credit card deleted")
