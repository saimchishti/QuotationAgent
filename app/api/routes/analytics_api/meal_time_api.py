from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Dict, Any
import logging
from fastapi import APIRouter, Depends

from app.db.session import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

# Core logic — same as your existing function
async def get_meal_time_consumption(db: AsyncSession, days: int = 30) -> Dict[str, Any]:
    try:
        start_date = datetime.now() - timedelta(days=days)
        query = text("""
            SELECT 
                inventorycase1.name AS ingredient_name,
                menu_ingredient.quantity AS quantity_per_serving,
                customer_order.delivery_datetime
            FROM inventorycase1 
            JOIN menu_ingredient ON inventorycase1.id = menu_ingredient.ingredient_id 
            JOIN menu ON menu.id = menu_ingredient.menu_id 
            JOIN customer_order_menu_mapping ON customer_order_menu_mapping.menu_id = menu.id 
            JOIN customer_order ON customer_order.id = customer_order_menu_mapping.customer_order_id 
            WHERE customer_order.created_at >= :start_date
        """)

        result = await db.execute(query, {"start_date": start_date})
        rows = result.fetchall()

        consumption_data = {
            "lunch": {},
            "evening": {},
            "dinner": {}
        }

        for row in rows:
            ingredient_name = row.ingredient_name
            quantity = float(row.quantity_per_serving) if row.quantity_per_serving else 0.0
            delivery_datetime = row.delivery_datetime

            if isinstance(delivery_datetime, str):
                try:
                    if 'T' in delivery_datetime:
                        delivery_dt = datetime.fromisoformat(delivery_datetime.replace('Z', '+00:00'))
                    else:
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%d/%m/%Y %H:%M:%S']:
                            try:
                                delivery_dt = datetime.strptime(delivery_datetime, fmt)
                                break
                            except ValueError:
                                continue
                        else:
                            logger.warning(f"Could not parse delivery_datetime: {delivery_datetime}")
                            continue
                except Exception as e:
                    logger.warning(f"Error parsing delivery_datetime '{delivery_datetime}': {e}")
                    continue
            elif isinstance(delivery_datetime, datetime):
                delivery_dt = delivery_datetime
            else:
                logger.warning(f"Unexpected delivery_datetime type: {type(delivery_datetime)}")
                continue

            hour = delivery_dt.hour

            if 11 <= hour <= 15:
                meal_time = "lunch"
            elif 16 <= hour <= 19:
                meal_time = "evening"
            elif 20 <= hour <= 23:
                meal_time = "dinner"
            else:
                continue

            if ingredient_name not in consumption_data[meal_time]:
                consumption_data[meal_time][ingredient_name] = 0

            consumption_data[meal_time][ingredient_name] += quantity

        for meal_time in consumption_data:
            for ingredient in consumption_data[meal_time]:
                consumption_data[meal_time][ingredient] = round(consumption_data[meal_time][ingredient], 2)

        total_ingredients = set()
        total_consumption = 0

        for meal_time in consumption_data:
            for ingredient, quantity in consumption_data[meal_time].items():
                total_ingredients.add(ingredient)
                total_consumption += quantity

        response = {
            "status": "success",
            "data": consumption_data,
            "summary": {
                "total_unique_ingredients": len(total_ingredients),
                "total_consumption": round(total_consumption, 2),
                "meal_time_breakdown": {
                    meal_time: {
                        "ingredient_count": len(consumption_data[meal_time]),
                        "total_quantity": round(sum(consumption_data[meal_time].values()), 2)
                    }
                    for meal_time in consumption_data
                }
            },
            "period_days": days,
            "generated_at": datetime.now().isoformat()
        }

        return response

    except Exception as e:
        logger.error(f"Error in get_meal_time_consumption: {e}")
        raise

# ✅ Expose via FastAPI router endpoint
@router.get("/api/v1/consumption/meal-time", tags=["Inventory Consumption"], summary="Ingredient Consumption by Meal Time")
async def meal_time_consumption_api(
    days: int = 7,
    db: AsyncSession = Depends(get_db)
):
    """
    Get ingredient consumption aggregated by meal time (lunch, evening, dinner)
    """
    return await get_meal_time_consumption(db, days=days)
