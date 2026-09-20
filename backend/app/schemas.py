"""Pydantic schemas for the Pacioli API.

Money amounts are Decimal internally and serialize as fixed-precision
strings (e.g. "1234.56") to avoid the precision loss of JSON floats.
Inputs accept either a number or a string and are coerced to Decimal.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, PlainSerializer

Money = Annotated[Decimal, PlainSerializer(lambda v: f"{v:.2f}", return_type=str)]


class CategoryIn(BaseModel):
    """Payload to create a category."""

    name: str = Field(min_length=1, max_length=100)
    type: Literal["income", "expense"]
    color: str = "#3B82F6"
    icon: str = "📁"


class CategoryUpdate(BaseModel):
    """Payload to update a category (type is immutable)."""

    name: str = Field(min_length=1, max_length=100)
    color: str = "#3B82F6"
    icon: str = "📁"


class CategoryOut(BaseModel):
    """Category as returned by the API."""

    id: int
    name: str
    type: str
    color: str
    icon: str


class SubcategoryIn(BaseModel):
    """Payload to create a subcategory."""

    name: str = Field(min_length=1, max_length=100)
    icon: str = "📁"


class SubcategoryOut(BaseModel):
    """Subcategory as returned by the API."""

    id: int
    category_id: int
    name: str
    icon: str


class TransactionIn(BaseModel):
    """Payload to create or update a transaction."""

    date: date
    amount: Money = Field(gt=0)
    category_id: int
    description: str = Field(default="", max_length=500)
    is_recurring: bool = False
    recurring_day: int | None = Field(default=None, ge=1, le=31)
    subcategory_id: int | None = None


class TransactionOut(BaseModel):
    """Transaction as returned by the API."""

    id: int
    date: date
    amount: Money
    category_id: int
    description: str
    is_recurring: bool
    recurring_day: int | None
    subcategory_id: int | None
    subcategory_name: str | None
    subcategory_icon: str | None
    generated_from: int | None
    category_name: str
    category_type: str
    color: str
    icon: str


class BudgetIn(BaseModel):
    """Payload to upsert a monthly budget."""

    category_id: int
    month: int = Field(ge=1, le=12)
    year: int
    amount: Money = Field(gt=0)


class BudgetOut(BaseModel):
    """Budget as returned by the API."""

    id: int
    category_id: int
    month: int
    year: int
    amount: Money


class MonthlySummaryOut(BaseModel):
    """Aggregated totals for a month."""

    month: int
    year: int
    total_income: Money
    total_expense: Money
    balance: Money
    by_category: dict[str, Money]


class CategorySpendingOut(BaseModel):
    """Spending total of a single category."""

    name: str
    total: Money
    color: str
    icon: str


class BudgetVsActualOut(BaseModel):
    """Budget vs actual comparison for an expense category."""

    category_id: int
    name: str
    color: str
    icon: str
    budget: Money
    actual: Money
    remaining: Money
    percent: float


class MaterializeResult(BaseModel):
    """Result of materializing recurring transactions."""

    created: int


class CreatedOut(BaseModel):
    """Generic response with the id of a created resource."""

    id: int


class MessageOut(BaseModel):
    """Generic message response."""

    message: str
