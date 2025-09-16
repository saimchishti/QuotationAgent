from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.routes.inventory_prediction import predict_daily_stock_depletion
import logging
from fastapi import APIRouter, Depends, HTTPException
from app.db.session import get_db  # ✅ match inventory pattern

router = APIRouter()
logger = logging.getLogger(__name__)

class StockRiskHeatmap:
    def __init__(self):
        self.risk_thresholds = {
            'critical_stock_ratio': 0.1,
            'low_stock_ratio': 0.5,
            'medium_stock_days': 3,
            'high_stock_days': 7
        }

    def calculate_risk_level(self, remaining_stock: float, avg_daily_usage: float) -> str:
        if avg_daily_usage <= 0:
            return "L"
        days_remaining = remaining_stock / avg_daily_usage
        if days_remaining < 1 or remaining_stock <= (avg_daily_usage * self.risk_thresholds['critical_stock_ratio']):
            return "H"
        elif days_remaining <= self.risk_thresholds['medium_stock_days'] or remaining_stock <= (avg_daily_usage * self.risk_thresholds['low_stock_ratio']):
            return "M"
        else:
            return "L"

    def generate_heatmap_data(self, daily_predictions: List[Dict[str, Any]], forecast_days: int = 7) -> List[Dict[str, Any]]:
        heatmap_data = []
        for ingredient_data in daily_predictions:
            ingredient_name = ingredient_data.get('ingredient_name', '')
            avg_daily_usage = ingredient_data.get('avg_daily_usage', 0)
            heatmap_entry = {
                'ingredient_name': ingredient_name,
                'avg_daily_usage': avg_daily_usage,
                'risk_levels': {}
            }
            for day in range(1, forecast_days + 1):
                date_key = f"date_{day}"
                remaining_stock = ingredient_data.get(date_key, 0)
                risk_level = self.calculate_risk_level(remaining_stock, avg_daily_usage)
                heatmap_entry['risk_levels'][f'day_{day}'] = {
                    'risk': risk_level,
                    'remaining_stock': remaining_stock
                }
            heatmap_data.append(heatmap_entry)
        return heatmap_data

    def format_heatmap_response(self, heatmap_data: List[Dict[str, Any]], forecast_days: int = 7) -> Dict[str, Any]:
        day_headers = [f"Day {i}" for i in range(1, forecast_days + 1)]
        ingredients = []
        for ingredient in heatmap_data:
            ingredient_row = {
                'ingredient_name': ingredient['ingredient_name'],
                'avg_daily_usage': ingredient['avg_daily_usage'],
                'days': []
            }
            for day in range(1, forecast_days + 1):
                day_key = f'day_{day}'
                risk_data = ingredient['risk_levels'].get(day_key, {'risk': 'L', 'remaining_stock': 0})
                ingredient_row['days'].append({
                    'day': day,
                    'risk_level': risk_data['risk'],
                    'remaining_stock': risk_data['remaining_stock']
                })
            ingredients.append(ingredient_row)
        ingredients.sort(key=lambda x: (
            sum(1 for day in x['days'] if day['risk_level'] == 'H'),
            sum(1 for day in x['days'] if day['risk_level'] == 'M')
        ), reverse=True)
        return {
            'title': f'Stockout Risk Heatmap (Next {forecast_days} Days)',
            'forecast_days': forecast_days,
            'day_headers': day_headers,
            'ingredients': ingredients,
            'legend': {
                'H': 'High Risk',
                'M': 'Medium Risk',
                'L': 'Low Risk'
            },
            'risk_summary': self._generate_risk_summary(ingredients)
        }

    def _generate_risk_summary(self, ingredients: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_ingredients = len(ingredients)
        high_risk_count = sum(1 for ing in ingredients if any(day['risk_level'] == 'H' for day in ing['days']))
        medium_risk_count = sum(1 for ing in ingredients if any(day['risk_level'] == 'M' for day in ing['days']) and not any(day['risk_level'] == 'H' for day in ing['days']))
        low_risk_count = total_ingredients - high_risk_count - medium_risk_count
        return {
            'total_ingredients': total_ingredients,
            'high_risk_ingredients': high_risk_count,
            'medium_risk_ingredients': medium_risk_count,
            'low_risk_ingredients': low_risk_count,
            'high_risk_percentage': round((high_risk_count / total_ingredients) * 100, 1) if total_ingredients > 0 else 0
        }

# ================================
# ✅ ROUTES — following inventory pattern
# ================================

@router.get("/api/v1/heatmap/inventory-risk", tags=["Inventory Heatmap"], summary="Stock Risk Heatmap (7 Days)")
async def stock_risk_heatmap(db: AsyncSession = Depends(get_db)):
    try:
        forecast_days = 7
        daily_predictions = await predict_daily_stock_depletion(db, forecast_days)
        generator = StockRiskHeatmap()
        heatmap_data = generator.generate_heatmap_data(daily_predictions, forecast_days)
        return generator.format_heatmap_response(heatmap_data, forecast_days)
    except Exception as e:
        logger.error(f"Error generating stock risk heatmap: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/v1/heatmap/inventory-risk-simple", tags=["Inventory Heatmap"], summary="Simple Stock Risk Matrix (7 Days)")
async def stock_risk_heatmap_simple(db: AsyncSession = Depends(get_db)):
    try:
        forecast_days = 7
        daily_predictions = await predict_daily_stock_depletion(db, forecast_days)
        generator = StockRiskHeatmap()

        matrix_data = []
        for ingredient_data in daily_predictions:
            ingredient_name = ingredient_data.get('ingredient_name', '')
            avg_daily_usage = ingredient_data.get('avg_daily_usage', 0)

            row = {
                'ingredient': ingredient_name,
                'risk_levels': []
            }

            for day in range(1, forecast_days + 1):
                date_key = f"date_{day}"
                remaining_stock = ingredient_data.get(date_key, 0)
                risk_level = generator.calculate_risk_level(remaining_stock, avg_daily_usage)
                row['risk_levels'].append(risk_level)

            matrix_data.append(row)

        matrix_data.sort(key=lambda x: (
            x['risk_levels'].count('H'),
            x['risk_levels'].count('M')
        ), reverse=True)

        return {
            'title': 'Stockout Risk Heatmap (Next 7 Days)',
            'forecast_days': forecast_days,
            'heatmap_matrix': matrix_data,
            'legend': {
                'H': 'High Risk',
                'M': 'Medium Risk',
                'L': 'Low Risk'
            }
        }
    except Exception as e:
        logger.error(f"Error generating simple heatmap matrix: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
