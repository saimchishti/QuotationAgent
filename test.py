# # # import asyncio
# # # from app.services.customer_verification_service import verify_customer_by_phone

# # # async def main():
# # #     # Replace this with a real phone number from your vendors DB
# # #     test_phone_existing = "795-852-6581"  
# # #     test_phone_missing = "9999999999"

# # #     print("\n=== Testing existing phone ===")
# # #     print(await verify_customer_by_phone(test_phone_existing))

# # #     print("\n=== Testing missing phone ===")
# # #     print(await verify_customer_by_phone(test_phone_missing))

# # # if __name__ == "__main__":
# # #     asyncio.run(main())
# # import asyncio
# # import json

# # # 👉 import your actual tool functions
# # # If you put them in app/tools/caller_agent_tools.py, adjust the import below:
# # from app.tools.caller_agent_tools import (
# #     customer_verification_tool,
# #     register_customer_for_order_tool,
# # )

# # # Pick numbers you control
# # PHONE_EXISTING = "+1 (555) 000-1234"  # replace with a number that exists in vendors DB
# # PHONE_UNKNOWN  = "+1 (555) 111-2222"  # replace with a number that does NOT exist


# # async def test_verification_existing():
# #     print("\n=== customer_verification (existing) ===")
# #     res = await customer_verification_tool.ainvoke({"phone": PHONE_EXISTING})
# #     print(res)                         # JSON string
# #     print(json.loads(res))             # as dict


# # async def test_verification_missing():
# #     print("\n=== customer_verification (missing) ===")
# #     res = await customer_verification_tool.ainvoke({"phone": PHONE_UNKNOWN})
# #     print(res)
# #     print(json.loads(res))


# # async def test_register_missing_then_verify():
# #     print("\n=== register_customer_for_order (create unknown) ===")
# #     # Intentionally use the unknown phone
# #     payload = {
# #         "phone": PHONE_UNKNOWN,
# #         "business_name": "Acme Foods",
# #         "full_name": "Alex Rivera",     # or first_name + last_name
# #         "email": "alex@example.com",
# #         "service_required": "Weekly supplies",
# #         "notes": "Called to set up a regular order",
# #         "source_channel": "phone-call",
# #     }
# #     res = await register_customer_for_order_tool.ainvoke(payload)
# #     print(res)
# #     print(json.loads(res))

# #     # Verify again – now it should be found
# #     print("\n=== customer_verification (after create) ===")
# #     res2 = await customer_verification_tool.ainvoke({"phone": PHONE_UNKNOWN})
# #     print(res2)
# #     print(json.loads(res2))


# # async def main():
# #     # Run whichever tests you need
# #     await test_verification_existing()
# #     await test_verification_missing()
# #     await test_register_missing_then_verify()


# # if __name__ == "__main__":
# #     asyncio.run(main())


# import asyncio
# from app.services.item_availability_service import check_item_availability

# async def main():
#     test_item = "Tomatoes"

#     print(f"=== Checking availability for: {test_item} ===")
#     result = await check_item_availability(test_item)
#     print(result)

# if __name__ == "__main__":
#     asyncio.run(main())
# scripts/test_submit_order.py
# scripts/test_submit_from_draft.py
# test_create_draft.py
# scripts/test_submit_order_end_to_end.py
# scripts/test_submit_order.py
# # import asyncio, json
# from sqlalchemy import select
# from app.db.session import VendorSessionLocal
# from app.db.vendors_models import VdInventory
# from app.services.order_draft_service import create_order_draft_service
# from app.services.order_submit_service import submit_order_service

# PHONE = "5976044626"

# async def pick_inventory_items(limit: int = 2):
#     async with VendorSessionLocal() as s:
#         rows = (await s.execute(select(VdInventory).limit(limit))).scalars().all()
#         return [{"item_id": r.inventory_id, "qty": 1} for r in rows]

# async def main():
#     items = await pick_inventory_items()
#     if not items:
#         print("❌ No inventory rows exist. Add at least one item to vendors.inventory.")
#         return

#     draft = await create_order_draft_service(
#         phone=PHONE,
#         line_items=items,
#         notes="E2E test draft"
#     )
#     print("\n--- DRAFT ---")
#     print(json.dumps(draft, indent=2, default=str))
#     if "error" in draft:
#         return

#     res = await submit_order_service(
#         draft["draft_id"],
#         payment_method="cash",
#         payment_status="paid",
#         delivery_status="processing",
#     )
#     print("\n--- SUBMIT RESULT ---")
#     print(json.dumps(res, indent=2, default=str))

# if __name__ == "__main__":
#     asyncio.run(main())
# app/services/insert_test_draft.py
# insert_test_draft.py
# import asyncio
# from app.db.mongo_models import OrderDraft, post_doc

# async def main():
#     draft = OrderDraft(
#         customer_id="1",
#         phone_number="555-1234",
#         items={"burger": 2, "fries": 1},
#         notes="extra ketchup",
#         status="draft"
#     )
#     inserted_id = post_doc("order_drafts", draft)
#     print("✅ Inserted test draft:", inserted_id)

# if __name__ == "__main__":
#     asyncio.run(main())


# import asyncio
# from app.services.live_quotation_service import make_live_quotation

# async def main():
#     # Example customer request (replace with real product names from your DB)
#     requested_items = {"Sample Item": 5, "Butter Croissant": 2}

#     quotation = await make_live_quotation(requested_items)
#     print("🧾 Vendor Quotation:\n", quotation)

# if __name__ == "__main__":
# #     asyncio.run(main())

# import os
# import sys
# from datetime import datetime, timezone

# # Ensure project root is in sys.path
# sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# from app.db.session import get_collection


# def insert_test_draft():
#     collection = get_collection("order_drafts")
#     draft = {
#         "customer_id": "ACC002",
#         "phone_number": "555-43211",
#         "items": {"Sample Item": 5, "Butter Croissant": 2},
#         "notes": "quotation test draft",
#         "status": "draft",
#         "created_at": datetime.now(timezone.utc),
#         "updated_at": datetime.now(timezone.utc),
#     }
#     result = collection.insert_one(draft)
#     print(f"✅ Inserted draft with _id={result.inserted_id}")


# if __name__ == "__main__":
#     insert_test_draft()

#!/usr/bin/env python3
"""
 gmail_quote_agent_plus.py — thread-aware, memory-enabled, discount-policy version

What’s new vs your previous script
- Adds a lightweight persistent memory (JSON file) keyed by Gmail thread-id and by contact email.
  • Remembers last order refs (PO/RFQ/Quote numbers), last quoted totals/discounts, and the last active thread per contact.
- Stronger intent detection with both heuristics + optional Groq check (classify: acceptance / requote / question / OOO-bounce / unrelated).
- Conversational acceptance replies (still clear + professional) with next steps and gentle asks for missing info.
- Safer auto-reply guard (skips out-of-office, bounces, bulk/list mail, no-reply senders, etc.).
- Better IMAP resilience (auto-reconnect loops, conservative IDLE usage, startup catch-up, duplicate suppression).
- Uses full thread context (limited by MAX_THREAD_* env) and feeds summary + memory into the Groq prompts.

ENV (.env supported via python-dotenv)
  # Incoming (IMAP)
  IMAP_HOST=imap.gmail.com
  IMAP_PORT=993
  IMAP_FOLDER=INBOX

  # Outgoing (SMTP)
  SMTP_SERVER=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USERNAME=you@gmail.com
  SMTP_PASSWORD=xxxx xxxx xxxx xxxx   # Gmail App Password (spaces OK)

  # Groq LLM
  GROQ_API_KEY=sk_...
  LLM_VENDOR_QUOTE_MODEL=llama-3.3-70b-versatile   # optional override

  # Discount policy
  BASE_DISCOUNT_PCT=10
  FINAL_DISCOUNT_PCT=20

  # Thread/context controls (optional)
  MAX_THREAD_MESSAGES=12
  MAX_THREAD_CHARS=14000

  # Memory (optional)
  MEMORY_FILE=.agent_memory.json   # default at repo root
  COMPANY_NAME=Your Company Pvt Ltd
  SALES_NAME=Sales Team
  DEFAULT_CURRENCY=PKR

  # Runtime knobs (optional)
  IDLE_HEARTBEAT_SECS=60
  RECONNECT_BACKOFF_SECS=5
  PROMPT_IF_MISSING=false
  DRY_RUN=false                      # if true, logs the reply instead of sending

Install:
  pip install imapclient python-dotenv groq

Run:
  python gmail_quote_agent_plus.py
"""

from __future__ import annotations
import os
import re
import ssl
import time
import json
import atexit
import socket
import smtplib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional
from email import message_from_bytes
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import parseaddr, formataddr, make_msgid

from imapclient import IMAPClient
from dotenv import load_dotenv
from groq import Groq

# ------------------------- Load .env -----------------------------------------
load_dotenv(os.getenv("ENV_FILE") or ".env")

# IMAP config (receive)
IMAP_HOST   = os.getenv("IMAP_HOST", "imap.gmail.com").strip()
IMAP_PORT   = int(os.getenv("IMAP_PORT", "993"))
IMAP_FOLDER = os.getenv("IMAP_FOLDER", "INBOX").strip()

# SMTP config (send)
SMTP_SERVER   = os.getenv("SMTP_SERVER", "smtp.gmail.com").strip()
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = (os.getenv("SMTP_USERNAME") or os.getenv("GMAIL_USER") or "").strip()
SMTP_PASSWORD = (os.getenv("SMTP_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD") or "").replace(" ", "").strip()

# Identity / formatting
COMPANY_NAME = os.getenv("COMPANY_NAME", "Your Company Pvt Ltd").strip()
SALES_NAME   = os.getenv("SALES_NAME", "Sales").strip()
DEFAULT_CCY  = os.getenv("DEFAULT_CURRENCY", "PKR").strip()

# Groq LLM
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
LLM_MODEL    = (os.getenv("LLM_VENDOR_QUOTE_MODEL") or "llama-3.3-70b-versatile").strip()

# Discount policy

def _pct_env(name: str, default: int) -> int:
    try:
        v = int(os.getenv(name, str(default)).strip())
        return max(0, min(95, v))  # sanity cap
    except Exception:
        return default

BASE_DISCOUNT_PCT = _pct_env("BASE_DISCOUNT_PCT", 10)   # default 10%
FINAL_DISCOUNT_PCT = _pct_env("FINAL_DISCOUNT_PCT", 20) # default 20% (final, do-not-exceed)

# Options
IDLE_HEARTBEAT_SECS    = int(os.getenv("IDLE_HEARTBEAT_SECS", "60"))
RECONNECT_BACKOFF_SECS = int(os.getenv("RECONNECT_BACKOFF_SECS", "5"))
PROMPT_IF_MISSING      = os.getenv("PROMPT_IF_MISSING", "false").lower() in ("1", "true", "yes")
DRY_RUN                = os.getenv("DRY_RUN", "false").lower() in ("1", "true", "yes")

# Thread/context limits
MAX_THREAD_MESSAGES = int(os.getenv("MAX_THREAD_MESSAGES", "12"))
MAX_THREAD_CHARS    = int(os.getenv("MAX_THREAD_CHARS", "14000"))

# Memory
MEMORY_FILE = os.getenv("MEMORY_FILE", ".agent_memory.json").strip()

# ------------------------- Utils --------------------------------------------

def ts_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def decode_str(s: Optional[str]) -> str:
    if s is None:
        return ""
    try:
        return str(make_header(decode_header(s)))
    except Exception:
        return s

def get_text_body(msg) -> str:
    """Return a best-effort plain-text body."""
    if msg.is_multipart():
        # Prefer text/plain (non-attachment)
        for part in msg.walk():
            ctype = (part.get_content_type() or "").lower()
            disp = (part.get("Content-Disposition") or "").lower()
            if "attachment" in disp:
                continue
            if ctype == "text/plain":
                try:
                    return part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
                except Exception:
                    pass
        # Fallback to stripped HTML
        for part in msg.walk():
            ctype = (part.get_content_type() or "").lower()
            disp = (part.get("Content-Disposition") or "").lower()
            if "attachment" in disp:
                continue
            if ctype == "text/html":
                try:
                    html = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
                    return re.sub(r"<[^>]+>", "", html)
                except Exception:
                    pass
    else:
        ctype = (msg.get_content_type() or "").lower()
        payload = msg.get_payload(decode=True) or b""
        try:
            content = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
        except Exception:
            content = payload.decode("utf-8", errors="replace")
        if ctype == "text/plain":
            return content
        if ctype == "text/html":
            return re.sub(r"<[^>]+>", "", content)
    return ""

def is_from_self(msg) -> bool:
    from_ = parseaddr(decode_str(msg.get("From")))[1].lower()
    me    = (SMTP_USERNAME or "").lower()
    return from_ == me or from_ == (os.getenv("GMAIL_USER", "").lower())

# --- Autoresponder / bounce / bulk guards -----------------------------------

NOREPLY_RE = re.compile(r"no-?reply|noreply|donotreply|no[-_.]response", re.I)

OOO_HINTS = (
    "out of office",
    "oof",
    "vacation auto-reply",
    "auto-reply",
    "autoreply",
)

BOUNCE_HINTS = (
    "delivery status notification",
    "mail delivery subsystem",
    "mailer-daemon",
    "undeliverable",
    "returned mail",
)

def should_skip_autoresponder(msg, subject: str, body: str) -> bool:
    # Headers first
    h_auto = (msg.get("Auto-Submitted") or "").lower()
    if h_auto and h_auto != "no":
        return True
    precedence = (msg.get("Precedence") or "").lower()
    if precedence in {"bulk", "list", "junk"}:
        return True
    x_ars = (msg.get("X-Auto-Response-Suppress") or "").lower()
    if "all" in x_ars or "autoreply" in x_ars:
        return True

    # From address like no-reply@
    from_email = parseaddr(decode_str(msg.get("From")))[1]
    if NOREPLY_RE.search(from_email or ""):
        return True

    # Subject/body hints
    text = f"{subject}\n{body}".lower()
    if any(h in text for h in OOO_HINTS):
        return True
    if any(h in text for h in BOUNCE_HINTS):
        return True
    return False

# ---------- Thread utilities (Gmail X-GM-THRID) ------------------------------

def fetch_thread_uids(server: IMAPClient, any_uid: int) -> tuple[list[int], Optional[int]]:
    info = server.fetch([any_uid], ["X-GM-THRID"])
    thrid = info.get(any_uid, {}).get(b"X-GM-THRID")
    if thrid is None:
        return [any_uid], None
    try:
        uids = server.search(["X-GM-THRID", thrid])
    except Exception:
        return [any_uid], thrid
    return sorted(uids), thrid

@dataclass
class ThreadMemory:
    subject: str = ""
    contact: str = ""
    order_refs: List[str] = None
    last_total: str = ""
    last_discount_pct: int = 0
    currency: str = DEFAULT_CCY
    summary: str = ""   # free-form
    updated_at: str = ""

    def to_json(self) -> Dict[str, Any]:
        d = asdict(self)
        d["order_refs"] = self.order_refs or []
        return d

class MemoryStore:
    def __init__(self, path: str):
        self.path = path
        self.data: Dict[str, Any] = {"threads": {}, "contacts": {}}
        self._load()
        atexit.register(self._save)

    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
        except Exception:
            self.data = {"threads": {}, "contacts": {}}

    def _save(self):
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except Exception as e:
            print(f"[warn] Could not save memory: {e}")

    # --- Thread memory ---
    def get_thread(self, thrid: str) -> ThreadMemory:
        obj = self.data.get("threads", {}).get(thrid) or {}
        tm = ThreadMemory(
            subject=obj.get("subject", ""),
            contact=obj.get("contact", ""),
            order_refs=obj.get("order_refs", []),
            last_total=obj.get("last_total", ""),
            last_discount_pct=int(obj.get("last_discount_pct", 0) or 0),
            currency=obj.get("currency", DEFAULT_CCY),
            summary=obj.get("summary", ""),
            updated_at=obj.get("updated_at", ""),
        )
        return tm

    def set_thread(self, thrid: str, tm: ThreadMemory):
        self.data.setdefault("threads", {})[thrid] = tm.to_json()
        self._save()

    # --- Contact memory ---
    def get_contact(self, email: str) -> Dict[str, Any]:
        return self.data.get("contacts", {}).get(email.lower(), {})

    def set_contact(self, email: str, **kwargs):
        email = email.lower()
        c = self.data.setdefault("contacts", {}).get(email) or {}
        c.update(kwargs)
        c["updated_at"] = ts_iso()
        self.data["contacts"][email] = c
        self._save()

MEM = MemoryStore(MEMORY_FILE)

# ------------------------- Summaries / extraction ----------------------------

ORDER_REF_RE = re.compile(r"\b(?:PO|P/O|RFQ|R/F/Q|Quote|Quotation|Order|Enquiry|Inquiry|SO|Sales\s*Order)\s*[#:]?\s*([A-Za-z0-9._-]{3,})\b", re.I)
MONEY_RE = re.compile(r"(?:PKR|Rs\.?|USD|AED|QAR|SAR|EUR|GBP|INR)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.I)
DISCOUNT_RE = re.compile(r"([1-9][0-9]?)\s*%\s*(?:discount|off)", re.I)


def extract_order_refs(text: str) -> List[str]:
    refs = []
    for m in ORDER_REF_RE.finditer(text or ""):
        refs.append(m.group(1))
    # de-dup, preserve order
    seen = set()
    uniq = []
    for r in refs:
        if r.lower() not in seen:
            uniq.append(r)
            seen.add(r.lower())
    return uniq[:5]


def build_thread_context(server: IMAPClient, uids: list[int]) -> tuple[str, list[str]]:
    """Build a compact plaintext conversation log and collect References."""
    if not uids:
        return "", []
    fetched = server.fetch(uids, ["RFC822", "INTERNALDATE", "ENVELOPE"])  # noqa

    def _sort_key(uid):
        meta = fetched.get(uid, {})
        return meta.get(b"INTERNALDATE") or 0

    ordered = sorted(uids, key=_sort_key)

    lines: List[str] = []
    total_len = 0
    refs: List[str] = []

    def add_chunk(chunk: str):
        nonlocal total_len
        if total_len >= MAX_THREAD_CHARS:
            return
        remaining = MAX_THREAD_CHARS - total_len
        piece = chunk if len(chunk) <= remaining else (chunk[:remaining].rstrip() + "…")
        lines.append(piece)
        total_len += len(piece)

    if len(ordered) > MAX_THREAD_MESSAGES:
        ordered = ordered[-MAX_THREAD_MESSAGES:]

    for uid in ordered:
        raw = fetched[uid][b"RFC822"]
        msg = message_from_bytes(raw)
        frm = decode_str(msg.get("From"))
        subj = decode_str(msg.get("Subject"))
        dt   = decode_str(msg.get("Date"))
        mid  = msg.get("Message-ID")
        if mid:
            refs.append(mid)

        body = get_text_body(msg).strip()
        body = re.sub(r"\s+", " ", body)
        header = f"From: {frm}\nDate: {dt}\nSubject: {subj}\n"
        sep = "-" * 68
        add_chunk(f"{sep}\n{header}\n{body}\n")

    thread_text = "\n".join(lines).strip()
    return thread_text, refs

# ------------------------- Groq helpers --------------------------------------

class LLM:
    def __init__(self, api_key: str, model: str):
        self.client = Groq(api_key=api_key) if api_key else None
        self.model = model

    def chat(self, system: str, user: str, temperature: float = 0.2) -> str:
        if not self.client:
            raise RuntimeError("Groq API key not set")
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            temperature=temperature,
        )
        return (resp.choices[0].message.content or "").strip()

LLM_CLIENT = LLM(GROQ_API_KEY, LLM_MODEL) if GROQ_API_KEY else None

# ---- Intent classification (heuristics + optional LLM confirmation) ---------

ACCEPTANCE_KW = [
    "accept the order", "accept this order", "we accept", "accepted",
    "order confirmed", "confirm the order", "confirmed", "proceed with the order",
    "go ahead", "place the order", "approved the quote", "approve this quote",
    "we are placing the order", "book the order", "we confirm", "raise the po",
]

PUSHBACK_KW = [
    "more discount", "extra discount", "better price", "lower price", "too high",
    "negotiate", "negotiate further", "reduce price", "can you do better",
    "final price", "best price", "last price", "your best", "lowest you can",
    "sharpen your pencil", "match competitor", "price match", "tight budget",
]

QUESTION_KW = ["clarify", "question", "details", "lead time", "delivery", "warranty", "datasheet"]


def heuristic_classify(subject: str, body: str) -> str:
    text = f"{subject}\n{body}".lower()
    if any(kw in text for kw in ACCEPTANCE_KW):
        return "acceptance"
    if should_skip_autoresponder_stub(text):
        return "skip"
    if any(kw in text for kw in PUSHBACK_KW):
        return "requote"  # we’ll escalate to FINAL in logic
    if any(kw in text for kw in QUESTION_KW) or "?" in text:
        return "question"
    # default path is requote (per your policy)
    return "requote"


def should_skip_autoresponder_stub(text: str) -> bool:
    # a light-weight helper for the heuristic_classify fast-path
    text = text.lower()
    return any(h in text for h in OOO_HINTS) or any(h in text for h in BOUNCE_HINTS)


def llm_classify(subject: str, body: str, thread_summary: str) -> Optional[str]:
    if not LLM_CLIENT:
        return None
    system = (
        "You classify emails for a B2B vendor. Return one of: "
        "acceptance | requote | question | skip | unrelated. "
        "'skip' means OOO/bounce/bulk/autoresponder. Use the thread summary for context."
    )
    user = f"""
Subject: {subject}
Latest body: {body[:1200]}
Thread summary: {thread_summary[:2000]}
Answer with ONLY one word from the allowed set.
"""
    try:
        out = LLM_CLIENT.chat(system, user, temperature=0)
        ans = out.strip().split()[0].lower()
        if ans in {"acceptance", "requote", "question", "skip", "unrelated"}:
            return ans
    except Exception as e:
        print(f"[warn] Groq classify error: {e}")
    return None

# ------------------------- Reply composers -----------------------------------

def craft_acceptance_reply(subject: str, body: str, tm: ThreadMemory) -> str:
    greeting = "Thanks for your confirmation!" if body else "Thanks for confirming the order!"
    refs = f" (ref: {', '.join(tm.order_refs)})" if tm.order_refs else ""
    who = SALES_NAME or "Sales"
    lines = [
        f"{greeting}{refs}",
        "\nGreat — we’re now moving this to fulfillment.",
        "Next steps:",
        "1) We’ll share the invoice for approval and payment.",
        "2) Once paid, we’ll book delivery (typ. 5–7 working days).",
        "3) We’ll keep you updated with tracking / delivery schedule.",
    ]
    # Gentle ask for missing info
    asks = []
    if not tm.last_total:
        asks.append("latest quoted total")
    if not tm.order_refs:
        asks.append("your PO/Order reference")
    if asks:
        lines.append("\nIf you can, please share: " + ", ".join(asks) + ".")
    lines.append("\nThank you for choosing us. If anything changes, just hit reply — we’re here to help.")
    lines.append(f"\nBest regards,\n{who}\n{COMPANY_NAME}")
    return "\n".join(lines)


def craft_question_reply(subject: str, body: str, tm: ThreadMemory) -> str:
    # A concise, helpful answer request — we’ll route to Groq if available to propose answers,
    # but keep it safe and brief if the LLM is not set.
    who = SALES_NAME or "Sales"
    if not LLM_CLIENT:
        return (
            f"Thanks for the questions regarding your quotation{(' (ref: ' + ', '.join(tm.order_refs) + ')') if tm.order_refs else ''}.\n"
            "We’ll be happy to clarify specs, lead time, and payment. If you can share the exact items/quantities, we’ll tailor the details and confirm availability.\n\n"
            f"Best regards,\n{who}\n{COMPANY_NAME}"
        )
    try:
        system = (
            "You answer brief customer questions about a quotation. "
            "Respond in plain text, concise, friendly, and professional. If missing facts, ask just what is needed."
        )
        user = f"""
Subject: {subject}
Customer message: {body[:1800]}
Known context: order refs={tm.order_refs}, last total={tm.last_total}, currency={tm.currency}
Keep it under 140 words.
"""
        out = LLM_CLIENT.chat(system, user, temperature=0.3)
        return out
    except Exception as e:
        print(f"[warn] Groq question reply error: {e}")
        return (
            f"Thanks for reaching out. Happy to help — could you share a bit more detail so we can answer precisely?\n\n"
            f"Best regards,\n{who}\n{COMPANY_NAME}"
        )


def craft_requote_reply(email_subject: str, latest_email_body: str, thread_text: str,
                        tm: ThreadMemory, escalate_to_final: bool) -> str:
    if not LLM_CLIENT:
        pct = FINAL_DISCOUNT_PCT if escalate_to_final else BASE_DISCOUNT_PCT
        tag = " (final)" if escalate_to_final else ""
        who = SALES_NAME or "Sales"
        return (
            f"Thanks for your message.\n\n"
            f"Here is our revised quotation with {pct}%{tag} discount."
            f"\n- Please share items/quantities or your last quote so we can compute the exact totals in {tm.currency or DEFAULT_CCY}.\n\n"
            "Terms:\n- Price validity: 7 days\n- Delivery: 5–7 working days after PO\n- Payment: Advance or Net 7\n\n"
            f"Best regards,\n{who}\n{COMPANY_NAME}"
        )

    target_pct = FINAL_DISCOUNT_PCT if escalate_to_final else BASE_DISCOUNT_PCT
    final_line = (f"Offer exactly {FINAL_DISCOUNT_PCT}% discount as FINAL and state clearly that "
                  f"{FINAL_DISCOUNT_PCT}% is our best and final; do not offer or imply any higher discount.")
    base_line = f"Offer exactly {BASE_DISCOUNT_PCT}% discount, and do NOT exceed {FINAL_DISCOUNT_PCT}% under any circumstances."

    system_prompt = (
        "You are a meticulous B2B sales quoting assistant for a vendor in Pakistan. "
        "Write brief, professional email replies in PLAIN TEXT (no HTML/markdown). "
        "Use the full email thread and the memory below to stay conversational and consistent.\n\n"
        "Discount policy:\n"
        f"- BASE discount: {BASE_DISCOUNT_PCT}%\n"
        f"- FINAL discount cap: {FINAL_DISCOUNT_PCT}%\n"
        f"- For this reply, apply EXACTLY {target_pct}% discount. {(final_line if escalate_to_final else base_line)}\n"
        "- Apply the discount to the latest vendor-quoted prices in the thread. If no prices exist, state the offered discount percentage and ask for the missing details in ONE sentence.\n"
        "- Show line items, subtotal, discount, taxes if mentioned, and GRAND TOTAL. Keep the currency from memory/thread (default PKR).\n"
        "- Include standard terms: validity 7 days, delivery 5–7 working days ARO, payment terms (Advance / Net 7). Keep it compact and actionable. No tables—use clean, fixed-width text."
    )

    memory_blob = (
        f"Known memory: refs={tm.order_refs}, last_total={tm.last_total}, last_discount={tm.last_discount_pct}%, currency={tm.currency}.\n"
        f"Thread subject: {tm.subject}\n"
        f"Thread summary: {tm.summary[:1000]}"
    )

    user_prompt = f"""
Thread Subject: {email_subject}
==== MEMORY ====
{memory_blob}
==== FULL EMAIL THREAD (oldest → newest) ====
{thread_text[:MAX_THREAD_CHARS]}
==== LATEST CUSTOMER MESSAGE (body only) ====
{latest_email_body.strip()[:4000]}
Task: Compose a ready-to-send PLAIN TEXT reply email with a revised quotation applying the exact discount policy above.
"""

    try:
        out = LLM_CLIENT.chat(system_prompt, user_prompt, temperature=0.25)
        return out
    except Exception as e:
        print(f"[warn] Groq requote error: {e}")
        pct = target_pct
        who = SALES_NAME or "Sales"
        tag = " (final)" if escalate_to_final else ""
        return (
            f"Thanks for your message.\n\nHere is our revised quotation with {pct}%{tag} discount.\n"
            "- [Temporary issue preparing final numbers] Please confirm items/quantities and last quoted prices.\n\n"
            "Terms:\n- Price validity: 7 days\n- Delivery: 5–7 working days after PO\n- Payment: Advance or Net 7\n\n"
            f"Best regards,\n{who}\n{COMPANY_NAME}"
        )

# ------------------------- SMTP ---------------------------------------------

def safe_subject_reply(subject: str) -> str:
    if not subject:
        return "Re: Your quotation"
    return subject if subject.lower().startswith("re:") else f"Re: {subject}"


def make_smtp() -> smtplib.SMTP:
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
    server.ehlo()
    server.starttls(context=ssl.create_default_context())
    server.ehlo()
    server.login(SMTP_USERNAME, SMTP_PASSWORD)
    return server


def send_reply(original_msg, reply_text: str, subject_override: Optional[str] = None,
               references_chain: Optional[List[str]] = None):
    to_email = parseaddr(decode_str(original_msg.get("From")))[1]
    if not to_email:
        print("[warn] No valid From address to reply to; skipping send.")
        return

    subj = subject_override or safe_subject_reply(decode_str(original_msg.get("Subject")))
    in_reply_to = original_msg.get("Message-ID")
    references = list(references_chain or [])
    if in_reply_to and in_reply_to not in references:
        references.append(in_reply_to)

    msg = EmailMessage()
    msg["From"] = formataddr((SALES_NAME or "Sales", SMTP_USERNAME))
    msg["To"] = to_email
    msg["Subject"] = subj
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = " ".join(references[-20:])
    msg["Message-ID"] = make_msgid()
    msg.set_content(reply_text)

    if DRY_RUN:
        print("\n[DRY-RUN] Would send reply to:", to_email)
        print("Subject:", subj)
        print("Body:\n" + reply_text)
        return

    try:
        with make_smtp() as s:
            s.send_message(msg)
        print(f"[send] Replied to {to_email} with subject: {subj}")
    except Exception as e:
        print(f"[error] SMTP send failed: {e}")

# ------------------------- Core handling -------------------------------------

def build_and_update_memory(thrid: Optional[int], subject: str, body: str, thread_text: str, contact_email: str) -> ThreadMemory:
    thrid_key = str(thrid or "no-thrid")
    tm = MEM.get_thread(thrid_key)
    tm.subject = subject or tm.subject
    tm.contact = contact_email or tm.contact

    combined = f"{subject}\n{body}\n{thread_text}"
    # Extract order refs, last total, discount
    refs = extract_order_refs(combined)
    if refs:
        tm.order_refs = (tm.order_refs or [])
        for r in refs:
            if r not in tm.order_refs:
                tm.order_refs.append(r)

    money_hits = MONEY_RE.findall(combined)
    if money_hits and not tm.last_total:
        tm.last_total = money_hits[-1]
    discount_hits = DISCOUNT_RE.findall(combined)
    if discount_hits:
        try:
            last_pct = int(discount_hits[-1])
            tm.last_discount_pct = last_pct
        except Exception:
            pass

    # Produce/refresh a short summary using LLM if possible
    if LLM_CLIENT:
        try:
            sys = (
                "Summarize the email thread from a sales quoting perspective in <=80 words. "
                "Include any PO/RFQ/Quote numbers, items mentioned, currency, totals, and the latest clear next step."
            )
            usr = thread_text[:3000]
            tm.summary = LLM_CLIENT.chat(sys, usr, temperature=0.1)
        except Exception as e:
            print(f"[warn] Groq summarize error: {e}")
            if not tm.summary:
                tm.summary = (subject or "").strip()[:80]
    else:
        if not tm.summary:
            tm.summary = (subject or "").strip()[:80]

    tm.currency = tm.currency or DEFAULT_CCY
    tm.updated_at = ts_iso()
    MEM.set_thread(thrid_key, tm)
    if contact_email:
        MEM.set_contact(contact_email, recent_thread=thrid_key, last_refs=tm.order_refs)
    return tm


def detect_pushback_for_more_discount(subject: str, body: str) -> bool:
    text = f"{subject}\n{body}".lower()
    return any(k in text for k in PUSHBACK_KW)


def handle_message(server: IMAPClient, uid: int):
    fetched = server.fetch([uid], ["RFC822"])  # noqa
    msg = message_from_bytes(fetched[uid][b"RFC822"])

    if is_from_self(msg):
        print("[info] Skipping self-sent email.")
        return

    subject = decode_str(msg.get("Subject"))
    body    = get_text_body(msg)

    if should_skip_autoresponder(msg, subject, body):
        print("[info] Skipping auto/bounce/list reply.")
        return

    # Build full thread context
    thread_uids, thrid = fetch_thread_uids(server, uid)
    thread_text, refs  = build_thread_context(server, thread_uids)

    from_email = parseaddr(decode_str(msg.get("From")))[1].lower()

    # Update memory with the latest thread data
    tm = build_and_update_memory(thrid, subject, body, thread_text, from_email)

    # Heuristic classify then optional LLM refinement
    intent = heuristic_classify(subject, body)
    if LLM_CLIENT:
        llm_guess = llm_classify(subject, body, tm.summary)
        # Prefer LLM unless it says "unrelated"
        if llm_guess and llm_guess != "unrelated":
            intent = llm_guess

    print(f"[classify] Subject='{subject}' → {intent}  (thread {thrid if thrid else 'n/a'})")

    # Route
    if intent == "skip":
        return
    elif intent == "acceptance":
        reply_text = craft_acceptance_reply(subject, body, tm)
        send_reply(msg, reply_text, references_chain=refs)
        return
    elif intent == "question":
        reply_text = craft_question_reply(subject, body, tm)
        send_reply(msg, reply_text, references_chain=refs)
        return

    # Default: revised quote with discount policy (ALL non-acceptance)
    escalate = detect_pushback_for_more_discount(subject, body)
    reply_text = craft_requote_reply(
        email_subject=subject,
        latest_email_body=body,
        thread_text=thread_text,
        tm=tm,
        escalate_to_final=escalate,
    )
    send_reply(msg, reply_text, references_chain=refs)

# ------------------------- Looping / startup ---------------------------------

def print_banner():
    print("=" * 80)
    print(" Gmail Quotation Agent — Thread-Aware + Memory + Discount Policy ".center(80, "="))
    print("=" * 80)
    print(f"Policy: base {BASE_DISCOUNT_PCT}%  |  final {FINAL_DISCOUNT_PCT}% (cap)")


def process_latest_once(server: IMAPClient):
    """Process the single most-recent email in the folder once at startup."""
    try:
        uids = server.search("ALL")
        if not uids:
            print("[info] No messages in mailbox.")
            return
        last_uid = sorted(uids)[-1]
        print("[startup] Processing most recent email once…")
        handle_message(server, last_uid)
    except Exception as e:
        print(f"[warn] Could not process latest email: {e}")


def listen_loop():
    processed: set[int] = set()
    while True:
        try:
            with IMAPClient(IMAP_HOST, port=IMAP_PORT, ssl=True) as server:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.select_folder(IMAP_FOLDER)

                # Startup: process the single latest message (seen or unseen)
                process_latest_once(server)

                # Also handle any UNSEEN at start (avoid duplicates)
                unseen = server.search(["UNSEEN"])
                for uid in sorted(unseen):
                    if uid in processed:
                        continue
                    handle_message(server, uid)
                    processed.add(uid)

                # Live updates via IDLE
                while True:
                    try:
                        server.idle()
                        responses = server.idle_check(timeout=IDLE_HEARTBEAT_SECS)
                        server.idle_done()

                        if responses:
                            uids = server.search(["UNSEEN"])
                            for uid in sorted(uids):
                                if uid in processed:
                                    continue
                                handle_message(server, uid)
                                processed.add(uid)
                    except (socket.timeout, ConnectionResetError):
                        try:
                            server.idle_done()
                        except Exception:
                            pass
                        continue

        except KeyboardInterrupt:
            print("\nExiting on Ctrl+C.")
            return
        except Exception as e:
            hint = ""
            es = str(e).lower()
            if "authentication failed" in es or "invalid credentials" in es:
                hint = ("\nHint: Ensure IMAP is enabled in Gmail Settings and you're using a Gmail App Password.")
            elif "imap" in es and "disabled" in es:
                hint = "\nHint: Enable IMAP in Gmail: Settings → Forwarding and POP/IMAP → Enable IMAP."
            print(f"\n[warn] Connection error: {e}{hint}\nReconnecting in {RECONNECT_BACKOFF_SECS}s…")
            time.sleep(RECONNECT_BACKOFF_SECS)

# ------------------------- Entrypoint ----------------------------------------

if __name__ == "__main__":
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        if PROMPT_IF_MISSING:
            SMTP_USERNAME = input("Gmail address (SMTP_USERNAME): ").strip() or SMTP_USERNAME
            if not SMTP_PASSWORD:
                SMTP_PASSWORD = input("App password (SMTP_PASSWORD, spaces OK): ").replace(" ", "").strip()
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print("ERROR: Set SMTP_USERNAME/SMTP_PASSWORD in your environment or .env.")
        raise SystemExit(1)

    print_banner()
    print(f"IMAP: {IMAP_HOST}:{IMAP_PORT}  |  Folder: {IMAP_FOLDER}")
    print(f"SMTP: {SMTP_SERVER}:{SMTP_PORT}  |  User: {SMTP_USERNAME}")
    if GROQ_API_KEY:
        print(f"Groq: model={LLM_MODEL}  (thread-aware)")
    else:
        print("Groq: GROQ_API_KEY not set → using safe fallback text for replies.")
    print(f"Memory: {MEMORY_FILE}")
    print("Press Ctrl+C to exit.")
    listen_loop()
