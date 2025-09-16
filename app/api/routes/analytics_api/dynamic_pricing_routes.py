from fastapi import APIRouter
from services.dynamic_pricing_data import get_dynamic_pricing_base_data
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from db.session import AsyncSessionLocal
from db.models import CustomerOrder
import numpy as np
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import datetime, timedelta
from db.session import get_db
from sqlalchemy import select, func, cast, Date
from sqlalchemy import select, func, cast, Date, DateTime
from fastapi import APIRouter, Query


from db.models import (
    CustomerOrder,
    CustomerOrderMenuMapping,
    Menu,
    MenuIngredient,
    Inventory,
    MenuPriceHistory
)

router = APIRouter()

# Dynamic Pricing Endpoint
@router.get("/dynamic-pricing", tags=["Dynamic Pricing"])
async def dynamic_pricing(business_owner_id: int = Query(..., description="Business owner ID to filter data")):
    df = await get_dynamic_pricing_base_data(business_owner_id)
    if df.empty:
        return {"error": "No data available"}

    demand_df = df.groupby("dish_name").agg(
        order_count=("order_price", "count"),
        current_price=("current_price", "first")
    ).reset_index()

    supply_df = df.groupby("dish_name").agg(
        avg_stock=("current_stock", "mean"),
        ingredient_count=("ingredient_name", "nunique")
    ).reset_index()

    merged = demand_df.merge(supply_df, on="dish_name")
    merged["demand_score"] = (merged["order_count"] - merged["order_count"].mean()) / merged["order_count"].std()
    merged["supply_score"] = (merged["avg_stock"] - merged["avg_stock"].mean()) / merged["avg_stock"].std()

    result = []
    for _, row in merged.iterrows():
        change, reason, confidence = 0, "", "70%"
        if row["demand_score"] > 0.5 and row["supply_score"] < -0.5:
            change, reason, confidence = 0.10, "High demand, low supply", "90%"
        elif row["demand_score"] < -0.5 and row["supply_score"] > 0.5:
            change, reason, confidence = -0.10, "Low demand, high supply", "90%"
        elif row["demand_score"] > 0:
            change, reason, confidence = 0.05, "Moderate demand increase", "80%"
        elif row["demand_score"] < 0:
            change, reason, confidence = -0.05, "Slight demand drop", "80%"
        else:
            reason = "Stable demand and supply"

        new_price = row["current_price"] * (1 + change)
        result.append({
            "dish": row["dish_name"],
            "current_price": round(row["current_price"], 2),
            "suggested_price": round(new_price, 2),
            "change_percent": round(change * 100, 2),
            "reason": reason,
            "confidence": confidence,
            "last_updated": "Just now"
        })

    return result

# Revenue Trend Endpoint
from sqlalchemy import extract

from sqlalchemy import extract, cast, TIMESTAMP

@router.get("/analytics/revenue-trend", tags=["Dynamic Pricing"])
async def revenue_trend():
    async with AsyncSessionLocal() as session:
        query = (
            select(
                extract("dow", cast(CustomerOrder.delivery_datetime, TIMESTAMP)).label("day_of_week"),
                func.sum(CustomerOrder.price).label("total_revenue")
            )
            .group_by("day_of_week")
            .order_by("day_of_week")
        )
        result = await session.execute(query)
        data = result.fetchall()

        day_map = {
            0: "Sun",
            1: "Mon",
            2: "Tue",
            3: "Wed",
            4: "Thu",
            5: "Fri",
            6: "Sat"
        }

        labels = [day_map[int(row.day_of_week)] for row in data]
        revenues = [row.total_revenue for row in data]

        return {"labels": labels, "revenues": revenues}


from sqlalchemy import extract, literal

from sqlalchemy import extract, literal, cast, TIMESTAMP

@router.get("/analytics/margin-performance", tags=["Dynamic Pricing"])
async def margin_performance():
    async with AsyncSessionLocal() as session:
        query = (
            select(
                extract("dow", cast(CustomerOrder.delivery_datetime, TIMESTAMP)).label("day_of_week"),
                func.sum(CustomerOrder.price * literal(0.20)).label("total_margin")
            )
            .group_by("day_of_week")
            .order_by("day_of_week")
        )
        result = await session.execute(query)
        data = result.fetchall()

        day_map = {
            0: "Sun",
            1: "Mon",
            2: "Tue",
            3: "Wed",
            4: "Thu",
            5: "Fri",
            6: "Sat"
        }

        labels = [day_map[int(row.day_of_week)] for row in data]
        margins = [row.total_margin for row in data]

        return {"labels": labels, "margins": margins}
from fastapi import APIRouter
from services.dynamic_pricing_data import get_dynamic_pricing_base_data
import numpy as np



@router.get("/analytics/action-distribution", tags=["Dynamic Pricing"])
async def action_distribution():
    df = await get_dynamic_pricing_base_data()
    if df.empty:
        return {"error": "No data available"}

    demand_df = df.groupby("dish_name").agg(
        order_count=("order_price", "count"),
        current_price=("current_price", "first")
    ).reset_index()

    supply_df = df.groupby("dish_name").agg(
        avg_stock=("current_stock", "mean")
    ).reset_index()

    merged = demand_df.merge(supply_df, on="dish_name")

    # Normalize scores
    merged["demand_score"] = (merged["order_count"] - merged["order_count"].mean()) / merged["order_count"].std()
    merged["supply_score"] = (merged["avg_stock"] - merged["avg_stock"].mean()) / merged["avg_stock"].std()

    actions = {"Promote": 0, "Discount": 0, "Remove": 0, "Maintain": 0}

    for _, row in merged.iterrows():
        if row["demand_score"] > 0.5 and row["supply_score"] > 0.5:
            actions["Promote"] += 1
        elif row["demand_score"] < -0.5 and row["supply_score"] > 0.5:
            actions["Discount"] += 1
        elif row["demand_score"] < -0.5 and row["supply_score"] < -0.5:
            actions["Remove"] += 1
        else:
            actions["Maintain"] += 1

    total = sum(actions.values())
    percentages = {k: round((v / total) * 100, 2) for k, v in actions.items()}

    return {
        "actions": actions,
        "percentages": percentages
    }
    
    
@router.get("/post-change-impact", tags=["Dynamic Pricing"])
async def post_change_impact(db: AsyncSession = Depends(get_db)):
    try:
        # Get latest price change date
        latest_date_result = await db.execute(
            select(MenuPriceHistory.effective_date)
            .order_by(MenuPriceHistory.effective_date.desc())
            .limit(1)
        )
        latest_date = latest_date_result.scalar()
        if not latest_date:
            return {"error": "No price change history found."}

        # Compute ingredient cost per dish
        async def compute_cost(menu_id: int):
            result = await db.execute(
                select(MenuIngredient.quantity, Inventory.price_per_unit)
                .join(Inventory, Inventory.id == MenuIngredient.ingredient_id)
                .where(MenuIngredient.menu_id == menu_id)
            )
            cost = 0.0
            for qty, price_str in result:
                try:
                    numeric_price = float(''.join(filter(str.isdigit, str(price_str))) or 0)
                    cost += float(qty) * numeric_price
                except:
                    continue
            return cost

        # Get order data between two dates
        async def get_order_data(start_date, end_date):
            result = await db.execute(
                select(
                    cast(CustomerOrder.delivery_datetime, Date).label("date"),
                    Menu.id,
                    Menu.name,
                    Menu.price,
                    func.count(CustomerOrderMenuMapping.id).label("quantity")
                )
                .join(CustomerOrderMenuMapping, CustomerOrder.id == CustomerOrderMenuMapping.customer_order_id)
                .join(Menu, CustomerOrderMenuMapping.menu_id == Menu.id)
                .where(cast(CustomerOrder.delivery_datetime, DateTime) >= start_date)
                .where(cast(CustomerOrder.delivery_datetime, DateTime) < end_date)
                .group_by(
                    cast(CustomerOrder.delivery_datetime, Date),
                    Menu.id,
                    Menu.name,
                    Menu.price
                )
            )
            return result.fetchall()

        today = datetime.utcnow().date()
        post_data = await get_order_data(latest_date, today)
        pre_data = await get_order_data(latest_date - timedelta(days=7), latest_date)

        # Aggregate revenue and quantities per weekday
        def aggregate(data):
            day_data = {}
            for row in data:
                day = row.date.strftime('%A')
                menu_id = row.id
                qty = row.quantity or 0
                price = float(row.price or 0)
                revenue = qty * price

                if day not in day_data:
                    day_data[day] = {"revenue": 0, "cost": 0}
                day_data[day]["revenue"] += revenue
                day_data[day].setdefault("menu_items", {})
                day_data[day]["menu_items"][menu_id] = day_data[day]["menu_items"].get(menu_id, 0) + qty

            return day_data

        pre_agg = aggregate(pre_data)
        post_agg = aggregate(post_data)

        # Compute post-change margins
        for day, data in post_agg.items():
            margin = 0
            for menu_id, qty in data.get("menu_items", {}).items():
                cost = await compute_cost(menu_id)
                menu_price = next((r.price for r in post_data if r.id == menu_id), 0)
                margin += (menu_price - cost) * qty
            data["margin"] = int(margin)

        total_pre_rev = sum([v["revenue"] for v in pre_agg.values()])
        total_post_rev = sum([v["revenue"] for v in post_agg.values()])
        revenue_increase = total_post_rev - total_pre_rev

        total_pre_margin = 0
        for day, data in pre_agg.items():
            for menu_id, qty in data.get("menu_items", {}).items():
                cost = await compute_cost(menu_id)
                price = next((r.price for r in pre_data if r.id == menu_id), 0)
                total_pre_margin += (price - cost) * qty

        total_post_margin = sum([v["margin"] for v in post_agg.values()])
        margin_improvement = ((total_post_margin - total_pre_margin) / total_pre_margin * 100) if total_pre_margin else 0
        success_rate = int((total_post_rev > total_pre_rev and total_post_margin > total_pre_margin) * 100)

        # Build weekday trend
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        trend = []
        for day in days_order:
            trend.append({
                "day": day,
                "revenue": int(post_agg.get(day, {}).get("revenue", 0)),
                "margin": int(post_agg.get(day, {}).get("margin", 0))
            })

        return {
            "revenue_increase": int(revenue_increase),
            "margin_improvement": round(margin_improvement, 2),
            "success_rate": f"{success_rate}%",
            "trend": trend
        }

    except Exception as e:
        return {"error": str(e)}