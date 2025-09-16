"""
LLM Vendor Quotation Service (LangChain + Groq) with model fallback.
- Uses GROQ_API_KEY from env
- Tries env model first (LLM_VENDOR_QUOTE_MODEL), then recommended fallbacks:
  1) llama-3.3-70b-versatile   (recommended successor)
  2) llama-3.1-8b-instant      (smaller/faster backup)
- If all fail, renders a deterministic plain-text fallback.

Exports:
- generate_vendor_quotation_text(quotation: dict, customer: dict) -> (text, meta)
- generate_vendor_email(quotation: dict, customer: dict) -> str
"""

from __future__ import annotations
import os, json
from datetime import datetime
from typing import Any, Dict, Tuple

from langchain.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

# -- Candidate order: env override -> recommended -> small backup
_DEFAULT_CANDIDATES = [
    os.getenv("LLM_VENDOR_QUOTE_MODEL", "").strip() or None,
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

SYSTEM_PROMPT = (
    "You are a helpful vendor generating professional quotations.\n"
    "Output *plain text only* (no markdown/code blocks). Keep it clear, concise, and human.\n"
    "Use numbers from the provided pricing JSON verbatim; do not invent figures.\n"
)

HUMAN_PROMPT = """
Create a detailed quotation for order {order_ref} for customer {customer_id}.
Phone: {phone_number}
Notes: {notes}

Items (as provided by caller):
{items}

Pricing engine output (authoritative numbers; use verbatim):
{quotation_json}

Format it nicely with:
- Quotation header (Company, Order Ref, Date)
- Itemized table (Qty | Item | Unit Price | Line Total), monospaced alignment
- Subtotal and Final Total (use provided numbers)
- Short 'Notes' for any unpriced/pending items with reason
- Brief thank-you signoff as the Vendor team

Return only the final plain-text quotation body. No extra commentary.
"""

_prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", HUMAN_PROMPT)])


def _json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)


def _fallback_render(quotation: Dict[str, Any], customer: Dict[str, Any]) -> str:
    """Deterministic plain-text render if LLM is unavailable."""
    order_ref = str(customer.get("id") or customer.get("_id") or customer.get("customer_id") or "")
    phone = customer.get("phone_number") or "-"
    notes = (customer.get("notes") or "").strip()
    company = os.getenv("VENDOR_COMPANY_NAME", "Vendor")

    header = "Qty  Item                           Unit Price     Line Total"
    line = "-" * len(header)
    rows = [header, line]
    unpriced = []

    items = quotation.get("items") or {}
    def money(n):
        try: return f"PKR {float(n):,.2f}"
        except Exception: return str(n)

    for name, it in items.items():
        qty = it.get("requested", 0)
        unit = it.get("unit_price")
        total = it.get("line_total")
        status = it.get("status") or "pending"
        if unit is not None and total is not None:
            rows.append(f"{str(qty):>3}  {name[:30]:<30}  {money(unit):>12}  {money(total):>12}")
        else:
            unpriced.append(f"- {qty} × {name} ({status})")

    if len(rows) == 2:
        rows.append("(no priced items)")

    final_total = quotation.get("final_total")
    final_total_str = money(final_total if final_total is not None else 0)

    body = [
        f"{company} — Quotation",
        f"Order Ref: {order_ref}",
        f"Date: {datetime.now().strftime('%Y-%m-%d')}",
        f"Phone: {phone}",
        "",
        *rows,
        "-" * len(header),
        f"Final Total: {final_total_str}",
    ]
    if unpriced:
        body += ["", "Notes:", *unpriced]
    if notes:
        body += ["", "Customer Notes:", notes]
    body += ["", "Thank you for considering us.", f"{company} Team"]
    return "\n".join(body).strip()


def _try_invoke(model: str, messages):
    """Attempt a single model; return (text, meta) or (None, err_str)."""
    try:
        llm = ChatGroq(model=model, api_key=os.getenv("GROQ_API_KEY", ""), temperature=0.2)
        resp = llm.invoke(messages)
        content = (resp.content or "").strip()
        if not content:
            return None, "empty_response"
        meta = {
            "provider": "groq",
            "model": model,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "raw_len": len(content),
        }
        return content, meta
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def generate_vendor_quotation_text(quotation: Dict[str, Any], customer: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Produce a vendor-style plain-text quotation via Groq LLM with automatic model fallback.
    Returns (text, meta). Falls back to deterministic render on failure.
    """
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        text = _fallback_render(quotation, customer)
        return text, {"provider": "fallback", "model": None, "generated_at": datetime.utcnow().isoformat() + "Z"}

    order_ref = str(customer.get("id") or customer.get("_id") or customer.get("customer_id") or "")
    messages = _prompt.format_messages(
        order_ref=order_ref,
        customer_id=customer.get("customer_id") or "",
        phone_number=customer.get("phone_number") or "",
        notes=customer.get("notes") or "",
        items=_json(customer.get("items")),
        quotation_json=_json(quotation),
    )

    tried = []
    for m in [c for c in _DEFAULT_CANDIDATES if c]:
        text, meta_or_err = _try_invoke(m, messages)
        if text:
            return text, meta_or_err
        tried.append({"model": m, "error": meta_or_err})

    text = _fallback_render(quotation, customer)
    return text, {
        "provider": "fallback",
        "model": None,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "tried": tried,
    }


# ---------------- New: Generate full email body ----------------
async def generate_vendor_email(quotation: Dict[str, Any], customer: Dict[str, Any]) -> str:
    """
    Use Groq LLM to generate a full professional email body
    (greeting, context, embedded quotation, sign-off).
    """
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        plain, _ = generate_vendor_quotation_text(quotation, customer)
        return (
            "Dear Customer,\n\n"
            "Please find below your quotation:\n\n"
            f"{plain}\n\n"
            "Best regards,\nVendor Team"
        )

    quotation_text = _json(quotation)
    prompt = f"""
    You are a vendor preparing a business quotation email.

    Customer context: {customer}

    Quotation JSON:
    {quotation_text}

    Please write a professional, polite email body including:
    - Greeting
    - Short context (acknowledging their request)
    - Nicely formatted quotation table or summary
    - Closing with vendor name/contact
    Return only the plain-text email body.
    """

    model = _DEFAULT_CANDIDATES[0] or "llama-3.3-70b-versatile"
    llm = ChatGroq(model=model, api_key=api_key, temperature=0.3)

    try:
        resp = await llm.ainvoke(prompt)
        return (resp.content or "").strip()
    except Exception as e:
        plain, _ = generate_vendor_quotation_text(quotation, customer)
        return (
            f"Dear Customer,\n\nHere is your quotation:\n\n{plain}\n\n"
            f"(LLM error: {type(e).__name__}: {e})\n\n"
            "Best regards,\nVendor Team"
        )
