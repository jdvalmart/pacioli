"""Savings and investment endpoints: bolsillos, scheduled pockets, CDTs and stocks."""

import sqlite3
from decimal import Decimal

from fastapi import APIRouter, HTTPException

from app import database as db
from app.schemas import CreatedOut, MessageOut, SavingsIn, SavingsOut, SavingsUpdate

router = APIRouter(prefix="/savings", tags=["savings"])


@router.get("", response_model=list[SavingsOut])
def list_savings() -> list[SavingsOut]:
    """List all savings items with their computed balance."""
    return [
        SavingsOut(
            id=s.id or 0,
            name=s.name,
            kind=s.kind,
            target=s.target,
            rate_bp=s.rate_bp,
            term_days=s.term_days,
            current_value=s.current_value,
            dividends=s.dividends or Decimal("0.00"),
            scheduled_day=s.scheduled_day,
            scheduled_amount=s.scheduled_amount,
            source_account_id=s.source_account_id,
            opening=s.opening or Decimal("0.00"),
            balance=s.balance or Decimal("0.00"),
            invested=s.invested or Decimal("0.00"),
            matures_on=s.matures_on,
        )
        for s in db.get_savings()
    ]


@router.post("", response_model=CreatedOut, status_code=201)
def create_savings(payload: SavingsIn) -> CreatedOut:
    """Create a savings item, optionally seeding it with an initial deposit."""
    try:
        item_id = db.add_savings(
            name=payload.name,
            kind=payload.kind,
            target=payload.target,
            rate_bp=payload.rate_bp,
            term_days=payload.term_days,
            current_value=payload.current_value,
            dividends=payload.dividends,
            scheduled_day=payload.scheduled_day,
            scheduled_amount=payload.scheduled_amount,
            source_account_id=payload.source_account_id,
            initial_amount=payload.initial_amount,
            initial_account_id=payload.initial_account_id,
        )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409, detail="A savings item with that name already exists"
        ) from None
    return CreatedOut(id=item_id)


@router.put("/{item_id}", response_model=MessageOut)
def update_savings(item_id: int, payload: SavingsUpdate) -> MessageOut:
    """Update a savings item."""
    db.update_savings(
        item_id=item_id,
        name=payload.name,
        kind=payload.kind,
        target=payload.target,
        rate_bp=payload.rate_bp,
        term_days=payload.term_days,
        current_value=payload.current_value,
        dividends=payload.dividends,
        scheduled_day=payload.scheduled_day,
        scheduled_amount=payload.scheduled_amount,
        source_account_id=payload.source_account_id,
    )
    return MessageOut(message="Savings item updated")


@router.delete("/{item_id}", response_model=MessageOut)
def delete_savings(item_id: int) -> MessageOut:
    """Delete a savings item and its recurring template."""
    db.delete_savings(item_id)
    return MessageOut(message="Savings item deleted")
