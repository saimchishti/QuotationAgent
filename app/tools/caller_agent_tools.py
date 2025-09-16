# app/tools/retrieval_tool.py
from __future__ import annotations
from __future__ import annotations

import json
from typing import Optional
from langchain.tools import tool
from app.services.order_submit_service import submit_order_service
import json
from langchain.tools import tool
from langchain.tools import tool
import json
from typing import Any, Dict, List, Optional
from app.services.order_draft_service import create_order_draft_service
from app.services.customer_verification_service import verify_customer_by_phone
from app.services.customer_registration_service import register_customer_for_order
from app.services.item_availability_service import check_item_availability

@tool("customer_verification", description="Verify if a customer exists in the vendor database by phone number", return_direct=False)
async def customer_verification_tool(phone: str) -> str:
    result = await verify_customer_by_phone(phone)
    return json.dumps(result)


@tool("register_customer_for_order", return_direct=False)
async def register_customer_for_order_tool(
    phone: str,
    *,
    business_name: str | None = None,
    full_name: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    service_required: str | None = None,
    notes: str | None = None,
    source_channel: str | None = "phone-call",
) -> str:
    """
    Tool wrapper for register_customer_for_order service.
    """
    result = await register_customer_for_order(
        phone=phone,
        business_name=business_name,
        full_name=full_name,
        first_name=first_name,
        last_name=last_name,
        email=email,
        service_required=service_required,
        notes=notes,
        source_channel=source_channel,
    )
    return json.dumps(result, default=str)


@tool(
    "check_item_availability",
    description="Check if an item is available in the vendor database by its name.",
    return_direct=False
)
async def check_item_availability_tool(item_name: str) -> str:
    """Check if an item is available in the vendor database by its name."""
    result = await check_item_availability(item_name)
    return json.dumps(result)




@tool("create_order_draft", return_direct=False)
async def create_order_draft_tool(
    phone: Optional[str] = None,
    customer_id: Optional[int] = None,
    line_items: Optional[List[Dict[str, Any]]] = None,
    delivery_date: Optional[str] = None,
    notes: Optional[str] = None
) -> str:
    """Create an order draft by validating customer & items, checking availability, and computing totals."""
    result = await create_order_draft_service(
        phone=phone,
        customer_id=customer_id,
        line_items=line_items or [],
        delivery_date=delivery_date,
        notes=notes
    )
    return json.dumps(result, default=str)


# app/tools/order_submit_tool.py
# app/tools/submit_order_tool.py


@tool(
    "submit_order",
    description=(
        "Submit a confirmed order from a draft_id. "
        "Re-checks stock, inserts rows into vendors.orders (one per item), "
        "decrements inventory, and returns the created order_id(s)/number."
    ),
    return_direct=False,
)
async def submit_order_tool(
    draft_id: str,
    payment_method: Optional[str] = None,
    payment_status: str = "pending",
    delivery_status: str = "pending",
) -> str:
    """
    Finalize an order from a previously created draft.

    Args:
        draft_id: The draft identifier returned by create_order_draft_service.
        payment_method: e.g., 'cash', 'card', 'bank_transfer' (optional).
        payment_status: e.g., 'pending', 'paid', 'failed' (default: 'pending').
        delivery_status: e.g., 'pending', 'processing', 'delivered' (default: 'pending').

    Returns:
        JSON string with:
        - success: bool
        - order_number: shared order number string (if success)
        - orders: list of created order rows (one per item)
        - total: grand total
        - or reason/error if it failed
    """
    result = await submit_order_service(
        draft_id,
        payment_method=payment_method,
        payment_status=payment_status,
        delivery_status=delivery_status,
    )
    return json.dumps(result, default=str)
