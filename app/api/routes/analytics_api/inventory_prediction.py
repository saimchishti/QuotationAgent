from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from db.session import get_db
from core.constants import business_owner_id
from services.dataprovider_inventory import (
    get_inventory_usage_sma,
    get_monthly_usage_forecast,
    get_deliveries_vs_depletion,
    get_menu_ingredients
)

router = APIRouter()

async def predict_stock_depletion(session: AsyncSession):
    days = 365
    raw_data = await get_inventory_usage_sma(session, business_owner_id, days=days)

    forecast = []
    for row in raw_data:
        total_used = row.total_used or 0
        avg_daily_usage = total_used / days
        predicted_days_left = (row.current_stock or 0) / avg_daily_usage if avg_daily_usage else float('inf')
        reorder_suggestion = "Yes" if predicted_days_left < 7 else "No"

        forecast.append({
            "ingredient_name": row.ingredient_name,
            "current_stock": row.current_stock,
            "avg_daily_usage": round(avg_daily_usage, 2),
            "predicted_days_left": round(predicted_days_left, 2),
            "reorder_suggestion": reorder_suggestion
        })

    return forecast

async def predict_daily_stock_depletion(session: AsyncSession, forecast_days: int = 7):
    days = 365
    raw_data = await get_inventory_usage_sma(session, business_owner_id, days=days)
    base_date = datetime.now().date()

    daily_forecasts = []
    for row in raw_data:
        total_used = row.total_used or 0
        avg_daily_usage = total_used / days
        current_stock = row.current_stock or 0

        forecast_item = {
            "ingredient_name": row.ingredient_name,
            "current_stock": current_stock,
            "avg_daily_usage": round(avg_daily_usage, 2)
        }

        remaining_stock = current_stock
        for day in range(1, forecast_days + 1):
            remaining_stock = max(0, remaining_stock - avg_daily_usage)
            forecast_item[f"date_{day}"] = round(remaining_stock, 2)

        daily_forecasts.append(forecast_item)

    return daily_forecasts

async def predict_daily_stock_depletion_with_dates(session: AsyncSession, forecast_days: int = 7):
    days = 365
    raw_data = await get_inventory_usage_sma(session, business_owner_id, days=days)
    base_date = datetime.now().date()

    daily_forecasts = []
    for row in raw_data:
        total_used = row.total_used or 0
        avg_daily_usage = total_used / days
        current_stock = row.current_stock or 0

        forecast_item = {
            "ingredient_name": row.ingredient_name,
            "current_stock": current_stock,
            "avg_daily_usage": round(avg_daily_usage, 2)
        }

        remaining_stock = current_stock
        for day in range(1, forecast_days + 1):
            remaining_stock = max(0, remaining_stock - avg_daily_usage)
            forecast_date = base_date + timedelta(days=day)
            date_key = forecast_date.strftime("%Y-%m-%d")
            forecast_item[date_key] = round(remaining_stock, 2)

        daily_forecasts.append(forecast_item)

    return daily_forecasts

async def deliveries_vs_depletion(session: AsyncSession):
    data = await get_deliveries_vs_depletion(session, business_owner_id)
    results = []

    for row in data:
        results.append({
            "ingredient_name": row.ingredient_name,
            "total_delivered": row.total_delivered,
            "total_used": row.total_used,
            "net_stock_change": round(row.total_delivered - row.total_used, 2)
        })

    return results

from services.dataprovider import get_training_data
from prophet import Prophet
import pandas as pd

async def predict_item_sales_amount_forecast_full():
    df = await get_training_data(business_owner_id)

    if df.empty or 'menu_name' not in df.columns or 'price' not in df.columns:
        return {"error": "Insufficient data: 'menu_name' and 'price' columns required."}

    df['ds'] = pd.to_datetime(df['delivery_datetime']).dt.tz_localize(None)
    df = df.sort_values('ds')
    last_date = df['ds'].max()

    forecast_results = []

    for dish in df['menu_name'].unique():
        dish_df = df[df['menu_name'] == dish][['ds', 'quantity', 'price']].copy()

        if len(dish_df) < 2:
            continue

        dish_df.rename(columns={'quantity': 'y'}, inplace=True)

        try:
            model = Prophet(daily_seasonality=True, weekly_seasonality=True)
            model.fit(dish_df[['ds', 'y']])
            future = model.make_future_dataframe(periods=7, freq='D')
            forecast = model.predict(future)
            next_7 = forecast[forecast['ds'] > last_date]

            total_quantity_forecast = next_7['yhat'].clip(lower=0).sum()
            avg_price = dish_df['price'].mean()

            total_sales_amount = total_quantity_forecast * avg_price

            forecast_results.append({
                "menu_name": dish,
                "forecast_quantity": int(total_quantity_forecast),
                "average_price": round(avg_price, 2),
                "forecast_sales_amount": round(total_sales_amount, 2)
            })
        except Exception as e:
            print(f"⚠️ Could not forecast for item: {dish} → {str(e)}")
            continue

    forecast_results.sort(key=lambda x: x['forecast_sales_amount'], reverse=True)

    return forecast_results

from sqlalchemy import select
from collections import defaultdict
from db.models import BusinessOwnerInventory, InventoryCase1

async def predict_inventory_depletion_from_sales(
    session: AsyncSession,
    business_owner_id: int,
    forecast_days: int = 7,
    reorder_threshold: int = 7
):
    sales_forecast = await predict_item_sales_amount_forecast_full()
    if "error" in sales_forecast:
        return sales_forecast

    menu_ingredients = await get_menu_ingredients(session)
    if not menu_ingredients:
        return {"error": "No menu ingredient mapping found."}

    def parse_float(value):
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    # Map menu_name → ingredient_name, quantity_per_item
    ingredient_usage_map = defaultdict(list)
    for row in menu_ingredients:
        ingredient_usage_map[row.menu_name].append({
            "ingredient_name": row.ingredient_name,
            "quantity_per_item": row.quantity
        })

    # Compute total depletion
    depletion_summary = defaultdict(float)
    for item in sales_forecast:
        menu_name = item["menu_name"]
        forecast_qty = item["forecast_quantity"]

        if menu_name not in ingredient_usage_map:
            continue

        for ing in ingredient_usage_map[menu_name]:
            quantity_per_item = parse_float(ing["quantity_per_item"])
            depletion_summary[ing["ingredient_name"]] += forecast_qty * quantity_per_item

    # Fetch current stock using BusinessOwnerInventory joined with InventoryCase1
    stock_result = await session.execute(
        select(
            InventoryCase1.name,
            BusinessOwnerInventory.stock_quantity
        )
        .select_from(BusinessOwnerInventory)
        .join(InventoryCase1, BusinessOwnerInventory.inventory_id == InventoryCase1.id)
        .where(BusinessOwnerInventory.business_owner_id == business_owner_id)
    )
    stock_data = {row.name: row.stock_quantity for row in stock_result.fetchall()}

    # Compute final predictions
    final_result = []
    for ingredient_name, total_depletion in depletion_summary.items():
        current_stock = stock_data.get(ingredient_name, 0)
        avg_daily_usage = total_depletion / forecast_days if forecast_days else 0
        predicted_days_left = current_stock / avg_daily_usage if avg_daily_usage else float('inf')
        reorder_suggestion = "Yes" if predicted_days_left < reorder_threshold else "No"

        final_result.append({
            "ingredient_name": ingredient_name,
            "current_stock": current_stock,
            "avg_daily_usage": round(avg_daily_usage, 2),
            "predicted_days_left": round(predicted_days_left, 2),
            "reorder_suggestion": reorder_suggestion
        })

    final_result.sort(key=lambda x: x["predicted_days_left"])
    return final_result


async def forecast_inventory_rulebase(session: AsyncSession, ingredient_id: int):
    return await get_monthly_usage_forecast(session, business_owner_id, ingredient_id)

@router.get("/stock-depletion", tags=["Stock Prediction"])
async def get_stock_depletion(db: AsyncSession = Depends(get_db)):
    return await predict_stock_depletion(db)

@router.get("/daily-stock-depletion", tags=["Stock Prediction"])
async def get_daily_stock_depletion(forecast_days: int = 7, db: AsyncSession = Depends(get_db)):
    return await predict_daily_stock_depletion(db, forecast_days)

@router.get("/daily-stock-depletion-dates", tags=["Stock Prediction"])
async def get_daily_stock_depletion_with_dates(forecast_days: int = 7, db: AsyncSession = Depends(get_db)):
    return await predict_daily_stock_depletion_with_dates(db, forecast_days)

@router.get("/inventory-rulebase-forecast", tags=["Stock Prediction"])
async def get_inventory_rulebase_forecast(ingredient_id: int, db: AsyncSession = Depends(get_db)):
    return await forecast_inventory_rulebase(db, ingredient_id)

@router.get("/deliveries-vs-depletion", tags=["Stock Prediction"])
async def get_deliveries_vs_depletion_api(db: AsyncSession = Depends(get_db)):
    return await deliveries_vs_depletion(db)

@router.get("/item-sales-amount-forecast", tags=["Stock Prediction"])
async def get_item_sales_amount_forecast():
    return await predict_item_sales_amount_forecast_full()

@router.get("/inventory-depletion-from-sales", tags=["Stock Prediction"])
async def get_inventory_depletion_from_sales(db: AsyncSession = Depends(get_db)):
    return await predict_inventory_depletion_from_sales(db)