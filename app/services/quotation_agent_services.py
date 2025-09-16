"""
quotation_service.py
--------------------
Services for generating quotations from draft orders.
Used by LangGraph Quotation Agent.
"""

import json
from datetime import datetime, timezone
from sqlalchemy import select, func
from app.db.session import VendorSessionLocal
from app.db.vendors_models import Product
from app.core.config import llm


# ==============================
# 1. Validate Items in Postgres
# ==============================
async def validate_items(items: dict) -> dict:
    """
    Validate item availability from Vendor DB (Products table).
    Args:
        items: dict like {"burger": 2, "fries": 1}
    Returns:
        dict with availability info
    """
    results = {}
    async with VendorSessionLocal() as session:
        for name, qty in items.items():
            stmt = select(Product).where(func.lower(Product.name) == func.lower(name)).limit(1)
            row = (await session.execute(stmt)).scalar_one_or_none()

            if not row:
                results[name] = {"available": False, "reason": "Not found"}
                continue

            if row.stock_quantity < qty:
                results[name] = {
                    "available": False,
                    "reason": f"Only {row.stock_quantity} in stock",
                    "requested": qty,
                }
            else:
                results[name] = {
                    "available": True,
                    "requested": qty,
                    "unit_price": float(row.price),
                    "stock": row.stock_quantity,
                }
    return results


# ==============================
# 2. Generate Quotation with LLM
# ==============================
async def generate_quotation(draft: dict) -> dict:
    """
    Take a draft order and generate quotation JSON via LLM.
    Args:
        draft: dict from Mongo draft
    Returns:
        dict with quotation info
    """
    items = draft.get("items", {})
    availability = await validate_items(items)

    items_text = "\n".join(
        f"- {n}: requested {i.get('requested')}, available {i.get('stock','N/A')}, price {i.get('unit_price','?')}"
        for n, i in availability.items()
    )

    prompt = f"""
    You are a quotation agent.

    Customer ID: {draft.get("customer_id")}
    Items requested:
    {items_text}

    Rules:
    - Only include items where available=True.
    - If order total > 1000 PKR, apply 10% discount.
    - If order total < 500 PKR, politely encourage customer to add more items.
    - Return output strictly as JSON:
      {{
        "items": {{ "burger": {{"qty": 2, "price": 500}} }},
        "total_price": 1200,
        "discount_applied": 120,
        "final_price": 1080,
        "negotiation_message": "..."
      }}
    """

    llm_response = llm.invoke(prompt).content
    try:
        data = json.loads(llm_response)
    except Exception:
        data = {"error": "Failed to parse LLM response", "raw": llm_response}

    return data
