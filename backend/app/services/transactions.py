"""Transaction use cases: business validation plus persistence.

Routers stay thin (HTTP in, HTTP out); every rule about what a movement
may do lives here and raises ``app.errors`` exceptions, never HTTP ones.
"""

from datetime import date
from decimal import Decimal
from typing import TypedDict

from app import clock
from app import database as db
from app.domain.kinds import TxKind
from app.errors import IntegrityViolation, ValidationFailed
from app.schemas import TransactionIn

_MISSING_REFERENCE = "Category, subcategory or account does not exist"


def validate(payload: TransactionIn) -> None:
    """Check the kind-specific business rules of a movement.

    Raises:
        ValidationFailed: with a user-facing message.
    """
    kind = payload.kind

    if kind == TxKind.TRANSFERENCIA:
        if payload.account_id is None or payload.to_account_id is None:
            raise ValidationFailed(
                "Transfers require both account_id (from) and to_account_id (to)",
            )
        if payload.account_id == payload.to_account_id:
            raise ValidationFailed("Transfer accounts must be different")
        return

    if kind == TxKind.PAGO_TC:
        if payload.account_id is None or payload.card_id is None:
            raise ValidationFailed(
                "Card payments require account_id (source) and card_id",
            )
        cards = {c.id: c for c in db.get_credit_cards(today=clock.today())}
        card = cards.get(payload.card_id)
        if card is None:
            raise ValidationFailed("Credit card does not exist")
        outstanding = card.outstanding or Decimal("0.00")
        if outstanding <= 0:
            raise ValidationFailed("Nothing to pay on this card")
        if payload.amount > outstanding:
            raise ValidationFailed(
                f"The amount exceeds the outstanding balance ({outstanding})",
            )
        accounts = {a.id: a for a in db.get_accounts()}
        source = accounts.get(payload.account_id)
        if source is None:
            raise ValidationFailed("Source account does not exist")
        if (source.balance or Decimal("0.00")) < payload.amount:
            raise ValidationFailed(
                "Insufficient balance in the source account",
            )
        return

    if kind in (TxKind.AHORRO, TxKind.RETIRO):
        if payload.account_id is None or payload.savings_id is None:
            raise ValidationFailed(
                "Savings movements require account_id and savings_id",
            )
        items = {s.id: s for s in db.get_savings()}
        item = items.get(payload.savings_id)
        if item is None:
            raise ValidationFailed("Savings item does not exist")
        if item.matures_on is not None and item.matures_on > clock.today():
            raise ValidationFailed(
                (f"This savings item is locked until it matures on {item.matures_on.isoformat()}"),
            )
        accounts = {a.id: a for a in db.get_accounts()}
        if accounts.get(payload.account_id) is None:
            raise ValidationFailed("Account does not exist")
        return

    if payload.category_id is None:
        raise ValidationFailed("A category is required for this movement type")

    cat_type = _category_types().get(payload.category_id)
    if cat_type is None:
        raise ValidationFailed("Category does not exist")
    if kind == TxKind.INGRESO and cat_type != "income":
        raise ValidationFailed("Income movements require an income category")
    if kind in (TxKind.GASTO, TxKind.GASTO_TC) and cat_type != "expense":
        raise ValidationFailed("Expense movements require an expense category")

    if kind == TxKind.GASTO_TC:
        if payload.card_id is None:
            raise ValidationFailed("Credit card expenses require a card_id")
        return

    if payload.account_id is None:
        raise ValidationFailed("This movement requires an account (money goes in or out)")


def _category_types() -> dict[int, str]:
    return {c.id: c.type for c in db.get_categories() if c.id is not None}


class _TransactionFields(TypedDict):
    """Keyword arguments shared by ``db.add_transaction`` and ``db.update_transaction``."""

    date_val: date
    amount: Decimal
    category_id: int | None
    description: str
    is_recurring: bool
    recurring_day: int | None
    subcategory_id: int | None
    account_id: int | None
    kind: str
    to_account_id: int | None
    card_id: int | None
    savings_id: int | None
    installments: int
    interest_bp: int


def _fields(payload: TransactionIn) -> _TransactionFields:
    return {
        "date_val": payload.date,
        "amount": payload.amount,
        "category_id": payload.category_id,
        "description": payload.description,
        "is_recurring": payload.is_recurring,
        "recurring_day": payload.recurring_day,
        "subcategory_id": payload.subcategory_id,
        "account_id": payload.account_id,
        "kind": str(payload.kind),
        "to_account_id": payload.to_account_id,
        "card_id": payload.card_id,
        "savings_id": payload.savings_id,
        "installments": payload.installments,
        "interest_bp": payload.interest_bp,
    }


def create(payload: TransactionIn) -> int:
    """Validate and store a new movement; return its id."""
    validate(payload)
    try:
        return db.add_transaction(**_fields(payload))
    except IntegrityViolation:
        raise ValidationFailed(_MISSING_REFERENCE) from None


def update(trans_id: int, payload: TransactionIn) -> None:
    """Validate and replace an existing movement."""
    validate(payload)
    try:
        db.update_transaction(trans_id=trans_id, **_fields(payload))
    except IntegrityViolation:
        raise ValidationFailed(_MISSING_REFERENCE) from None
