# app/services/order_draft_service.py
from typing import Any, Dict, List, Optional
import uuid
import time
from sqlalchemy import select, func
from app.db.session import VendorSessionLocal
from app.db.vendors_models import VdCustomer, VdTemporaryCustomer, VdInventory

# --- In-memory draft store ---
DRAFT_CACHE: Dict[str, Dict[str, Any]] = {}
DRAFT_TTL = 15 * 60  # 15 min


def _gc_drafts():
    now = time.time()
    expired = [k for k, v in DRAFT_CACHE.items() if now - v["_ts"] > DRAFT_TTL]
    for k in expired:
        DRAFT_CACHE.pop(k, None)


async def _find_customer(phone: Optional[str] = None, customer_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Find customer in Vendors DB by phone or id."""
    async with VendorSessionLocal() as session:
        if phone:
            digits = "".join(c for c in phone if c.isdigit())
            stmt = select(VdCustomer).where(func.regexp_replace(VdCustomer.phone, r"[^0-9]", "", "g") == digits)
            cust = (await session.execute(stmt)).scalar_one_or_none()
            if cust:
                return {"id": cust.customer_id, "first_name": cust.first_name, "last_name": cust.last_name, "phone": cust.phone}
            stmt = select(VdTemporaryCustomer).where(func.regexp_replace(VdTemporaryCustomer.phone, r"[^0-9]", "", "g") == digits)
            cust = (await session.execute(stmt)).scalar_one_or_none()
            if cust:
                return {"id": cust.temp_customer_id, "first_name": cust.first_name, "last_name": cust.last_name, "phone": cust.phone}

        if customer_id:
            stmt = select(VdCustomer).where(VdCustomer.customer_id == customer_id)
            cust = (await session.execute(stmt)).scalar_one_or_none()
            if cust:
                return {"id": cust.customer_id, "first_name": cust.first_name, "last_name": cust.last_name, "phone": cust.phone}
            stmt = select(VdTemporaryCustomer).where(VdTemporaryCustomer.temp_customer_id == customer_id)
            cust = (await session.execute(stmt)).scalar_one_or_none()
            if cust:
                return {"id": cust.temp_customer_id, "first_name": cust.first_name, "last_name": cust.last_name, "phone": cust.phone}

    return None


async def _find_item(item_id: Optional[int] = None, name: Optional[str] = None) -> Optional[VdInventory]:
    """Find item in Vendors DB by id or name."""
    async with VendorSessionLocal() as session:
        if item_id:
            stmt = select(VdInventory).where(VdInventory.inventory_id == item_id).limit(1)
            item = (await session.execute(stmt)).scalar_one_or_none()
            if item:
                return item
        if name:
            stmt = (
                select(VdInventory)
                .where(func.lower(VdInventory.item_name) == func.lower(name))
                .limit(1)
            )
            item = (await session.execute(stmt)).scalar_one_or_none()
            if item:
                return item
    return None



async def create_order_draft_service(
    *,
    phone: Optional[str] = None,
    customer_id: Optional[int] = None,
    line_items: List[Dict[str, Any]],
    delivery_date: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """Create an in-memory order draft: validate customer & items, compute totals."""
    _gc_drafts()

    # Validate customer
    customer = await _find_customer(phone=phone, customer_id=customer_id)
    if not customer:
        return {"error": "Customer not found"}

    subtotal = 0.0
    lines = []
    all_available = True

    for li in line_items:
        qty = li.get("qty")
        if not qty or qty <= 0:
            return {"error": f"Invalid qty for {li}"}

        item = await _find_item(item_id=li.get("item_id"), name=li.get("name"))
        if not item:
            all_available = False
            lines.append({"status": "not_found", "requested": qty})
            continue

        available = item.quantity_on_hand or 0
        unit_price = float(item.unit_price or 0)
        status = "ok" if available >= qty else "insufficient"
        if status != "ok":
            all_available = False

        subtotal += unit_price * qty
        lines.append({
            "item_id": item.inventory_id,
            "name": item.item_name,
            "requested": qty,
            "available": available,
            "unit_price": unit_price,
            "status": status
        })

    draft_id = str(uuid.uuid4())
    draft_data = {
        "draft_id": draft_id,
        "customer": customer,
        "lines": lines,
        "subtotal": subtotal,
        "all_available": all_available,
        "delivery_date": delivery_date,
        "notes": notes
    }
    DRAFT_CACHE[draft_id] = {**draft_data, "_ts": time.time()}

    return draft_data
# --- add to: app/services/order_draft_service.py ---

# --- replace ONLY this function in app/services/order_draft_service.py ---

async def get_draft_service(draft_id: str) -> dict:
    """
    Return a previously created order draft from the in-memory cache.
    If the draft is expired or missing, returns {"error": "..."}.
    """
    _gc_drafts()  # <- use the correct GC helper defined above
    data = DRAFT_CACHE.get(draft_id)
    if not data:
        return {"error": "Draft not found or expired"}

    out = dict(data)
    out.pop("_ts", None)  # hide internal timestamp
    return out
