"""Transaction endpoints, including recurring materialization."""

import sqlite3

from fastapi import APIRouter, HTTPException, Query

from app import database as db
from app.schemas import CreatedOut, MaterializeResult, MessageOut, TransactionIn, TransactionOut

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _validate_kind(payload: TransactionIn, categories: dict[int, str]) -> None:
    """Validate kind-specific rules."""
    kind = payload.kind

    if kind == "transferencia":
        if payload.account_id is None or payload.to_account_id is None:
            raise HTTPException(
                status_code=400,
                detail="Transfers require both account_id (from) and to_account_id (to)",
            )
        if payload.account_id == payload.to_account_id:
            raise HTTPException(status_code=400, detail="Transfer accounts must be different")
        return

    if payload.category_id is None:
        raise HTTPException(status_code=400, detail="A category is required for this movement type")

    cat_type = categories.get(payload.category_id)
    if cat_type is None:
        raise HTTPException(status_code=400, detail="Category does not exist")
    if kind == "ingreso" and cat_type != "income":
        raise HTTPException(status_code=400, detail="Income movements require an income category")
    if kind in ("gasto", "gasto_tc") and cat_type != "expense":
        raise HTTPException(status_code=400, detail="Expense movements require an expense category")

    if kind == "gasto_tc":
        if payload.card_id is None:
            raise HTTPException(status_code=400, detail="Credit card expenses require a card_id")
        return

    if payload.account_id is None:
        raise HTTPException(
            status_code=400, detail="This movement requires an account (money goes in or out)"
        )


def _category_types() -> dict[int, str]:
    return {c.id: c.type for c in db.get_categories() if c.id is not None}


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
    _validate_kind(payload, _category_types())
    try:
        trans_id = db.add_transaction(
            date_val=payload.date,
            amount=payload.amount,
            category_id=payload.category_id,
            description=payload.description,
            is_recurring=payload.is_recurring,
            recurring_day=payload.recurring_day,
            subcategory_id=payload.subcategory_id,
            account_id=payload.account_id,
            kind=payload.kind,
            to_account_id=payload.to_account_id,
            card_id=payload.card_id,
        )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=400, detail="Category, subcategory or account does not exist"
        ) from None
    return CreatedOut(id=trans_id)


@router.put("/{trans_id}", response_model=MessageOut)
def update_transaction(trans_id: int, payload: TransactionIn) -> MessageOut:
    """Update a transaction."""
    _validate_kind(payload, _category_types())
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
            account_id=payload.account_id,
            kind=payload.kind,
            to_account_id=payload.to_account_id,
            card_id=payload.card_id,
        )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=400, detail="Category, subcategory or account does not exist"
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
