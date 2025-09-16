# api/routes/inventory.py

from fastapi import APIRouter
from app.services.wastage_provider import get_daily_wastage_log, get_order_to_waste_correlation

router = APIRouter()

@router.get("/daily-wastage-log")
async def daily_wastage_log(business_owner_id: int):
    return await get_daily_wastage_log(business_owner_id)

@router.get("/order-to-waste-correlation")
async def order_to_waste_correlation(business_owner_id: int):
    return await get_order_to_waste_correlation(business_owner_id)