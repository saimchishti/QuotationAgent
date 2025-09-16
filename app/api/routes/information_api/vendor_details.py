# RESTAURANT-AGENT-MAIN/app/api/routes/information_api/vendor_details.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_restaurant_db
from app.services.dataprovidor_vendor import (
    get_vendor_directory,
    get_ingredient_to_vendor_mapping,
    get_vendor_performance,
    get_ingredient_sourcing_options,
    get_vendor_branch_linkage
)

router = APIRouter()

@router.get("/vendor/directory", tags=["Information - Vendor Details"])
async def get_vendor_directory_viewer(
    business_owner_id: Optional[int] = Query(None, description="Optional: Filter by Business Owner ID"),
    db: AsyncSession = Depends(get_restaurant_db)
):
    """
    List vendors with contact info, ingredients, and linked branches.
    Can be filtered by a specific business owner.
    """
    try:
        data = await get_vendor_directory(db, business_owner_id)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/vendor/ingredient-mapper", tags=["Information - Vendor Details"])
async def get_ingredient_vendor_mapper(
    business_owner_id: int = Query(..., description="Business Owner ID"),
    db: AsyncSession = Depends(get_restaurant_db)
):
    """
    Shows which vendor supplies each ingredient for a specific business owner.
    """
    try:
        data = await get_ingredient_to_vendor_mapping(db, business_owner_id)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/vendor/performance", tags=["Information - Vendor Details"])
async def get_vendor_performance_tracker(
    business_owner_id: int = Query(..., description="Business Owner ID"),
    db: AsyncSession = Depends(get_restaurant_db)
):
    """

    Tracks performance metrics (cost, delivery time, status) for vendors
    used by a specific business owner.
    """
    try:
        data = await get_vendor_performance(db, business_owner_id)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/vendor/sourcing-optimizer", tags=["Information - Vendor Details"])
async def get_ingredient_sourcing_optimizer(
    business_owner_id: int = Query(..., description="Business Owner ID"),
    ingredient_name: str = Query(..., description="Name of the ingredient to search for"),
    db: AsyncSession = Depends(get_restaurant_db)
):
    """
    Finds vendors for a specific ingredient relevant to a business owner,
    comparing price and delivery time.
    """
    try:
        data = await get_ingredient_sourcing_options(db, business_owner_id, ingredient_name)
        response = [
            {
                "vendor_name": row.vendor_name,
                "price_per_unit": row.price_per_unit,
                "delivery_time_frame": row.delivery_time_frame
            } for row in data
        ]
        return {"success": True, "data": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/vendor/branch-linkage", tags=["Information - Vendor Details"])
async def get_vendor_to_branch_linkage(
    business_owner_id: int = Query(..., description="Business Owner ID"),
    db: AsyncSession = Depends(get_restaurant_db)
):
    """
    Shows which vendors a specific business owner (branch) uses and how often.
    """
    try:
        data = await get_vendor_branch_linkage(db, business_owner_id)
        response = [{"vendor_name": row.vendor_name, "order_count": row.order_count} for row in data]
        return {"success": True, "data": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
