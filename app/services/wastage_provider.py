# tools/inventory_tools.py
from sqlalchemy import select, func, Date, cast
from app.db.session import RestaurantSessionLocal
from app.db.models import Wastage, InventoryCase1, CustomerOrder

async def get_daily_wastage_log(business_owner_id: int):
    async with RestaurantSessionLocal() as session:
        query = (
            select(
                func.date(Wastage.created_at).label("date"),
                InventoryCase1.name.label("ingredient_name"),
                func.sum(Wastage.wastage_qty).label("total_wastage_qty"),
                Wastage.unit_type
            )
            .join(InventoryCase1, InventoryCase1.id == Wastage.ingredient_id)
            .where(Wastage.business_owner_id == business_owner_id)
            .group_by(func.date(Wastage.created_at), InventoryCase1.name, Wastage.unit_type)
            .order_by(func.date(Wastage.created_at).desc())
        )
        result = await session.execute(query)
        return result.mappings().all()


async def get_order_to_waste_correlation(business_owner_id: int):
        
    async with RestaurantSessionLocal() as session:    
        customer_orders_per_day = (
            select(
                cast(CustomerOrder.created_at, Date).label("date"),
                func.count(CustomerOrder.id).label("total_orders")
            )
            .where(CustomerOrder.business_owner_id == business_owner_id)
            .group_by(cast(CustomerOrder.created_at, Date))
            .subquery()
        )

        wastage_per_day = (
            select(
                cast(Wastage.created_at, Date).label("date"),
                func.sum(Wastage.wastage_qty).label("total_waste")
            )
            .where(Wastage.business_owner_id == business_owner_id)
            .group_by(cast(Wastage.created_at, Date))
            .subquery()
        )

        stmt = (
            select(
                customer_orders_per_day.c.date,
                customer_orders_per_day.c.total_orders,
                wastage_per_day.c.total_waste
            )
            .outerjoin(wastage_per_day, customer_orders_per_day.c.date == wastage_per_day.c.date)
            .order_by(customer_orders_per_day.c.date.desc())
        )

        result = await session.execute(stmt)
        data = [
            {
                "date": row.date,
                "total_orders": row.total_orders,
                "total_waste": float(row.total_waste or 0)
            }
            for row in result
        ]
        return data