"""Monthly budget endpoints."""

import sqlite3

from fastapi import APIRouter, HTTPException, Query

from app import database as db
from app.schemas import BudgetIn, BudgetOut, MessageOut

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("", response_model=list[BudgetOut])
def list_budgets(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2100),
) -> list[BudgetOut]:
    """List the budgets of a month."""
    return [BudgetOut(**b.__dict__) for b in db.get_budgets(month, year)]


@router.put("", response_model=MessageOut)
def upsert_budget(payload: BudgetIn) -> MessageOut:
    """Create or update the budget of a category for a month."""
    try:
        db.set_budget(payload.category_id, payload.month, payload.year, payload.amount)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Category does not exist") from None
    return MessageOut(message="Budget saved")


@router.delete("", response_model=MessageOut)
def delete_budget(
    category_id: int = Query(),
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2100),
) -> MessageOut:
    """Delete the budget of a category for a month."""
    db.delete_budget(category_id, month, year)
    return MessageOut(message="Budget deleted")
