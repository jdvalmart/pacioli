"""Account endpoints: where the money lives."""

import sqlite3
from decimal import Decimal

from fastapi import APIRouter, HTTPException

from app import database as db
from app.schemas import AccountIn, AccountOut, AccountUpdate, CreatedOut, MessageOut

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountOut])
def list_accounts() -> list[AccountOut]:
    """List all accounts with their computed balance."""
    return [
        AccountOut(
            id=a.id or 0,
            name=a.name,
            type=a.type,
            icon=a.icon,
            color=a.color,
            balance=a.balance or Decimal("0.00"),
        )
        for a in db.get_accounts()
    ]


@router.post("", response_model=CreatedOut, status_code=201)
def create_account(payload: AccountIn) -> CreatedOut:
    """Create an account, seeding it with an income transaction if money is provided."""
    try:
        account_id = db.add_account(
            name=payload.name,
            acct_type=payload.type,
            starting_amount=payload.starting_amount,
            icon=payload.icon,
            color=payload.color,
        )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409, detail="An account with that name already exists"
        ) from None
    return CreatedOut(id=account_id)


@router.put("/{account_id}", response_model=MessageOut)
def update_account(account_id: int, payload: AccountUpdate) -> MessageOut:
    """Update an account's name."""
    db.update_account(account_id, payload.name)
    return MessageOut(message="Account updated")


@router.delete("/{account_id}", response_model=MessageOut)
def delete_account(account_id: int) -> MessageOut:
    """Delete an account, leaving its transactions unlinked."""
    db.delete_account(account_id)
    return MessageOut(message="Account deleted")
