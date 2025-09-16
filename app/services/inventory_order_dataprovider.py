from sqlalchemy import select, func, case
from app.db.models import ( OrderCase1, 
StatusCase1Type, 
VendorCase1, 
OrderCase1InventoryMapping, 
InventoryCase1,
IngredientCase1Type ,
OrderCase1InventoryMapping,
)
from app.db.session import RestaurantSessionLocal
from sqlalchemy import literal_column


async def get_purchase_orders(business_owner_id: int):
    async with RestaurantSessionLocal() as session:
        stmt = (
            select(
                OrderCase1.id.label("order_id"),
                VendorCase1.name.label("vendor_name"),
                StatusCase1Type.value.label("status"),
                OrderCase1.created_at,
                OrderCase1.delivery_date,
            )
            .join(VendorCase1, OrderCase1.vendor_id == VendorCase1.id)
            .join(StatusCase1Type, OrderCase1.status_type_id == StatusCase1Type.id)
            .where(OrderCase1.business_owner_id == business_owner_id)
            .order_by(OrderCase1.created_at.desc())
        )

        result = await session.execute(stmt)
        return [dict(row._mapping) for row in result.fetchall()]


async def get_supplier_order_history(business_owner_id: int):
    async with RestaurantSessionLocal() as session:
        stmt = (
            select(
                OrderCase1.id.label("order_id"),
                OrderCase1.created_at.label("order_date"),
                OrderCase1.delivery_date.label("expected_delivery_date"),
                VendorCase1.name.label("vendor_name"),
                OrderCase1InventoryMapping.inventory_id.label("inventory_id"),
                InventoryCase1.name.label("inventory_name"),
                OrderCase1InventoryMapping.quantity.label("quantity"),
            )
            .join(VendorCase1, OrderCase1.vendor_id == VendorCase1.id)
            .join(OrderCase1InventoryMapping, OrderCase1.id == OrderCase1InventoryMapping.order_id)
            .join(InventoryCase1, InventoryCase1.id == OrderCase1InventoryMapping.inventory_id)
            .where(OrderCase1.business_owner_id == business_owner_id)
            .order_by(OrderCase1.created_at.desc())
        )

        result = await session.execute(stmt)
        rows = result.mappings().all()

        orders = {}
        for row in rows:
            order_id = row["order_id"]
            if order_id not in orders:
                orders[order_id] = {
                    "order_id": order_id,
                    "vendor_name": row["vendor_name"],
                    "order_date": row["order_date"],
                    "expected_delivery_date": row["expected_delivery_date"],
                    "items": []
                }

            orders[order_id]["items"].append({
                "inventory_id": row["inventory_id"],
                "inventory_name": row["inventory_name"],
                "quantity": row["quantity"],
            })

        return list(orders.values())
    

from sqlalchemy import select, cast, Float, func
from sqlalchemy.ext.asyncio import AsyncSession

async def get_cost_per_order_breakdown(business_owner_id: int):
    async with RestaurantSessionLocal() as session:
        query = select(
            OrderCase1.id.label("order_id"),
            VendorCase1.name.label("vendor_name"),
            OrderCase1InventoryMapping.inventory_id,
            InventoryCase1.name.label("inventory_name"),
            InventoryCase1.ingredient_type.label("category"),
            OrderCase1InventoryMapping.quantity,
            func.REGEXP_REPLACE(
                InventoryCase1.price_per_unit, '[^0-9.]', '', 'g'
            ).cast(Float).label("unit_price"),
            (
                cast(OrderCase1InventoryMapping.quantity, Float) *
                cast(
                    func.REGEXP_REPLACE(InventoryCase1.price_per_unit, '[^0-9.]', '', 'g'),
                    Float
                )
            ).label("item_cost")
        ).select_from(
            OrderCase1.__table__
            .join(VendorCase1.__table__, VendorCase1.id == OrderCase1.vendor_id)
            .join(OrderCase1InventoryMapping.__table__, OrderCase1.id == OrderCase1InventoryMapping.order_id)
            .join(InventoryCase1.__table__, InventoryCase1.id == OrderCase1InventoryMapping.inventory_id)
            .join(IngredientCase1Type, IngredientCase1Type.id == InventoryCase1.ingredient_type_id)
        ).where(
            OrderCase1.business_owner_id == business_owner_id
        ).order_by(
            OrderCase1.created_at.desc()
        )

        result = await session.execute(query)
        return result.mappings().all()


from datetime import datetime
from sqlalchemy import DateTime


async def get_pending_deliveries(business_owner_id: int):
    async with RestaurantSessionLocal() as session:
        query = (
            select(
                OrderCase1.id.label("order_id"),
                OrderCase1.delivery_date,
                OrderCase1.created_at,
                StatusCase1Type.value.label("status")
            )
            .join(StatusCase1Type, StatusCase1Type.id == OrderCase1.status_type_id)
            .where(
                OrderCase1.business_owner_id == business_owner_id,
                StatusCase1Type.value.in_(["pending", "delayed"]),
                cast(OrderCase1.delivery_date, DateTime) >= datetime.utcnow()

            )
            .order_by(OrderCase1.delivery_date.asc())
        )

        result = await session.execute(query)
        return result.mappings().all()

async def get_received_inventory_log(business_owner_id: int):
    async with RestaurantSessionLocal() as session:
        query = (
            select(
                OrderCase1.id.label("order_id"),
                VendorCase1.name.label("vendor_name"),
                OrderCase1InventoryMapping.inventory_id,
                InventoryCase1.name.label("inventory_name"),
                OrderCase1InventoryMapping.quantity.label("received_quantity"),
                OrderCase1.delivery_date,
                OrderCase1.payment_invoice_url,
                StatusCase1Type.value.label("status")
            )
            .select_from(OrderCase1)
            .join(VendorCase1, VendorCase1.id == OrderCase1.vendor_id)
            .join(OrderCase1InventoryMapping, OrderCase1.id == OrderCase1InventoryMapping.order_id)
            .join(InventoryCase1, InventoryCase1.id == OrderCase1InventoryMapping.inventory_id)
            .join(StatusCase1Type, StatusCase1Type.id == OrderCase1.status_type_id)
            .where(
                OrderCase1.business_owner_id == business_owner_id,
                OrderCase1.delivery_date.isnot(None)
            )
            .order_by(OrderCase1.delivery_date.desc())
        )

        result = await session.execute(query)
        return result.mappings().all()


async def get_rejected_orders_log(business_owner_id: int):
    async with RestaurantSessionLocal() as session:
        query = (
            select(
                OrderCase1.id.label("order_id"),
                VendorCase1.name.label("vendor_name"),
                OrderCase1.created_at,
                OrderCase1.delivery_date,
                OrderCase1.delivery_date,
                StatusCase1Type.value.label("status"),
            )
            .select_from(OrderCase1)
            .join(VendorCase1, VendorCase1.id == OrderCase1.vendor_id)
            .join(StatusCase1Type, StatusCase1Type.id == OrderCase1.status_type_id)
            .where(
                OrderCase1.business_owner_id == business_owner_id,
                StatusCase1Type.value.ilike("rejected")  # case-insensitive match
            )
            .order_by(OrderCase1.created_at.desc())
        )
        result = await session.execute(query)
        return result.mappings().all()
