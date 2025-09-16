"""
quotation_tools.py
------------------
Async LangChain tools for the Quotation Agent workflow:
1) Fetch draft orders from Mongo
2) Mark draft as in_progress
3) Check item availability in Vendor DB (using Product table)
4) Validate all draft items
"""

import json
from datetime import datetime, timezone
from sqlalchemy import select, func
from langchain_core.tools import tool

from app.db.session import get_collection, VendorSessionLocal
from app.db.vendors_models import Product   # ✅ use Product instead of missing VdInventory


# ==============================
# 1. Fetch Draft Orders
# ==============================
@tool("fetch_draft_orders")
async def fetch_draft_orders_tool() -> str:
    """
    Fetch all pending draft orders from MongoDB.
    Returns a JSON string of drafts.
    """
    collection = get_collection("order_drafts")
    cursor = collection.find({"status": "draft"})
    drafts = list(cursor)
    for d in drafts:
        d["_id"] = str(d["_id"])  # BSON -> str
    return json.dumps(drafts, default=str)


# ==============================
# 2. Mark Draft In Progress
# ==============================
@tool("mark_draft_in_progress")
async def mark_draft_in_progress_tool(draft_id: str) -> str:
    """
    Mark a draft order as 'in_progress' so it is not picked twice.
    Accepts a draft_id string.
    """
    collection = get_collection("order_drafts")
    collection.update_one(
        {"_id": draft_id},
        {"$set": {"status": "in_progress", "picked_at": datetime.now(timezone.utc)}},
    )
    return json.dumps({"success": True, "draft_id": draft_id})


# ==============================
# 3. Check Item Availability
# ==============================
@tool("check_item_availability")
async def check_item_availability_tool(item_name: str) -> str:
    """
    Check if a single item is available in Vendor DB (Products table).
    Returns JSON with stock and price info.
    """
    if not item_name or not item_name.strip():
        return json.dumps({"error": "Item name is required"})

    name = item_name.strip()

    async with VendorSessionLocal() as session:
        # Try exact (case-insensitive) match
        stmt_exact = select(Product).where(func.lower(Product.name) == func.lower(name)).limit(1)
        row = (await session.execute(stmt_exact)).scalar_one_or_none()

        # If not found, try partial match
        if row is None:
            stmt_partial = select(Product).where(
                func.lower(Product.name).like(f"%{name.lower()}%")
            ).limit(1)
            row = (await session.execute(stmt_partial)).scalar_one_or_none()

        if row is None:
            return json.dumps({"available": False, "message": "Item not found"})

        qty = getattr(row, "stock_quantity", None)
        price = float(row.price) if row.price is not None else None

        if qty is not None and qty > 0:
            return json.dumps({
                "available": True,
                "product_id": getattr(row, "product_id", None),
                "name": row.name,
                "quantity": qty,
                "unit_price": price,
                "message": f"{qty} units available",
            })
        else:
            return json.dumps({
                "available": False,
                "product_id": getattr(row, "product_id", None),
                "name": row.name,
                "quantity": qty,
                "unit_price": price,
                "message": "Out of stock",
            })


# ==============================
# 4. Validate All Draft Items
# ==============================
@tool("validate_draft_items")
async def validate_draft_items_tool(items_json: str) -> str:
    """
    Validate items JSON string against Products table.
    Returns availability info.
    """
    import json
    from app.services.quotation_agent_services import validate_items

    try:
        items = json.loads(items_json)
    except Exception as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    result = await validate_items(items)
    return json.dumps(result, default=str)