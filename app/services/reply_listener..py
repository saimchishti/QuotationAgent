#!/usr/bin/env python3
"""
gmail_quote_agent.py — thread-aware, discount-policy version

Behavior
- Listens for new Gmail via IMAP IDLE.
- On startup: processes the single most-recent email once.
- For each new message:
    • If the latest message is an ORDER ACCEPTANCE → reply: "Your order is confirmed. We will send the invoice shortly."
    • Otherwise (ALL non-acceptance emails) → reply with a revised quotation that applies a discount policy:
        - Default/base discount = BASE_DISCOUNT_PCT (default 10%)
        - If buyer pushes for more / asks "best/final" → use FINAL_DISCOUNT_PCT (default 20%) as the final, do-not-exceed discount
- Uses full Gmail thread context (X-GM-THRID) so the reply is conversational and consistent.
- Sends replies via your SMTP creds, keeps threading (In-Reply-To / References).
- Self-loop protection (doesn’t reply to your own emails).

ENV (.env supported via python-dotenv):
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

  # Misc
  IDLE_HEARTBEAT_SECS=60
  RECONNECT_BACKOFF_SECS=5
  PROMPT_IF_MISSING=false

Install:
  pip install imapclient python-dotenv groq
Run:
  python gmail_quote_agent.py
"""

import os
import re
import ssl
import time
import socket
import smtplib
from datetime import datetime, timezone
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

# Thread/context limits
MAX_THREAD_MESSAGES = int(os.getenv("MAX_THREAD_MESSAGES", "12"))
MAX_THREAD_CHARS    = int(os.getenv("MAX_THREAD_CHARS", "14000"))

# ------------------------- Helpers ------------------------------------------
def decode_str(s: str | None) -> str:
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

def classify_email(subject: str, body: str) -> str:
    """
    'acceptance' for order acceptance; otherwise treat as 'requote'.
    (Per your policy: reply to ALL non-acceptance messages with a revised quote.)
    """
    text = f"{subject}\n{body}".lower()

    acceptance_kw = [
        "accept the order", "accept this order", "we accept", "accepted",
        "order confirmed", "confirm the order", "confirmed", "proceed with the order",
        "go ahead", "place the order", "approved the quote", "approve this quote",
        "we are placing the order", "book the order", "we confirm"
    ]
    if any(kw in text for kw in acceptance_kw):
        return "acceptance"
    return "requote"

def detect_pushback_for_more_discount(subject: str, body: str) -> bool:
    """Detects if the buyer is asking for better price / more discount / 'final'."""
    text = f"{subject}\n{body}".lower()
    kw = [
        "more discount", "extra discount", "better price", "lower price", "too high",
        "negotiate", "negotiate further", "reduce price", "can you do better",
        "final price", "best price", "last price", "your best", "lowest you can",
        "sharpen your pencil", "match competitor", "price match"
    ]
    return any(k in text for k in kw)

def safe_subject_reply(subject: str) -> str:
    return subject if subject.lower().startswith("re:") else f"Re: {subject or ''}"

def make_smtp() -> smtplib.SMTP:
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
    server.ehlo()
    server.starttls(context=ssl.create_default_context())
    server.ehlo()
    server.login(SMTP_USERNAME, SMTP_PASSWORD)
    return server

def send_reply(original_msg, reply_text: str, subject_override: str | None = None, references_chain: list[str] | None = None):
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
    msg["From"] = formataddr(("Sales", SMTP_USERNAME))
    msg["To"] = to_email
    msg["Subject"] = subj
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = " ".join(references[-20:])
    msg["Message-ID"] = make_msgid()
    msg.set_content(reply_text)

    try:
        with make_smtp() as s:
            s.send_message(msg)
        print(f"[send] Replied to {to_email} with subject: {subj}")
    except Exception as e:
        print(f"[error] SMTP send failed: {e}")

# ---------- Thread utilities (Gmail X-GM-THRID) ------------------------------
def fetch_thread_uids(server: IMAPClient, any_uid: int) -> tuple[list[int], int | None]:
    info = server.fetch([any_uid], ["X-GM-THRID"])
    thrid = info.get(any_uid, {}).get(b"X-GM-THRID")
    if thrid is None:
        return [any_uid], None
    try:
        uids = server.search(["X-GM-THRID", thrid])
    except Exception:
        return [any_uid], thrid
    return sorted(uids), thrid

def build_thread_context(server: IMAPClient, uids: list[int]) -> tuple[str, list[str]]:
    """Build a compact plaintext conversation log and collect References."""
    if not uids:
        return "", []
    fetched = server.fetch(uids, ["RFC822", "INTERNALDATE", "ENVELOPE"])
    def _sort_key(uid):
        meta = fetched.get(uid, {})
        return meta.get(b"INTERNALDATE") or 0
    ordered = sorted(uids, key=_sort_key)

    lines = []
    total_len = 0
    refs: list[str] = []

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

# ------------------------- Groq logic ----------------------------------------
def groq_revised_quote(email_subject: str,
                       latest_email_body: str,
                       thread_text: str,
                       base_discount_pct: int,
                       final_discount_pct: int,
                       escalate_to_final: bool) -> str:
    """
    Draft a revised quotation reply using full thread context and discount policy.
    - If escalate_to_final=True → apply exactly final_discount_pct and clearly mark it as final/best.
    - Else → apply exactly base_discount_pct.
    - Apply discount against latest vendor-quoted prices in the thread. If none exist,
      state the offered discount percentage and ask for missing details in ONE sentence.
    - Keep currency consistent with the thread (default PKR).
    - Plain text only.
    """
    if not GROQ_API_KEY:
        pct = final_discount_pct if escalate_to_final else base_discount_pct
        tag = " (final)" if escalate_to_final else ""
        return (f"Thanks for your message.\n\n"
                f"Here is our revised quotation with {pct}%{tag} discount:\n"
                f"- [No Groq key set] Please share items/quantities or the last quote to apply {pct}% precisely.\n\n"
                "Terms:\n- Price validity: 7 days\n- Delivery: 5–7 working days after PO\n- Payment: Advance or Net 7\n\nBest regards,\nSales")

    client = Groq(api_key=GROQ_API_KEY)
    target_pct = final_discount_pct if escalate_to_final else base_discount_pct
    final_line = (f"Offer exactly {final_discount_pct}% discount as FINAL and state clearly that "
                  f"{final_discount_pct}% is our best and final; do not offer or imply any higher discount.")
    base_line = f"Offer exactly {base_discount_pct}% discount, and do NOT exceed {final_discount_pct}% under any circumstances."

    policy_directive = final_line if escalate_to_final else base_line

    system_prompt = (
        "You are a meticulous B2B sales quoting assistant for a vendor in Pakistan. "
        "Write brief, professional email replies in PLAIN TEXT (no HTML/markdown). "
        "Use the full email thread below to stay conversational and consistent.\n\n"
        "Discount policy:\n"
        f"- BASE discount: {base_discount_pct}%\n"
        f"- FINAL discount cap: {final_discount_pct}%\n"
        f"- For this reply, apply EXACTLY {target_pct}% discount. {policy_directive}\n"
        "- Apply the discount to the latest vendor-quoted prices in the thread. "
        "If no prices exist, state the offered discount percentage and ask for the missing details in ONE sentence.\n"
        "- Show line items, subtotal, discount, taxes if mentioned, and GRAND TOTAL. "
        "Keep the currency from the thread (default PKR).\n"
        "- Include standard terms: validity 7 days, delivery 5–7 working days ARO, payment terms (Advance / Net 7). "
        "Keep it compact and actionable. No tables—use clean, fixed-width text."
    )

    user_prompt = f"""Thread Subject: {email_subject}

==== FULL EMAIL THREAD (oldest → newest) ====
{thread_text[:MAX_THREAD_CHARS]}

==== LATEST CUSTOMER MESSAGE (body only) ====
{latest_email_body.strip()[:4000]}

Task:
Compose a ready-to-send PLAIN TEXT reply email with a revised quotation applying the exact discount policy above.
"""

    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.2,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"[warn] Groq error: {e}")
        pct = target_pct
        tag = " (final)" if escalate_to_final else ""
        return (f"Thanks for your message.\n\n"
                f"Here is our revised quotation with {pct}%{tag} discount.\n"
                "- [Temporary issue preparing final numbers] Please confirm items/quantities and last quoted prices.\n\n"
                "Terms:\n- Price validity: 7 days\n- Delivery: 5–7 working days after PO\n- Payment: Advance or Net 7\n\nBest regards,\nSales")

# ------------------------- Core handling -------------------------------------
def handle_message(server: IMAPClient, uid: int):
    fetched = server.fetch([uid], ["RFC822"])
    msg = message_from_bytes(fetched[uid][b"RFC822"])

    if is_from_self(msg):
        print("[info] Skipping self-sent email.")
        return

    subject = decode_str(msg.get("Subject"))
    body    = get_text_body(msg)

    # Build full thread context
    thread_uids, thrid = fetch_thread_uids(server, uid)
    thread_text, refs  = build_thread_context(server, thread_uids)

    # Classify
    cls = classify_email(subject, body)
    print(f"[classify] Subject='{subject}' → {cls}  (thread {thrid if thrid else 'n/a'})")

    if cls == "acceptance":
        reply_text = "Your order is confirmed. We will send the invoice shortly."
        send_reply(msg, reply_text, references_chain=refs)
        return

    # For ALL non-acceptance → revised quote with discount policy
    escalate = detect_pushback_for_more_discount(subject, body)
    reply_text = groq_revised_quote(
        email_subject=subject,
        latest_email_body=body,
        thread_text=thread_text,
        base_discount_pct=BASE_DISCOUNT_PCT,
        final_discount_pct=FINAL_DISCOUNT_PCT,
        escalate_to_final=escalate
    )
    send_reply(msg, reply_text, references_chain=refs)

def print_banner():
    print("=" * 80)
    print(" Gmail Quotation Agent — Thread-Aware + Discount Policy ".center(80, "="))
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
        print("Groq: GROQ_API_KEY not set → using safe fallback text for revised quotes.")
    print("Press Ctrl+C to exit.")
    listen_loop()
