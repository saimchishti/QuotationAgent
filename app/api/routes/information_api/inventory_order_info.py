from fastapi import APIRouter, HTTPException
from typing import Any
from app.services.inventory_order_dataprovider import (
    get_purchase_orders,
    get_supplier_order_history,
    get_cost_per_order_breakdown,
    get_pending_deliveries,
    get_received_inventory_log,
    get_rejected_orders_log
)

router = APIRouter()

@router.get("/purchase-orders/{business_owner_id}")
async def purchase_orders(business_owner_id: int):
    return await get_purchase_orders(business_owner_id)


@router.get("/supplier-orders/{business_owner_id}")
async def supplier_order_history(business_owner_id: int):
    return await get_supplier_order_history(business_owner_id)

@router.get("/cost-breakdown/{business_owner_id}")
async def cost_breakdown_viewer(business_owner_id: int):
    try:
        data = await get_cost_per_order_breakdown(business_owner_id)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/pending-deliveries/{business_owner_id}")
async def pending_deliveries(business_owner_id: int) -> Any:
    try:
        result = await get_pending_deliveries(business_owner_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/received-log/{business_owner_id}")
async def received_inventory_log(business_owner_id: int):
    return await get_received_inventory_log(business_owner_id)


@router.get("/rejected-orders-log")
async def rejected_orders_log(business_owner_id: int):
    return await get_rejected_orders_log(business_owner_id)