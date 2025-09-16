from fastapi import APIRouter, Depends, Query
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, Session
from sqlalchemy import func
from datetime import datetime, timedelta, date
from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
import pandas as pd
from datetime import datetime, timedelta
from prophet import Prophet
import pandas as pd
from db.session import AsyncSessionLocal, get_db
from db.models import (
    Wastage, Menu, MenuIngredient,
    Inventory, CustomerOrder,
    CustomerOrderMenuMapping
)
from db.models import (
    Menu,
    MenuPriceHistory,
    CustomerOrder,
    CustomerOrderMenuMapping
)
router = APIRouter()



@router.get("/api/most-reordered-dishes", tags=["Menu Optimization"])
async def most_reordered_dishes(db: AsyncSession = Depends(get_db)):
    try:
        # Subquery: Get customers who ordered the same dish more than once
        subquery = (
            select(
                CustomerOrderMenuMapping.menu_id,
                CustomerOrder.customer_id,
                func.count().label("order_count")
            )
            .join(CustomerOrder, CustomerOrder.id == CustomerOrderMenuMapping.customer_order_id)
            .group_by(CustomerOrderMenuMapping.menu_id, CustomerOrder.customer_id)
            .having(func.count() > 1)
            .subquery()
        )

        # Main query: Count how many customers reordered each menu item and join with menu name
        query = (
            select(
                Menu.id.label("menu_id"),
                Menu.name.label("menu_name"),
                func.count().label("reorder_count")
            )
            .join(subquery, subquery.c.menu_id == Menu.id)
            .group_by(Menu.id, Menu.name)
            .order_by(func.count().desc())
        )

        result = await db.execute(query)
        rows = result.fetchall()

        return [
            {
                "menu_id": row.menu_id,
                "menu_name": row.menu_name,
                "reorder_count": row.reorder_count
            }
            for row in rows
        ]

    except Exception as e:
        return {"error": str(e)}

# 🔹 Contribution Margin Distribution API
@router.get("/api/contribution-margins", tags=["Dynamic Pricing"])
async def contribution_margin_distribution():
    async with AsyncSessionLocal() as session:
        try:
            query = select(Menu).options(
                joinedload(Menu.ingredients).joinedload(MenuIngredient.ingredient)
            )
            result = await session.execute(query)
            menus = result.scalars().all()

            bins = {
                "0-20%": 0,
                "20-30%": 0,
                "30-40%": 0,
                "40-50%": 0,
                "50%+": 0
            }

            for menu in menus:
                if not menu.ingredients:
                    continue

                total_cost = 0.0
                for mi in menu.ingredients:
                    if mi.ingredient and mi.quantity:
                        price = extract_numeric_price(mi.ingredient.price_per_unit)
                        quantity = float(mi.quantity)
                        total_cost += price * quantity

                if menu.price and total_cost > 0:
                    margin = ((menu.price - total_cost) / menu.price) * 100
                    if margin < 20:
                        bins["0-20%"] += 1
                    elif margin < 30:
                        bins["20-30%"] += 1
                    elif margin < 40:
                        bins["30-40%"] += 1
                    elif margin < 50:
                        bins["40-50%"] += 1
                    else:
                        bins["50%+"] += 1

            return {"data": [{"range": k, "count": v} for k, v in bins.items()]}

        except Exception as e:
            return {"error": str(e)}


# 🔹 Orders Impact API
from sqlalchemy import select, func, case
from sqlalchemy.orm import joinedload



from sqlalchemy import select, func, case, cast, Date
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, cast, TIMESTAMP
from datetime import datetime, timedelta


@router.get("/api/orders-impact", tags=["Menu Optimization"])
async def get_orders_impact(db: AsyncSession = Depends(get_db)):
    try:
        # Get latest price change per menu item
        subquery = (
            select(
                MenuPriceHistory.menu_id,
                func.max(MenuPriceHistory.effective_date).label("latest_change")
            )
            .group_by(MenuPriceHistory.menu_id)
            .subquery()
        )

        # Join to get latest effective date per menu item
        query = (
            select(
                Menu.name,
                MenuPriceHistory.menu_id,
                MenuPriceHistory.effective_date
            )
            .join(MenuPriceHistory, Menu.id == MenuPriceHistory.menu_id)
            .join(subquery, MenuPriceHistory.menu_id == subquery.c.menu_id)
            .where(MenuPriceHistory.effective_date == subquery.c.latest_change)
        )

        result = await db.execute(query)
        recent_changes = result.fetchall()

        response = []
        for row in recent_changes:
            menu_id = row.menu_id
            name = row.name
            effective_date = row.effective_date

            # Query order counts before and after price change using cast
            count_query = (
                select(
                    func.sum(
                        case(
                            (cast(CustomerOrder.delivery_datetime, TIMESTAMP) < effective_date, 1),
                            else_=0
                        )
                    ).label("before"),
                    func.sum(
                        case(
                            (cast(CustomerOrder.delivery_datetime, TIMESTAMP) >= effective_date, 1),
                            else_=0
                        )
                    ).label("after")
                )
                .select_from(CustomerOrder)
                .join(CustomerOrderMenuMapping, CustomerOrder.id == CustomerOrderMenuMapping.customer_order_id)
                .where(CustomerOrderMenuMapping.menu_id == menu_id)
            )

            count_result = await db.execute(count_query)
            before, after = count_result.fetchone()

            response.append({
                "item": name,
                "before": int(before or 0),
                "after": int(after or 0)
            })

        return {"data": response}

    except Exception as e:
        return {"error": str(e)}


# 🔹 Wastage Trend Over Time API
@router.get("/api/waste-trend", tags=["Menu Optimization"])
async def waste_reduction_trend(
    days: int = Query(30, description="Number of days to look back for trend analysis")
):
    async with AsyncSessionLocal() as session:
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            query = select(Wastage.created_at, Wastage.wastage_qty).where(Wastage.created_at >= start_date)
            result = await session.execute(query)
            rows = result.fetchall()

            if not rows:
                return {"trend": [], "message": "No wastage data available for the selected period."}

            df = pd.DataFrame(rows, columns=['created_at', 'wastage_qty'])
            df['created_at'] = pd.to_datetime(df['created_at'])
            df['date'] = df['created_at'].dt.date

            trend = df.groupby('date')['wastage_qty'].sum().reset_index().sort_values('date')

            response = [
                {"date": str(row['date']), "total_waste": round(row['wastage_qty'], 2)}
                for _, row in trend.iterrows()
            ]

            return {"trend": response}

        except Exception as e:
            return {"error": str(e)}


# 🔧 Helper Function
def extract_numeric_price(price_str):
    try:
        return float(''.join(c for c in price_str if c.isdigit() or c == '.'))
    except:
        return 0.0



@router.get("/api/total-orders-after-latest-price-change", tags=["Menu Optimization"])
async def total_orders_after_latest_price_change(
    db: AsyncSession = Depends(get_db)
):
    try:
        # Get the latest effective date from menu_price_history
        subquery = select(MenuPriceHistory.effective_date).order_by(MenuPriceHistory.effective_date.desc()).limit(1)
        result = await db.execute(subquery)
        latest_date = result.scalar()

        if not latest_date:
            return {"message": "No effective date found in menu_price_history."}

        # Count orders after the latest effective date
        query = (
            select(func.count())
            .select_from(CustomerOrder)
            .where(cast(CustomerOrder.delivery_datetime, TIMESTAMP) >= latest_date)
        )
        result = await db.execute(query)
        total = result.scalar()

        return {
            "latest_effective_date": latest_date.isoformat(),
            "total_orders_after": total
        }

    except Exception as e:
        return {"error": str(e)}
    
    



def parse_price_per_unit(price_str):
    try:
        numeric = str(price_str).split()[0]
        return float(numeric)
    except Exception:
        return 0.0


@router.get("/api/sales-profitability-trend", tags=["Menu Optimization"])
async def dish_sales_profitability_trend(
    days: int = Query(10, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db)
):
    try:
        start_date = datetime.utcnow().date() - timedelta(days=days)

        # 1. Fetch orders joined with menu items
        query = (
            select(
                cast(CustomerOrder.delivery_datetime, Date).label("order_date"),
                Menu.id.label("menu_id"),
                Menu.name.label("menu_name"),
                Menu.price.label("menu_price"),
                CustomerOrder.id.label("order_id")
            )
            .select_from(CustomerOrder)
            .join(CustomerOrderMenuMapping, CustomerOrder.id == CustomerOrderMenuMapping.customer_order_id)
            .join(Menu, Menu.id == CustomerOrderMenuMapping.menu_id)
            .where(cast(CustomerOrder.delivery_datetime, Date) >= start_date)
        )
        result = await db.execute(query)
        rows = result.fetchall()

        if not rows:
            return {"trend": []}

        df = pd.DataFrame(rows, columns=["order_date", "menu_id", "menu_name", "menu_price", "order_id"])

        # 2. Fetch menu ingredient cost mappings
        menu_ids = df["menu_id"].unique().tolist()
        ingredient_query = (
            select(MenuIngredient.menu_id, MenuIngredient.quantity, Inventory.price_per_unit)
            .join(Inventory, Inventory.id == MenuIngredient.ingredient_id)
            .where(MenuIngredient.menu_id.in_(menu_ids))
        )
        ingredient_result = await db.execute(ingredient_query)
        ingredient_data = ingredient_result.fetchall()

        # Build cost lookup
        cost_map = {}
        for menu_id, quantity, price_str in ingredient_data:
            price = parse_price_per_unit(price_str)
            qty = float(quantity or 0)
            total_cost = cost_map.get(menu_id, 0.0)
            cost_map[menu_id] = total_cost + (price * qty)

        # Add cost & margin columns to df
        df["cost"] = df["menu_id"].map(cost_map)
        df["margin_percent"] = ((df["menu_price"] - df["cost"]) / df["menu_price"]) * 100

        # Group by date
        summary = df.groupby("order_date").agg(
            total_orders=pd.NamedAgg(column="order_id", aggfunc="count"),
            avg_margin_percent=pd.NamedAgg(column="margin_percent", aggfunc="mean")
        ).reset_index()

        # Format response
        trend = [
            {
                "date": str(row["order_date"]),
                "total_orders": int(row["total_orders"]),
                "avg_margin_percent": round(row["avg_margin_percent"], 2)
            }
            for _, row in summary.iterrows()
        ]

        return {"trend": trend}

    except Exception as e:
        return {"error": str(e)}
    
    
from fastapi import APIRouter
from services.dynamic_pricing_data import get_dynamic_pricing_base_data
from sqlalchemy.sql import func
import numpy as np


@router.get("/analytics/action-distribution", tags=["Menu Optimization"])
async def action_distribution():
    # Fetch demand, supply, price, ingredient data via your data provider
    df = await get_dynamic_pricing_base_data()

    if df.empty:
        return {"error": "No data available"}

    # Demand per dish (number of orders)
    demand_df = df.groupby("dish_name").agg(
        order_count=("order_price", "count"),
        current_price=("current_price", "first")
    ).reset_index()

    # Supply per dish (average stock)
    supply_df = df.groupby("dish_name").agg(
        avg_stock=("current_stock", "mean")
    ).reset_index()

    # Merge demand and supply info
    merged_df = demand_df.merge(supply_df, on="dish_name")

    # Normalize demand and stock scores
    merged_df["demand_score"] = (merged_df["order_count"] - merged_df["order_count"].mean()) / merged_df["order_count"].std(ddof=0)
    merged_df["supply_score"] = (merged_df["avg_stock"] - merged_df["avg_stock"].mean()) / merged_df["avg_stock"].std(ddof=0)

    # Action category counts
    actions = {
        "Promote": 0,
        "Discount": 0,
        "Remove": 0,
        "Maintain": 0
    }

    for _, row in merged_df.iterrows():
        if row["demand_score"] > 0.5 and row["supply_score"] > 0.5:
            actions["Promote"] += 1
        elif row["demand_score"] < -0.5 and row["supply_score"] > 0.5:
            actions["Discount"] += 1
        elif row["demand_score"] < -0.5 and row["supply_score"] < -0.5:
            actions["Remove"] += 1
        else:
            actions["Maintain"] += 1

    total = sum(actions.values())

    if total == 0:
        return {"error": "No dishes available for classification"}

    # Convert counts to percentages for chart labels
    percentages = {
        k: round((v / total) * 100, 2)
        for k, v in actions.items()
    }

    # Final response payload for the graph
    return {
        "labels": list(actions.keys()),
        "percentages": list(percentages.values())
    }
