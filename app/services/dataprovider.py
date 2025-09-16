from sqlalchemy.future import select
from sqlalchemy import func
from app.db.session import RestaurantSessionLocal
from app.db.models import (
    BusinessOwnerInventory,
    InventoryCase1,
    IngredientCase1Type,
    VendorCase1,
    VendorInventory,
    OrderCase1,
    OrderCase1InventoryMapping,
    UnitCase1Type
)


from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from sqlalchemy import cast, Float


async def get_inventory_overview_by_owner(business_owner_id: int):
    """
    Fetches inventory stock grouped by ingredient type (category) and vendor (brand)
    for a specific business owner.
    """
    async with RestaurantSessionLocal() as session:
        query = (
            select(
                IngredientCase1Type.value.label("ingredient_type"),
                VendorCase1.name.label("vendor_name"),
                InventoryCase1.name.label("item_name"),
                func.sum(BusinessOwnerInventory.stock_quantity).label("total_quantity"),
                InventoryCase1.unit_quantity,
                InventoryCase1.price_per_unit,
            )
            .join(InventoryCase1, BusinessOwnerInventory.inventory)
            .join(IngredientCase1Type, InventoryCase1.ingredient_type)
            .join(VendorCase1, InventoryCase1.vendor)
            .filter(BusinessOwnerInventory.business_owner_id == business_owner_id)
            .group_by(
                IngredientCase1Type.value,
                VendorCase1.name,
                InventoryCase1.name,
                InventoryCase1.unit_quantity,
                InventoryCase1.price_per_unit,
            )
            .order_by(IngredientCase1Type.value, VendorCase1.name)
        )

        result = await session.execute(query)
        rows = result.fetchall()

        return [
            {
                "ingredient_type": row.ingredient_type,
                "vendor_name": row.vendor_name,
                "item_name": row.item_name,
                "total_quantity": row.total_quantity,
                "unit_quantity": row.unit_quantity,
                "price_per_unit": row.price_per_unit,
            }
            for row in rows
        ]

def parse_to_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            return None
    return None

async def get_expiring_inventory_by_owner(business_owner_id: int, db: AsyncSession = None):
    if db is None:
        async with RestaurantSessionLocal() as db:
            return await get_expiring_inventory_by_owner(business_owner_id, db)

    today = datetime.utcnow().date()

    stmt = (
        select(
            BusinessOwnerInventory.id,
            BusinessOwnerInventory.inventory_id,
            BusinessOwnerInventory.created_at.label("received_date"),
            BusinessOwnerInventory.expiry_date,
            InventoryCase1.shelf_life,
            InventoryCase1.name.label("item_name")
        )
        .join(InventoryCase1, BusinessOwnerInventory.inventory_id == InventoryCase1.id)
        .where(BusinessOwnerInventory.business_owner_id == business_owner_id)
    )

    result = await db.execute(stmt)
    records = result.fetchall()

    expiring_items = []
    for row in records:
        expiry = parse_to_date(row.expiry_date)
        received = parse_to_date(row.received_date)

        # Compute expiry if missing and shelf_life exists
        if expiry is None and received and row.shelf_life:
            try:
                expiry = received + timedelta(days=int(row.shelf_life))
            except (ValueError, TypeError):
                continue

        if expiry and received:
            total_life = (expiry - received).days
            if total_life <= 0:
                continue  # Skip invalid shelf life
            days_remaining = (expiry - today).days
            remaining_percent = days_remaining / total_life

            if 0 <= remaining_percent <= 0.9:
                expiring_items.append({
                    "id": row.id,
                    "item_name": row.item_name,
                    "expiry_date": expiry.isoformat(),
                    "days_remaining": days_remaining,
                    "status": "Nearing Expiry"
                })

    return expiring_items


async def get_inventory_cost_breakdown(business_owner_id: int, db: AsyncSession = None):

    
    if db is None:
        async with RestaurantSessionLocal() as session:
            return await get_inventory_cost_breakdown(business_owner_id, db=session)

    # Get current inventory list price per unit
    stmt_inventory = (
        select(
            InventoryCase1.id,
            InventoryCase1.name,
            InventoryCase1.unit_type_id,
            InventoryCase1.unit_type,
            InventoryCase1.vendor_id,
            InventoryCase1.price_per_unit
        )
    )
    inv_data = (await db.execute(stmt_inventory)).fetchall()
    inventory_map = {row.id: row._asdict() for row in inv_data}

    # Vendor cost price comparison
    stmt_vendor = (
        select(
            VendorInventory.id,
            func.avg(VendorInventory.cost_price).label("avg_supplier_price")
        )
        .join(VendorCase1, VendorInventory.vendor_id == VendorCase1.id)
        .where(VendorCase1.id == business_owner_id)
        .group_by(VendorInventory.id)
    )
    vendor_data = (await db.execute(stmt_vendor)).fetchall()

    for row in vendor_data:
        if row.inventory_id in inventory_map:
            inventory_map[row.inventory_id]["avg_supplier_price"] = float(row.avg_supplier_price)

    # Historical price trend from orders
    from sqlalchemy import cast, Float

    month_trunc_expr = func.date_trunc('month', OrderCase1.created_at)

    stmt_orders = (
    select(
        OrderCase1InventoryMapping.inventory_id,
        month_trunc_expr,
        func.avg(cast(InventoryCase1.price_per_unit, Float)).label("avg_unit_price"),
        UnitCase1Type.value.label("unit_type_name")
    )
    .join(OrderCase1, OrderCase1InventoryMapping.order_id == OrderCase1.id)
    .join(InventoryCase1, OrderCase1InventoryMapping.inventory_id == InventoryCase1.id)
    .join(UnitCase1Type, InventoryCase1.unit_type_id == UnitCase1Type.id)  # ✅ fix
    .where(OrderCase1.business_owner_id == business_owner_id)
    .group_by(
        OrderCase1InventoryMapping.inventory_id,
        month_trunc_expr,
        UnitCase1Type.value
    )
    .order_by(month_trunc_expr)
)
    

    
    order_data = (await db.execute(stmt_orders)).fetchall()

    for row in order_data:
        if row.inventory_id in inventory_map:
            inventory_map[row.inventory_id].setdefault("price_trend", []).append({
                "month": row.month.strftime("%Y-%m"),
                "avg_unit_price": float(row.avg_unit_price)
            })

    return list(inventory_map.values())


    month_trunc_expr = func.date_trunc('month', OrderCase1.created_at).label("month")

    PreferredVendor = aliased(VendorCase1)
    DefaultVendor = aliased(VendorCase1)

    stmt = (
        select(
            OrderCase1InventoryMapping.inventory_id,
            month_trunc_expr,
            func.avg(cast(InventoryCase1.price_per_unit, Float)).label("avg_unit_price"),
            UnitCase1Type.name.label("unit_type"),
            case(
                (PreferredVendor.name != None, PreferredVendor.name),
                else_=DefaultVendor.name
            ).label("vendor_name")
        )
        .join(OrderCase1, OrderCase1InventoryMapping.order_id == OrderCase1.id)
        .join(InventoryCase1, OrderCase1InventoryMapping.inventory_id == InventoryCase1.id)
        .join(UnitCase1Type, InventoryCase1.unit_type_id == UnitCase1Type.id)
        .join(
            BusinessOwnerInventory,
            (BusinessOwnerInventory.inventory_id == InventoryCase1.id) &
            (BusinessOwnerInventory.business_owner_id == business_owner_id),
            isouter=True
        )
        .join(PreferredVendor, BusinessOwnerInventory.vendor_id == PreferredVendor.id, isouter=True)
        .join(DefaultVendor, InventoryCase1.vendor_id == DefaultVendor.id)
        .where(OrderCase1.business_owner_id == business_owner_id)
        .group_by(
            OrderCase1InventoryMapping.inventory_id,
            month_trunc_expr,
            UnitCase1Type.name,
            PreferredVendor.name,
            DefaultVendor.name
        )
        .order_by(month_trunc_expr)
    )

    async with async_session() as session:
        result = await session.execute(stmt)
        return [dict(row) for row in result.fetchall()]
    

    from sqlalchemy import select, func



from sqlalchemy import select, func
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession

async def get_inventory_by_supplier_or_brand(session: AsyncSession, business_owner_id: int):
    stmt = (
        select(
            VendorCase1.name.label("vendor_name"),
            InventoryCase1.name.label("brand"),
            func.count(InventoryCase1.id).label("item_count")
        )
        .select_from(BusinessOwnerInventory)
        .join(InventoryCase1, BusinessOwnerInventory.inventory_id == InventoryCase1.id)
        .join(VendorCase1, InventoryCase1.vendor_id == VendorCase1.id)
        .where(BusinessOwnerInventory.business_owner_id == business_owner_id)
        .group_by(VendorCase1.name, InventoryCase1.name)
        .order_by(VendorCase1.name, InventoryCase1.name)
    )

    result = await session.execute(stmt)
    return result.fetchall()

