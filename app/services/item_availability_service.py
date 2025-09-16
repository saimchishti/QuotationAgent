from sqlalchemy import select, func
from app.db.session import VendorSessionLocal
from app.db.vendors_models import VdInventory  # <- correct module & model

async def check_item_availability(item_name: str) -> dict:
    """
    Check if an item is available in the Vendors DB inventory by name.
    Prefers exact (case-insensitive) match; falls back to partial match.
    Returns available True/False and quantity if found.
    """
    if not item_name or not item_name.strip():
        return {"error": "Item name is required"}

    name = item_name.strip()

    async with VendorSessionLocal() as session:
        # 1) Try exact (case-insensitive) match
        stmt_exact = select(VdInventory).where(func.lower(VdInventory.item_name) == func.lower(name)).limit(1)
        row = (await session.execute(stmt_exact)).scalar_one_or_none()

        # 2) If not found, try partial (case-insensitive) match
        if row is None:
            stmt_partial = select(VdInventory).where(
                func.lower(VdInventory.item_name).like(f"%{name.lower()}%")
            ).limit(1)
            row = (await session.execute(stmt_partial)).scalar_one_or_none()

        if row is None:
            return {"available": False, "message": "Item not found"}

        qty = getattr(row, "quantity_on_hand", None)
        if qty is not None and qty > 0:
            return {
                "available": True,
                "item_id": getattr(row, "inventory_id", None),
                "name": row.item_name,
                "quantity": qty,
                "message": f"{qty} units available",
            }
        else:
            return {
                "available": False,
                "item_id": getattr(row, "inventory_id", None),
                "name": row.item_name,
                "quantity": qty,
                "message": "Out of stock",
            }
