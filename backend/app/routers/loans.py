"""Loan endpoints (credits other than cards)."""

from fastapi import APIRouter, HTTPException

from app.db import loans as loans_db
from app.errors import IntegrityViolation
from app.schemas import CreatedOut, LoanIn, LoanOut, MessageOut

router = APIRouter(prefix="/loans", tags=["loans"])


@router.get("", response_model=list[LoanOut])
def list_loans() -> list[LoanOut]:
    """List loans with their balance today and payoff projection."""
    return [LoanOut(**loan.__dict__) for loan in loans_db.get_loans()]


@router.post("", response_model=CreatedOut, status_code=201)
def create_loan(payload: LoanIn) -> CreatedOut:
    """Register a loan from the balance the bank shows."""
    try:
        loan_id = loans_db.add_loan(**payload.model_dump())
    except IntegrityViolation:
        raise HTTPException(
            status_code=409, detail="A loan with that name already exists"
        ) from None
    return CreatedOut(id=loan_id)


@router.put("/{loan_id}", response_model=MessageOut)
def update_loan(loan_id: int, payload: LoanIn) -> MessageOut:
    """Edit a loan (a new balance and date re-anchor it to the bank)."""
    try:
        loans_db.update_loan(loan_id, **payload.model_dump())
    except IntegrityViolation:
        raise HTTPException(
            status_code=409, detail="A loan with that name already exists"
        ) from None
    return MessageOut(message="Loan updated")


@router.delete("/{loan_id}", response_model=MessageOut)
def delete_loan(loan_id: int) -> MessageOut:
    """Delete a loan; its payments remain as ordinary expenses."""
    loans_db.delete_loan(loan_id)
    return MessageOut(message="Loan deleted")
