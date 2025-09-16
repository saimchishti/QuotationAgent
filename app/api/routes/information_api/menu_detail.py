# RESTAURANT-AGENT-MAIN/app/api/routes/information_api/menu_details.py

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict

from app.db.session import get_restaurant_db
from app.services.dataprovider_menu import (
    get_menu_items_with_ingredients,
    get_menu_by_category,
    get_menu_item_availability,
    get_menu_price_history
    )

router = APIRouter()

@router.get("/menu/items", tags=["Information - Menu Details"])
async def get_menu_item_manager(
    business_owner_id: int = Query(..., description="Business Owner ID"),
    db: AsyncSession = Depends(get_restaurant_db)
):
    """View all menu items with their prices and ingredients."""
    try:
        items = await get_menu_items_with_ingredients(db, business_owner_id)
        response = [
            {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "price": item.price,
                "ingredients": [
                    {
                        "name": ing.ingredient.name,
                        "quantity": ing.quantity,
                        "unit": ing.ingredient.unit_type.value if ing.ingredient.unit_type else "N/A"
                    } for ing in item.menu_ingredients
                ]
            } for item in items
        ]
        return {"success": True, "data": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/menu/categories", tags=["Information - Menu Details"])
async def get_menu_category_overview(
    business_owner_id: int = Query(..., description="Business Owner ID"),
    db: AsyncSession = Depends(get_restaurant_db)
):
    """Organize the menu by categories."""
    try:
        items = await get_menu_by_category(db, business_owner_id)
        response = defaultdict(list)
        for item in items:
            category_name = item.menu_category.value if item.menu_category else "Uncategorized"
            response[category_name].append({"id": item.id, "name": item.name, "price": item.price})
        return {"success": True, "data": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/menu/availability", tags=["Information - Menu Details"])
async def get_item_availability_tracker(
    business_owner_id: int = Query(..., description="Business Owner ID"),
    db: AsyncSession = Depends(get_restaurant_db)
):
    """Show which menu items are in or out of stock based on ingredients."""
    try:
        data = await get_menu_item_availability(db, business_owner_id)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/menu/price-history", tags=["Information - Menu Details"])
async def get_menu_change_log(
    business_owner_id: int = Query(..., description="Business Owner ID"),
    db: AsyncSession = Depends(get_restaurant_db)
):
    """View the history of price changes for menu items."""
    try:
        history = await get_menu_price_history(db, business_owner_id)
        response = [
            {
                "menu_item": item.menu.name,
                "old_price": item.old_price,
                "new_price": item.new_price,
                "changed_on": item.effective_date.isoformat(),
                "reason": item.reason
            } for item in history
        ]
        return {"success": True, "data": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

