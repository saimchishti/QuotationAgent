from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.routes.inventory_prediction import predict_stock_depletion
import logging
from fastapi import APIRouter, Depends
from app.db.session import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

class TopDepletionTracker:
    @staticmethod
    def calculate_depletion_priority(predicted_days_left: float, avg_daily_usage: float) -> float:
        if predicted_days_left <= 0:
            return 1000
        urgency_score = 100 / predicted_days_left
        usage_factor = min(avg_daily_usage * 2, 50)
        priority_score = urgency_score + usage_factor
        if predicted_days_left < 3:
            priority_score *= 1.5
        return round(priority_score, 2)

def get_urgency_level(days_remaining: float) -> str:
    if days_remaining <= 1:
        return "Critical"
    elif days_remaining <= 3:
        return "High"
    elif days_remaining <= 7:
        return "Medium"
    else:
        return "Low"

async def get_top_10_depletion_items(session: AsyncSession) -> List[Dict[str, Any]]:
    try:
        stock_data = await predict_stock_depletion(session)
        if not stock_data:
            return []

        depletion_items = []
        for item in stock_data:
            predicted_days_left = item.get('predicted_days_left', float('inf'))
            avg_daily_usage = item.get('avg_daily_usage', 0)
            if predicted_days_left == float('inf'):
                continue

            priority_score = TopDepletionTracker.calculate_depletion_priority(
                predicted_days_left, avg_daily_usage
            )

            depletion_items.append({
                "ingredient_name": item.get('ingredient_name'),
                "days_remaining": predicted_days_left,
                "avg_daily_usage": avg_daily_usage,
                "current_stock": item.get('current_stock', 0),
                "priority_score": priority_score,
                "urgency_level": get_urgency_level(predicted_days_left)
            })

        top_10_items = sorted(depletion_items, key=lambda x: x['priority_score'], reverse=True)[:10]
        return top_10_items

    except Exception as e:
        logger.error(f"Error getting top 10 depletion items: {e}")
        raise

async def get_top_10_depletion_summary(session: AsyncSession) -> List[Dict[str, Any]]:
    try:
        top_10_items = await get_top_10_depletion_items(session)
        summary = [{
            "rank": idx + 1,
            "ingredient_name": item['ingredient_name'],
            "days_remaining": item['days_remaining'],
            "urgency_level": item['urgency_level']
        } for idx, item in enumerate(top_10_items)]
        return summary
    except Exception as e:
        logger.error(f"Error getting top 10 depletion summary: {e}")
        raise

async def get_depletion_analytics(session: AsyncSession) -> Dict[str, Any]:
    try:
        top_10_items = await get_top_10_depletion_items(session)
        if not top_10_items:
            return {
                "top_10_items": [],
                "analytics": {
                    "total_items_tracked": 0,
                    "critical_items": 0,
                    "high_priority_items": 0,
                    "average_days_remaining": 0
                }
            }

        critical_items = sum(1 for item in top_10_items if item['urgency_level'] == 'Critical')
        high_priority_items = sum(1 for item in top_10_items if item['urgency_level'] in ['Critical', 'High'])
        avg_days_remaining = sum(item['days_remaining'] for item in top_10_items) / len(top_10_items)

        return {
            "top_10_items": top_10_items,
            "analytics": {
                "total_items_tracked": len(top_10_items),
                "critical_items": critical_items,
                "high_priority_items": high_priority_items,
                "average_days_remaining": round(avg_days_remaining, 2)
            }
        }
    except Exception as e:
        logger.error(f"Error getting depletion analytics: {e}")
        raise

# ✅ FastAPI Routes

@router.get("/api/v1/depletion/top-10", tags=["Inventory Deletion"], summary="Top 10 Fastest Depleting Items")
async def api_get_top_10_depletion_items(db: AsyncSession = Depends(get_db)):
    return await get_top_10_depletion_items(db)

@router.get("/api/v1/depletion/top-10-summary", tags=["Inventory Deletion"], summary="Top 10 Depletion Summary")
async def api_get_top_10_depletion_summary(db: AsyncSession = Depends(get_db)):
    return await get_top_10_depletion_summary(db)

@router.get("/api/v1/depletion/analytics", tags=["Inventory Deletion"], summary="Depletion Analytics Dashboard")
async def api_get_depletion_analytics(db: AsyncSession = Depends(get_db)):
    return await get_depletion_analytics(db)
