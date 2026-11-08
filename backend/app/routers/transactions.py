"""Transaction endpoints, including recurring materialization."""

from fastapi import APIRouter, Query

from app.db import transactions as transactions_db
from app.schemas import CreatedOut, MaterializeResult, MessageOut, TransactionIn, TransactionOut
from app.services import transactions

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2100),
) -> list[TransactionOut]:
    """List the transactions of a month, newest first."""
    return [TransactionOut(**t.__dict__) for t in transactions_db.get_transactions(month, year)]


@router.post("", response_model=CreatedOut, status_code=201)
def create_transaction(payload: TransactionIn) -> CreatedOut:
    """Create a transaction."""
    trans_id = transactions.create(payload)
    return CreatedOut(id=trans_id)


@router.put("/{trans_id}", response_model=MessageOut)
def update_transaction(trans_id: int, payload: TransactionIn) -> MessageOut:
    """Update a transaction."""
    transactions.update(trans_id, payload)
    return MessageOut(message="Transaction updated")


@router.delete("/{trans_id}", response_model=MessageOut)
def delete_transaction(trans_id: int) -> MessageOut:
    """Delete a transaction."""
    transactions_db.delete_transaction(trans_id)
    return MessageOut(message="Transaction deleted")


@router.post("/materialize", response_model=MaterializeResult)
def materialize_recurring(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2100),
) -> MaterializeResult:
    """Materialize recurring templates for a month.

    Idempotent: months already materialized return created=0.
    """
    return MaterializeResult(created=transactions_db.ensure_recurring(month, year))
