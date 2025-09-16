"""
live_quotation_service.py
-------------------------
Pulls product costs from Postgres, applies margin rules,
normalizes draft items, generates a structured quotation,
and emails it to the customer.
"""

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional
import json
import re

from sqlalchemy import select
from app.db.session import VendorSessionLocal
from app.db.vendors_models import Product, Client
from app.services.email_service import send_email  # SendGrid helper


# ---------------- Helpers ----------------
def _to_int(value, default: int = 1) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _parse_kv_token(token: str):
    """
    Parse tokens like "Rice:5", "Rice x 5", "Rice * 5" -> ("Rice", 5)
    """
    token = token.strip()
    if not token:
        return None, None
    # Try separators
    for sep in [":", "x", "X", "*", "×", "-"]:
        if sep in token:
            left, right = token.split(sep, 1)
            name = left.strip()
            qty = _to_int(right.strip(), 1)
            return name, qty
    # Fallback "Name 5" at the end
    m = re.match(r"^(.*?)[\s]+(\d+)$", token)
    if m:
        name = m.group(1).strip()
        qty = _to_int(m.group(2), 1)
        return name, qty
    # No qty found; default 1
    return token.strip(), 1


def _normalize_items(raw: Any) -> Dict[str, int]:
    """
    Accepts:
      - dict: {"Rice": 5, "Oil": 2}
      - list[dict]: [{"name":"Rice","quantity":5}, ...]
      - list[tuple]: [("Rice",5), ...]
      - list[str]: ["Rice:5", "Oil x 2"]
      - str: JSON or CSV-ish "Rice:5, Oil:2" / "Rice x 5, Oil x 2"

    Returns:
      dict[str,int]
    """
    if raw is None:
        return {}

    # If string, try JSON first, then CSV-ish parsing
    if isinstance(raw, str):
        s = raw.strip()
        # Try JSON
        if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
            try:
                raw = json.loads(s)
            except Exception:
                # Fall through to token parsing
                pass
        if isinstance(raw, str):
            # Parse CSV-ish "Rice:5, Oil x 2"
            out: Dict[str, int] = {}
            tokens = [t for t in re.split(r"[,\n;]+", raw) if t.strip()]
            for t in tokens:
                name, qty = _parse_kv_token(t)
                if name:
                    out[name] = out.get(name, 0) + _to_int(qty, 1)
            return out

    # If dict, coerce quantities
    if isinstance(raw, dict):
        out = {}
        for k, v in raw.items():
            name = str(k).strip()
            qty = _to_int(v, 1)
            if name:
                out[name] = out.get(name, 0) + qty
        return out

    # If list-like
    if isinstance(raw, (list, tuple)):
        out: Dict[str, int] = {}
        for el in raw:
            if isinstance(el, dict):
                name = el.get("name") or el.get("product") or el.get("product_name") or el.get("sku") or el.get("item")
                qty = el.get("quantity") or el.get("qty") or el.get("count") or el.get("units") or 1
                if name:
                    out[str(name).strip()] = out.get(str(name).strip(), 0) + _to_int(qty, 1)
            elif isinstance(el, (list, tuple)) and len(el) >= 2:
                name = str(el[0]).strip()
                qty = _to_int(el[1], 1)
                if name:
                    out[name] = out.get(name, 0) + qty
            elif isinstance(el, str):
                name, qty = _parse_kv_token(el)
                if name:
                    out[name] = out.get(name, 0) + _to_int(qty, 1)
        return out

    # Fallback: nothing usable
    return {}


def _lookup_client_email_sync(session, customer_id) -> Optional[str]:
    """
    Tries multiple ways to find a client's email.
    Supports numeric IDs and codes like CT-0001/OTW00123 if your model has such fields.
    """
    client = None
    try:
        # Prefer numeric id if possible
        if isinstance(customer_id, int) or (isinstance(customer_id, str) and customer_id.isdigit()):
            cid = int(customer_id)
            client = (session.execute(select(Client).where(Client.client_id == cid).limit(1))).scalar_one_or_none()
        else:
            # Try common code columns if they exist
            for code_col in ("client_code", "external_id", "customer_code"):
                if hasattr(Client, code_col):
                    client = (session.execute(
                        select(Client).where(getattr(Client, code_col) == str(customer_id)).limit(1)
                    )).scalar_one_or_none()
                    if client:
                        break
        if not client:
            # Last resort: try direct equality if the column type allows (e.g., String PK)
            client = (session.execute(select(Client).where(Client.client_id == customer_id).limit(1))).scalar_one_or_none()
    except Exception:
        client = None

    return (client.email if client and getattr(client, "email", None) else None)


async def _lookup_client_email_async(session, customer_id) -> Optional[str]:
    try:
        if isinstance(customer_id, int) or (isinstance(customer_id, str) and customer_id.isdigit()):
            cid = int(customer_id)
            client = (await session.execute(select(Client).where(Client.client_id == cid).limit(1))).scalar_one_or_none()
        else:
            client = None
            for code_col in ("client_code", "external_id", "customer_code"):
                if hasattr(Client, code_col):
                    client = (await session.execute(
                        select(Client).where(getattr(Client, code_col) == str(customer_id)).limit(1)
                    )).scalar_one_or_none()
                    if client:
                        break
            if not client:
                client = (await session.execute(
                    select(Client).where(Client.client_id == customer_id).limit(1)
                )).scalar_one_or_none()
        return client.email if client and getattr(client, "email", None) else None
    except Exception:
        return None


async def _find_product(session, name: str) -> Optional[Product]:
    """
    Try to find a product by common name/code fields. Prefer exact ilike,
    then fallback to contains match. Returns first match or None.
    """
    fields = ["name", "product_name", "title", "sku"]
    # Exact (ILIKE 'name')
    for f in fields:
        if hasattr(Product, f):
            stmt = select(Product).where(getattr(Product, f).ilike(name)).limit(1)
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row:
                return row
    # Contains (ILIKE '%name%')
    pattern = f"%{name}%"
    for f in fields:
        if hasattr(Product, f):
            stmt = select(Product).where(getattr(Product, f).ilike(pattern)).limit(1)
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row:
                return row
    return None


def _resolve_product_cost(product) -> float:
    """
    Try common field names to get a numeric cost/price from a Product row.
    Raises AttributeError if no price-like field exists,
    or ValueError if the value isn't numeric.
    """
    candidates = ("cost", "unit_cost", "price", "unit_price", "base_cost", "selling_price", "rate")
    for attr in candidates:
        if hasattr(product, attr):
            val = getattr(product, attr)
            if val is not None:
                try:
                    # supports Decimal, str, int, float
                    return float(val)
                except (TypeError, ValueError, InvalidOperation) as e:
                    raise ValueError(
                        f"Non-numeric value for Product.{attr}={val!r} on product "
                        f"{getattr(product, 'name', '') or getattr(product, 'id', '?')}"
                    ) from e
    raise AttributeError(
        f"Product has none of the expected price fields {candidates}. "
        f"Add one of these columns or map your schema."
    )


# ---------------- Margin Playbook ----------------
def apply_margin_rules(cost, customer_type, order_total, payment_terms, loyalty_months):
    tiers = {
        "individual": {"start": 0.275, "floor": 0.18, "sweet": (0.31, 0.33)},
        "restaurant": {"start": 0.205, "floor": 0.12, "sweet": (0.19, 0.20)},
        "chain": {"start": 0.095, "floor": 0.04, "sweet": (0.08, 0.09)},
    }
    # default to 'restaurant' tier if unknown
    tier = tiers.get(customer_type, tiers["restaurant"])
    margin = tier["start"]

    # Order size adj
    if order_total < 50000:
        margin += 0.02
    elif order_total > 250000:
        margin -= 0.02

    # Payment adj
    if payment_terms in ["net7", "prepaid"]:
        margin += 0.01
    elif payment_terms == "net30+":
        margin -= 0.01

    # Loyalty adj
    if 6 <= loyalty_months < 12:
        margin -= 0.01
    elif 12 <= loyalty_months < 24:
        margin -= 0.02
    elif loyalty_months >= 24:
        margin -= 0.03

    # Guardrails
    floor = tier["floor"]
    sweet_low, sweet_high = tier["sweet"]

    if margin < floor:
        return {"status": "needs_approval", "margin": margin, "sell_price": None}

    # Price calc
    sell_price = cost / (1 - margin) if (1 - margin) > 0 else cost

    # Rounding to .49/.99
    rounded = round(sell_price)
    if rounded % 2 == 0:
        sell_price = rounded - 0.01
    else:
        sell_price = rounded - 0.51

    status = "sweet_spot" if sweet_low <= margin <= sweet_high else "ok"
    return {"status": status, "margin": margin, "sell_price": sell_price}


# ---------------- Quotation Service ----------------
async def make_live_quotation(
    requested_items: Any,
    customer_id: Any,
    customer_type: str = "restaurant",
    payment_terms: str = "net7",
    loyalty_months: int = 0,
) -> dict:
    """
    Take requested items (any shape), fetch product costs from Postgres,
    apply margin rules, generate a vendor-style quotation,
    and email it to the customer.

    Args:
        requested_items: can be dict/list/str; will be normalized
        customer_id: numeric id or external code (CT-0001, OTW00123, etc.)
    """
    # Normalize items early so we never call .items() on a str/list
    normalized = _normalize_items(requested_items)
    if not normalized:
        raise ValueError("No valid items found in draft. Provide at least one item with quantity.")

    quotation = {
        "items": {},
        "subtotal_cost": 0.0,
        "final_total": 0.0,
        "message": "",
        "status": "draft",
    }

    async with VendorSessionLocal() as session:
        subtotal_cost = 0.0
        final_total = 0.0

        # ------- Lookup customer email (tolerant to id/code) -------
        try:
            underlying = getattr(session, "sync_session", None)
            if underlying is not None:
                customer_email = _lookup_client_email_sync(underlying, customer_id)
            else:
                customer_email = await _lookup_client_email_async(session, customer_id)
        except Exception:
            customer_email = None

        # ---------------- Process items ----------------
        for raw_name, qty in normalized.items():
            item_name = str(raw_name).strip()
            qty = _to_int(qty, 1)

            row = await _find_product(session, item_name)

            if not row:
                quotation["items"][item_name] = {
                    "requested": qty,
                    "status": "not found",
                }
                continue

            try:
                cost = _resolve_product_cost(row)
            except (ValueError, TypeError, InvalidOperation) as e:
                # If pricing data is bad, mark item but continue
                quotation["items"][getattr(row, "name", item_name) or item_name] = {
                    "requested": qty,
                    "status": f"bad_price_data: {type(e).__name__}",
                    "cost": None,
                    "unit_price": None,
                    "line_total": None,
                    "stock": getattr(row, "stock_quantity", None),
                    "applied_margin": None,
                }
                continue
            except AttributeError:
                # No known price field; treat as not priceable
                quotation["items"][getattr(row, "name", item_name) or item_name] = {
                    "requested": qty,
                    "status": "no_price_field",
                    "cost": None,
                    "unit_price": None,
                    "line_total": None,
                    "stock": getattr(row, "stock_quantity", None),
                    "applied_margin": None,
                }
                continue

            line_cost = cost * qty
            subtotal_cost += line_cost

            margin_result = apply_margin_rules(
                cost=cost,
                customer_type=customer_type,
                order_total=subtotal_cost,
                payment_terms=payment_terms,
                loyalty_months=loyalty_months,
            )

            if margin_result["status"] == "needs_approval":
                sell_price = None
                line_total = None
                item_status = "below_floor_needs_approval"
            else:
                sell_price = margin_result["sell_price"]
                line_total = round(sell_price * qty, 2)
                final_total += line_total
                item_status = margin_result["status"]

            quotation["items"][getattr(row, "name", item_name) or item_name] = {
                "requested": qty,
                "cost": float(cost),
                "unit_price": float(sell_price) if sell_price is not None else None,
                "line_total": float(line_total) if line_total is not None else None,
                "status": item_status,
                "stock": getattr(row, "stock_quantity", None),
                "applied_margin": round(margin_result["margin"], 4) if margin_result.get("margin") is not None else None,
            }

        quotation["subtotal_cost"] = round(subtotal_cost, 2)
        quotation["final_total"] = round(final_total, 2)

        # Messaging
        if any(i["status"] == "below_floor_needs_approval" for i in quotation["items"].values()):
            quotation["status"] = "needs_ops_approval"
            quotation["message"] = "Some items fell below floor margin and need Ops/Finance approval."
        elif all(i.get("status") == "sweet_spot" for i in quotation["items"].values() if "status" in i):
            quotation["status"] = "confirmed"
            quotation["message"] = f"Your quote is within our preferred tier. Final total: PKR {quotation['final_total']}."
        else:
            quotation["status"] = "review"
            quotation["message"] = f"Draft quotation prepared. Total: PKR {quotation['final_total']}."

        # ---------------- Send Email ----------------
        try:
            if customer_email:
                subject = "Your Quotation from Vendor"
                # Build a small HTML summary list for items that have prices
                lines = []
                for name, i in quotation["items"].items():
                    if i.get("unit_price"):
                        lines.append(f"<li>{i['requested']} × {name} @ {i['unit_price']} → {i['line_total']}</li>")
                body = f"""
                <h2>Quotation Summary</h2>
                <ul>{''.join(lines)}</ul>
                <p><b>Subtotal:</b> PKR {quotation['subtotal_cost']}</p>
                <p><b>Final Total:</b> PKR {quotation['final_total']}</p>
                <p>Status: {quotation['status']}</p>
                <p>{quotation['message']}</p>
                """
                send_email(customer_email, subject, body)
        except Exception:
            # Email failures shouldn't crash quoting
            pass

    return quotation
