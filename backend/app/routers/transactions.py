"""Transaction endpoints, including recurring materialization."""

import sqlite3

from fastapi import APIRouter, HTTPException, Query

from app import database as db
from app.schemas import CreatedOut, MaterializeResult, MessageOut, TransactionIn, TransactionOut

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2100),
) -> list[TransactionOut]:
    """List the transactions of a month, newest first."""
    return [TransactionOut(**t.__dict__) for t in db.get_transactions(month, year)]


@router.post("", response_model=CreatedOut, status_code=201)
def create_transaction(payload: TransactionIn) -> CreatedOut:
    """Create a transaction."""
    try:
        trans_id = db.add_transaction(
            date_val=payload.date,
            amount=payload.amount,
            category_id=payload.category_id,
            description=payload.description,
            is_recurring=payload.is_recurring,
            recurring_day=payload.recurring_day,
            subcategory_id=payload.subcategory_id,
        )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=400, detail="Category or subcategory does not exist"
        ) from None
    return CreatedOut(id=trans_id)


@router.put("/{trans_id}", response_model=MessageOut)
def update_transaction(trans_id: int, payload: TransactionIn) -> MessageOut:
    """Update a transaction."""
    try:
        db.update_transaction(
            trans_id=trans_id,
            date_val=payload.date,
            amount=payload.amount,
            category_id=payload.category_id,
            description=payload.description,
            is_recurring=payload.is_recurring,
            recurring_day=payload.recurring_day,
            subcategory_id=payload.subcategory_id,
        )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=400, detail="Category or subcategory does not exist"
        ) from None
    return MessageOut(message="Transaction updated")


@router.delete("/{trans_id}", response_model=MessageOut)
def delete_transaction(trans_id: int) -> MessageOut:
    """Delete a transaction."""
    db.delete_transaction(trans_id)
    return MessageOut(message="Transaction deleted")


@router.post("/materialize", response_model=MaterializeResult)
def materialize_recurring(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2100),
) -> MaterializeResult:
    """Materialize recurring templates for a month.

    Idempotent: months already materialized return created=0.
    """
    return MaterializeResult(created=db.ensure_recurring(month, year))
