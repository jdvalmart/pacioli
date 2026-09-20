"""Category and subcategory endpoints."""

import sqlite3

from fastapi import APIRouter, HTTPException, Query

from app import database as db
from app.schemas import (
    CategoryIn,
    CategoryOut,
    CategoryUpdate,
    CreatedOut,
    MessageOut,
    SubcategoryIn,
    SubcategoryOut,
)

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(
    type: str | None = Query(default=None, pattern="^(income|expense)$"),
) -> list[CategoryOut]:
    """List categories, optionally filtered by type."""
    return [CategoryOut(**c.__dict__) for c in db.get_categories(type)]


@router.post("", response_model=CreatedOut, status_code=201)
def create_category(payload: CategoryIn) -> CreatedOut:
    """Create a category."""
    try:
        cat_id = db.add_category(payload.name, payload.type, payload.color, payload.icon)
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409, detail="A category with that name already exists"
        ) from None
    return CreatedOut(id=cat_id)


@router.put("/{cat_id}", response_model=MessageOut)
def update_category(cat_id: int, payload: CategoryUpdate) -> MessageOut:
    """Update a category's name, color and icon."""
    db.update_category(cat_id, payload.name, payload.color, payload.icon)
    return MessageOut(message="Category updated")


@router.delete("/{cat_id}", response_model=MessageOut)
def delete_category(cat_id: int) -> MessageOut:
    """Delete a category, refusing if transactions or budgets reference it."""
    try:
        db.delete_category(cat_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return MessageOut(message="Category deleted")


@router.get("/{cat_id}/subcategories", response_model=list[SubcategoryOut])
def list_subcategories(cat_id: int) -> list[SubcategoryOut]:
    """List the subcategories of a category."""
    return [SubcategoryOut(**s.__dict__) for s in db.get_subcategories(cat_id)]


@router.post("/{cat_id}/subcategories", response_model=CreatedOut, status_code=201)
def create_subcategory(cat_id: int, payload: SubcategoryIn) -> CreatedOut:
    """Create a subcategory inside a category."""
    try:
        sub_id = db.add_subcategory(cat_id, payload.name, payload.icon)
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409, detail="A subcategory with that name already exists in this category"
        ) from None
    return CreatedOut(id=sub_id)


@router.delete("/subcategories/{sub_id}", response_model=MessageOut)
def delete_subcategory(sub_id: int) -> MessageOut:
    """Delete a subcategory, detaching it from its transactions."""
    db.delete_subcategory(sub_id)
    return MessageOut(message="Subcategory deleted")
