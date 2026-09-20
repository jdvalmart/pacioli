"""Credit card endpoints."""

import sqlite3
from decimal import Decimal

from fastapi import APIRouter, HTTPException

from app import database as db
from app.schemas import CreatedOut, CreditCardIn, CreditCardOut, MessageOut

router = APIRouter(prefix="/credit-cards", tags=["credit-cards"])


@router.get("", response_model=list[CreditCardOut])
def list_cards() -> list[CreditCardOut]:
    """List all credit cards with spending and available credit."""
    return [
        CreditCardOut(
            id=c.id or 0,
            name=c.name,
            limit=c.limit,
            cutoff_day=c.cutoff_day,
            payment_day=c.payment_day,
            spent=c.spent or Decimal("0.00"),
            available=c.available or c.limit,
        )
        for c in db.get_credit_cards()
    ]


@router.post("", response_model=CreatedOut, status_code=201)
def create_card(payload: CreditCardIn) -> CreatedOut:
    """Create a credit card."""
    try:
        card_id = db.add_credit_card(
            name=payload.name,
            limit=payload.limit,
            cutoff_day=payload.cutoff_day,
            payment_day=payload.payment_day,
        )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409, detail="A card with that name already exists"
        ) from None
    return CreatedOut(id=card_id)


@router.put("/{card_id}", response_model=MessageOut)
def update_card(card_id: int, payload: CreditCardIn) -> MessageOut:
    """Update a credit card."""
    db.update_credit_card(
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
    db.delete_credit_card(card_id)
    return MessageOut(message="Credit card deleted")
