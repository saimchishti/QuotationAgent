from datetime import datetime, timedelta
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Wastage, InventoryCase1
import re
from fastapi import APIRouter, Depends
from app.db.session import get_db

router = APIRouter()

def extract_numeric_price(price_str):
    if not price_str:
        return 0.0
    match = re.search(r"\d+(\.\d+)?", price_str.replace(",", ""))
    return float(match.group()) if match else 0.0

async def get_waste_report(session: AsyncSession, days: int = 30):
    start_date = datetime.utcnow() - timedelta(days=days)

    query = (
        select(
            InventoryCase1.id.label("ingredient_id"),
            InventoryCase1.name.label("ingredient_name"),
            InventoryCase1.price_per_unit,
            func.sum(Wastage.wastage_qty).label("stock_wasted"),
            func.sum(Wastage.loss_value).label("loss_value"),
        )
        .join(Wastage.inventory)
        .where(
            or_(
                Wastage.created_at == None,
                Wastage.created_at >= start_date
            )
        )
        .group_by(InventoryCase1.id, InventoryCase1.name, InventoryCase1.price_per_unit)
    )

    result = await session.execute(query)
    records = result.fetchall()

    response = []
    for row in records:
        stock_wasted = float(row.stock_wasted or 0)
        loss_value = float(row.loss_value or 0)
        unit_price = extract_numeric_price(row.price_per_unit)

        if loss_value > 1000:
            suggestion = "High-value loss — audit supplier or process"
        elif stock_wasted > 15:
            suggestion = "Large quantity wasted — consider reducing order size"
        elif 5 < stock_wasted <= 15:
            suggestion = "Moderate wastage — monitor closely"
        elif unit_price > 200 and stock_wasted > 2:
            suggestion = "Expensive ingredient waste — improve storage or prep"
        else:
            suggestion = "Wastage under control"

        response.append({
            "ingredient_name": row.ingredient_name,
            "stock_wasted": round(stock_wasted, 2),
            "loss_value": round(loss_value, 2),
            "suggestion": suggestion
        })

    return response

# ✅ FastAPI route

@router.get("/api/v1/waste/reduction-report", tags=["Inventory Wastage"], summary="Waste Reduction Report")
async def api_get_waste_report(db: AsyncSession = Depends(get_db)):
    return await get_waste_report(db, days=30)
