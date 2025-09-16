# app/services/submit_order_service.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
from decimal import Decimal
from datetime import datetime

from sqlalchemy import select, update, func, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.order_draft_service import DRAFT_CACHE, _gc_drafts
from app.db.session import VendorSessionLocal
from app.db.vendors_models import VdOrder, VdInventory  # <-- matches your file name

def _to_float(x: Any) -> float:
    if x is None: return 0.0
    if isinstance(x, Decimal): return float(x)
    try: return float(x)
    except Exception: return 0.0

def _order_number() -> str:
    # e.g., ORD-20250813-153512
    return f"ORD-{datetime.utcnow():%Y%m%d-%H%M%S}"

async def _recheck_lines(session: AsyncSession, draft_lines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Re-check availability & pull live unit_price from VdInventory."""
    all_ok = True
    out: List[Dict[str, Any]] = []

    for li in draft_lines:
        item_id = li.get("item_id")
        requested = int(li.get("requested") or li.get("qty") or 0)

        if not item_id or requested <= 0:
            all_ok = False
            out.append({"item_id": item_id, "requested": requested, "status": "invalid"})
            continue

        stmt = select(VdInventory).where(VdInventory.inventory_id == item_id).limit(1)
        row = (await session.execute(stmt)).scalar_one_or_none()
        if not row:
            all_ok = False
            out.append({"item_id": item_id, "requested": requested, "status": "not_found"})
            continue

        now_avail = int(row.quantity_on_hand or 0)
        unit_price = _to_float(row.unit_price)
        status = "ok" if now_avail >= requested and now_avail > 0 else ("insufficient" if now_avail > 0 else "out_of_stock")
        if status != "ok":
            all_ok = False

        out.append({
            "item_id": item_id,
            "name": row.item_name,
            "requested": requested,
            "now_available": now_avail,
            "unit_price": unit_price,
            "status": status,
        })

    return {"ok": all_ok, "lines": out}

async def submit_order_service(
    draft_id: str,
    *,
    payment_method: Optional[str] = None,
    payment_status: str = "pending",
    delivery_status: str = "pending",
) -> Dict[str, Any]:
    """
    Submit an order from a draft:
      - Loads draft from in-memory cache
      - Re-checks live stock & price from VdInventory
      - Inserts ONE VdOrder row PER line (your schema stores item in the order row)
      - Decrements inventory
      - Removes the draft from cache

    Returns:
      {"success": True, "order_number": "...", "orders": [...], "total": float}
      or {"success": False, "reason": "stock_changed", "recheck": [...]}
      or {"success": False, "error": "..."}
    """
    _gc_drafts()
    draft = DRAFT_CACHE.get(draft_id)
    if not draft:
        return {"success": False, "error": "Draft not found or expired"}

    customer = draft.get("customer") or {}
    lines = draft.get("lines") or []
    if not lines:
        return {"success": False, "error": "No line items in draft"}

    # Prepare customer_name
    customer_name = " ".join(filter(None, [customer.get("first_name"), customer.get("last_name")])) or customer.get("name") or "Unknown Customer"
    order_number = _order_number()
    grand_total = 0.0
    created: List[Dict[str, Any]] = []

    async with VendorSessionLocal() as session:
        # 1) Live re-check
        recheck = await _recheck_lines(session, lines)
        if not recheck["ok"]:
            return {"success": False, "reason": "stock_changed", "recheck": recheck["lines"]}

        # 2) Persist rows & decrement stock atomically
        try:
            async with session.begin():
                for rc in recheck["lines"]:
                    qty = int(rc["requested"])
                    unit_price = _to_float(rc["unit_price"])
                    line_total = round(unit_price * qty, 2)
                    grand_total += line_total

                    ins = (
                        insert(VdOrder)
                        .values(
                            order_number=order_number,
                            customer_name=customer_name,
                            # order_date default is CURRENT_TIMESTAMP in DB
                            service_or_item=rc["name"],
                            quantity=qty,
                            price_per_unit=unit_price,
                            total_amount=line_total,
                            payment_method=payment_method,
                            payment_status=payment_status,
                            delivery_status=delivery_status,
                            notes=draft.get("notes"),
                        )
                        .returning(VdOrder.order_id)
                    )
                    res = await session.execute(ins)
                    order_id = res.scalar_one()

                    created.append({
                        "order_id": order_id,
                        "order_number": order_number,
                        "item_id": rc["item_id"],
                        "item_name": rc["name"],
                        "quantity": qty,
                        "price_per_unit": unit_price,
                        "total_amount": line_total,
                    })

                    # Decrement inventory safely
                    upd = (
                        update(VdInventory)
                        .where(VdInventory.inventory_id == rc["item_id"])
                        .values(quantity_on_hand=func.GREATEST(VdInventory.quantity_on_hand - qty, 0))
                    )
                    await session.execute(upd)

            # 3) Remove the draft after commit
            DRAFT_CACHE.pop(draft_id, None)

            return {
                "success": True,
                "order_number": order_number,
                "orders": created,
                "total": round(grand_total, 2),
            }

        except IntegrityError as e:
            return {"success": False, "error": f"Integrity error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
