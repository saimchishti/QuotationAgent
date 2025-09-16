# RESTAURANT-AGENT-MAIN/app/services/dataprovider_vendor.py

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from collections import defaultdict
from datetime import datetime, timedelta
import re

from app.db.models import (
    VendorCase1,
    InventoryCase1,
    OrderCase1,
    StatusCase1Type,
    BusinessOwnerInventory,
    OrderCase1InventoryMapping
)

def _extract_numeric_price(price_str: str) -> float:
    """Helper to safely extract a number from a price string like '150.50 PKR'."""
    if not price_str:
        return 0.0
    # Find the first numeric part of the string (integer or float)
    match = re.search(r"\d+(\.\d+)?", str(price_str))
    return float(match.group()) if match else 0.0

# --- 1. Vendor Directory Viewer ---
async def get_vendor_directory(db: AsyncSession, business_owner_id: int = None):
    """
    Fetches a directory of vendors. If a business_owner_id is provided, it shows
    only vendors used by that owner. Otherwise, it shows all vendors.
    """
    # Part 1: Get base vendor information
    vendors_query = select(VendorCase1)
    if business_owner_id:
        vendor_ids_subquery = select(OrderCase1.vendor_id).where(OrderCase1.business_owner_id == business_owner_id).distinct()
        vendors_query = vendors_query.where(VendorCase1.id.in_(vendor_ids_subquery))
    vendors_result = await db.execute(vendors_query)
    all_vendors = vendors_result.scalars().all()

    # Part 2: Get all ingredients and map them to their vendor
    ingredients_query = select(InventoryCase1.vendor_id, InventoryCase1.name)
    ingredients_result = await db.execute(ingredients_query)
    vendor_ingredients_map = defaultdict(list)
    for row in ingredients_result.fetchall():
        vendor_ingredients_map[row.vendor_id].append(row.name)

    # Part 3: Get all unique restaurant-vendor order pairs
    branches_query = select(OrderCase1.vendor_id, OrderCase1.business_owner_id).distinct()
    branches_result = await db.execute(branches_query)
    vendor_branches_map = defaultdict(set)
    for row in branches_result.fetchall():
        vendor_branches_map[row.vendor_id].add(row.business_owner_id)

    # Part 4: Combine all data
    enriched_vendors = []
    for vendor in all_vendors:
        vendor_data = {
            "id": vendor.id,
            "name": vendor.name,
            "contact_person": vendor.contact_person,
            "email": vendor.email,
            "phone": vendor.phone,
            "city": vendor.city,
            "supplied_ingredients": vendor_ingredients_map.get(vendor.id, []),
            "linked_branches": list(vendor_branches_map.get(vendor.id, []))
        }
        enriched_vendors.append(vendor_data)
    return enriched_vendors

# --- 2. Ingredient-to-Vendor Mapper ---
async def get_ingredient_to_vendor_mapping(db: AsyncSession, business_owner_id: int):
    """
    Creates a mapping of each ingredient to the vendors who supply it,
    scoped to a specific business owner's inventory.
    """
    query = (
        select(
            InventoryCase1.name.label("ingredient_name"),
            VendorCase1.name.label("vendor_name")
        )
        .select_from(BusinessOwnerInventory)  # Start from the owner's inventory
        .join(InventoryCase1, BusinessOwnerInventory.inventory_id == InventoryCase1.id)
        .join(VendorCase1, InventoryCase1.vendor_id == VendorCase1.id)
        .where(BusinessOwnerInventory.business_owner_id == business_owner_id)  # Filter by owner
        .order_by(InventoryCase1.name)
    )
    result = await db.execute(query)
    
    ingredient_map = defaultdict(list)
    for row in result.fetchall():
        ingredient_map[row.ingredient_name].append(row.vendor_name)
        
    return ingredient_map
# --- 3. Vendor Performance Tracker (CORRECTED VERSION) ---
async def get_vendor_performance(db: AsyncSession, business_owner_id: int):
    """
    Tracks order status, delivery times, and costs for vendors used by a specific business owner.
    """
    # This query now joins all necessary tables to calculate the order cost.
    query = (
        select(
            OrderCase1.id.label("order_id"),
            VendorCase1.name.label("vendor_name"),
            VendorCase1.delivery_time,
            OrderCase1.created_at,
            OrderCase1.delivery_date,
            StatusCase1Type.value.label("order_status"),
            OrderCase1InventoryMapping.quantity,
            InventoryCase1.price_per_unit
        )
        .join(VendorCase1, OrderCase1.vendor_id == VendorCase1.id)
        .join(StatusCase1Type, OrderCase1.status_type_id == StatusCase1Type.id)
        .join(OrderCase1InventoryMapping, OrderCase1.id == OrderCase1InventoryMapping.order_id)
        .join(InventoryCase1, OrderCase1InventoryMapping.inventory_id == InventoryCase1.id)
        .where(OrderCase1.business_owner_id == business_owner_id)
    )
    result = await db.execute(query)
    
    # Step 1: Process results to calculate total cost per order
    order_costs = defaultdict(float)
    order_details = {}
    for row in result.fetchall():
        order_id = row.order_id
        item_cost = (row.quantity or 0) * _extract_numeric_price(row.price_per_unit)
        order_costs[order_id] += item_cost
        if order_id not in order_details:
            order_details[order_id] = row # Store the first row of order details

    # Step 2: Aggregate performance data per vendor
    performance_data = defaultdict(lambda: {
        "total_orders": 0,
        "total_cost": 0.0,
        "on_time_deliveries": 0,
        "late_deliveries": 0,
        "status_counts": defaultdict(int)
    })

    processed_orders = set()
    for order_id, details in order_details.items():
        if order_id in processed_orders:
            continue
        
        vendor_name = details.vendor_name
        stats = performance_data[vendor_name]
        
        stats["total_orders"] += 1
        stats["total_cost"] += order_costs[order_id]
        stats["status_counts"][details.order_status] += 1
        
        try:
            if details.delivery_date and details.created_at and details.delivery_time is not None:
                expected_delivery_date = details.created_at + timedelta(days=details.delivery_time)
                actual_delivery_date = datetime.fromisoformat(str(details.delivery_date))
                if actual_delivery_date.date() <= expected_delivery_date.date():
                    stats["on_time_deliveries"] += 1
                else:
                    stats["late_deliveries"] += 1
        except (TypeError, ValueError):
            pass
        
        processed_orders.add(order_id)
            
    return performance_data

# --- 4. Ingredient Sourcing Optimizer ---
async def get_ingredient_sourcing_options(db: AsyncSession, business_owner_id: int, ingredient_name: str):
    """
    Finds vendors for a specific ingredient that are relevant to a business owner.
    """
    query = (
        select(
            VendorCase1.name.label("vendor_name"),
            InventoryCase1.price_per_unit,
            InventoryCase1.delivery_time_frame
        )
        .select_from(BusinessOwnerInventory)
        .join(InventoryCase1, BusinessOwnerInventory.inventory_id == InventoryCase1.id)
        .join(VendorCase1, InventoryCase1.vendor_id == VendorCase1.id)
        .where(BusinessOwnerInventory.business_owner_id == business_owner_id)
        .where(InventoryCase1.name.ilike(f"%{ingredient_name}%"))
    )
    result = await db.execute(query)
    return result.fetchall()

# --- 5. Vendor-Branch Linkage ---
async def get_vendor_branch_linkage(db: AsyncSession, business_owner_id: int):
    """
    Shows which vendors a specific business owner (branch) orders from.
    """
    query = (
        select(
            VendorCase1.name.label("vendor_name"),
            func.count(OrderCase1.id).label("order_count")
        )
        .join(VendorCase1, OrderCase1.vendor_id == VendorCase1.id)
        .where(OrderCase1.business_owner_id == business_owner_id)
        .group_by(VendorCase1.name)
        .order_by(func.count(OrderCase1.id).desc())
    )
    result = await db.execute(query)
    return result.fetchall()
