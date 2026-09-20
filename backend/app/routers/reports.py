"""Reporting endpoints: summaries, comparisons and CSV export."""

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from app import database as db
from app.schemas import (
    BudgetVsActualOut,
    CategorySpendingOut,
    MonthlySummaryOut,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary", response_model=MonthlySummaryOut)
def monthly_summary(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2100),
) -> MonthlySummaryOut:
    """Return income, expense and balance totals for a month."""
    return MonthlySummaryOut(**db.get_monthly_summary(month, year).__dict__)


@router.get("/monthly", response_model=list[MonthlySummaryOut])
def yearly_summaries(year: int = Query(ge=2000, le=2100)) -> list[MonthlySummaryOut]:
    """Return the monthly summary for every month of a year."""
    return [MonthlySummaryOut(**s.__dict__) for s in db.get_monthly_summaries(year)]


@router.get("/category-spending", response_model=list[CategorySpendingOut])
def category_spending(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2100),
    type: str = Query(default="expense", pattern="^(income|expense)$"),
) -> list[CategorySpendingOut]:
    """Return spending totals by category, highest first."""
    rows = db.get_category_spending(month, year, type)
    return [CategorySpendingOut(name=n, total=t, color=c, icon=i) for n, t, c, i in rows]


@router.get("/budget-vs-actual", response_model=list[BudgetVsActualOut])
def budget_vs_actual(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2100),
) -> list[BudgetVsActualOut]:
    """Return budget vs actual spending per expense category."""
    return [BudgetVsActualOut(**row) for row in db.get_budget_vs_actual(month, year)]


@router.get("/export", response_class=PlainTextResponse)
def export_csv(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2100),
) -> PlainTextResponse:
    """Export the transactions of a month as a CSV download."""
    return PlainTextResponse(
        db.transactions_to_csv(month, year),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=pacioli_{year}-{month:02d}.csv"},
    )
