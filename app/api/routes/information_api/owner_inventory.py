from fastapi import APIRouter, HTTPException, Query
from app.services.dataprovider import (
    get_inventory_overview_by_owner, 
    get_expiring_inventory_by_owner,
    get_inventory_cost_breakdown
    )

router = APIRouter()

@router.get("/overview")
async def inventory_overview(business_owner_id: int = Query(..., description="Business Owner ID")):
    try:
        data = await get_inventory_overview_by_owner(business_owner_id)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/expiry")
async def check_expiry(business_owner_id: int = Query(...)):
    try:
        data = await get_expiring_inventory_by_owner(business_owner_id)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost-breakdown")
async def inventory_cost_breakdown(business_owner_id: int = Query(...)):
    try:
        data = await get_inventory_cost_breakdown(business_owner_id)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from app.services.dataprovider import get_inventory_by_supplier_or_brand

@router.get("/by-supplier-or-brand")
async def inventory_by_supplier_or_brand(
    business_owner_id: int = Query(..., description="Business owner ID")
):
    try:
        data = await get_inventory_by_supplier_or_brand(business_owner_id)
        return {"success": True, "data": [dict(row) for row in data]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
