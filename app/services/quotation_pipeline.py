# # """
# # quotation_pipeline.py
# # ---------------------
# # Async pipeline: fetch draft orders from MongoDB,
# # run live quotation, print it, update draft status,
# # and send quotation email to the customer.

# # Resilient email sending:
# # - Uses a sync psycopg2 URL (DATABASE_URL_SYNC) for email lookups.
# # - If DB lookup fails/unreachable, falls back to email from the draft,
# #   or a lookup in Mongo customers, or DEV_TEST_TO (if set).
# # - Looks up SQL client by TEXT client_id first (e.g., "ACC002").
# # """

# # import os
# # import sys
# # import json
# # import asyncio
# # import traceback
# # import smtplib
# # from email.mime.text import MIMEText
# # from datetime import datetime, timezone
# # from pathlib import Path
# # from urllib.parse import urlparse
# # import socket
# # from typing import Optional

# # # --- Load .env early (SMTP_*, DB URLs, DEV_TEST_TO, etc.) ---
# # try:
# #     from dotenv import load_dotenv  # type: ignore
# #     load_dotenv()
# # except Exception:
# #     pass

# # # --- Ensure 'app/' is importable ---
# # _CURR = Path(__file__).resolve()
# # for p in [_CURR.parent, *_CURR.parents]:
# #     if (p / "app").is_dir():
# #         sys.path.insert(0, str(p))
# #         break
# # else:
# #     raise RuntimeError("Could not find a parent directory containing 'app/'.")

# # # --- App imports ---
# # from app.db.session import get_collection
# # from app.services.live_quotation_service import make_live_quotation
# # from app.services.llm_vendor_quotation import generate_vendor_quotation_text
# # from app.db.vendors_models import Client  # <-- your SQLAlchemy model (plural module)

# # # --- Build a sync SessionLocal strictly for email lookups (psycopg2) ---
# # from sqlalchemy import create_engine
# # from sqlalchemy.orm import sessionmaker


# # def _resolve_sync_url() -> str:
# #     """Prefer DATABASE_URL_SYNC (psycopg2). If absent, try to derive from DATABASE_URL."""
# #     env_sync = os.getenv("DATABASE_URL_SYNC")
# #     if env_sync:
# #         return env_sync

# #     base = os.getenv("DATABASE_URL")
# #     if not base:
# #         try:
# #             from app.core.config import settings  # type: ignore
# #             base = getattr(settings, "DATABASE_URL", None)
# #         except Exception:
# #             base = None

# #     if not base:
# #         raise RuntimeError("Set DATABASE_URL_SYNC (psycopg2) or DATABASE_URL to continue.")

# #     # Convert async driver to sync driver if needed
# #     if "+asyncpg" in base:
# #         return base.replace("+asyncpg", "+psycopg2")
# #     return base


# # def _host_resolves(db_url: str) -> bool:
# #     try:
# #         host = urlparse(db_url).hostname
# #         if not host:
# #             return False
# #         socket.gethostbyname(host)
# #         return True
# #     except Exception:
# #         return False


# # SYNC_DB_URL = _resolve_sync_url()
# # sync_engine = create_engine(SYNC_DB_URL, echo=False, future=True)
# # SessionLocal = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)


# # # ---------------- Helpers to find a fallback email ----------------

# # def _extract_fallback_email_from_draft(draft: dict) -> Optional[str]:
# #     """Look for the most common places an email might live in the draft."""
# #     # flat keys
# #     for k in ("customer_email", "email", "to", "recipient"):
# #         val = draft.get(k)
# #         if isinstance(val, str) and "@" in val:
# #             return val.strip()

# #     # nested structures
# #     for parent in ("customer", "contact", "client", "billing", "shipping"):
# #         obj = draft.get(parent)
# #         if isinstance(obj, dict):
# #             for k in ("email", "e_mail", "mail"):
# #                 val = obj.get(k)
# #                 if isinstance(val, str) and "@" in val:
# #                     return val.strip()
# #     return None


# # def _lookup_email_from_mongo(client_ref: Optional[str]) -> Optional[str]:
# #     """Try Mongo-side customer stores by common keys (best-effort)."""
# #     if not client_ref:
# #         return None
# #     db = get_collection("order_drafts").database  # get DB handle
# #     # Try temp_customers / customers by code/id
# #     for coll_name, key in (("temp_customers", "customer_code"),
# #                            ("temp_customers", "customer_id"),
# #                            ("customers", "code"),
# #                            ("customers", "customer_id")):
# #         try:
# #             coll = db.get_collection(coll_name)
# #             doc = coll.find_one({key: str(client_ref)})
# #             if doc:
# #                 for k in ("email", "customer_email"):
# #                     val = doc.get(k)
# #                     if isinstance(val, str) and "@" in val:
# #                         return val.strip()
# #         except Exception:
# #             pass
# #     return None


# # # ---------------- SMTP ----------------

# # def _smtp_send(to_email: str, subject: str, body: str) -> dict:
# #     smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
# #     smtp_port = int(os.getenv("SMTP_PORT", 587))
# #     smtp_user = os.getenv("SMTP_USERNAME")
# #     smtp_pass = (os.getenv("SMTP_PASSWORD") or "").replace(" ", "")  # strip spaces in Gmail app pwd

# #     if not smtp_user or not smtp_pass:
# #         raise RuntimeError("Missing SMTP_USERNAME/SMTP_PASSWORD in environment.")

# #     msg = MIMEText(body or "", "plain")
# #     msg["Subject"] = subject
# #     msg["From"] = smtp_user
# #     msg["To"] = to_email

# #     print("\n📤 Sending Email:")
# #     print(f"To: {to_email}")
# #     print(f"Subject: {subject}")
# #     print("Body:\n" + ("-" * 40) + f"\n{body}\n" + ("-" * 40))

# #     with smtplib.SMTP(smtp_server, smtp_port) as server:
# #         try:
# #             server.starttls()
# #         except smtplib.SMTPNotSupportedError:
# #             pass
# #         server.login(smtp_user, smtp_pass)
# #         server.sendmail(smtp_user, [to_email], msg.as_string())

# #     print(f"✅ Email sent successfully to {to_email}")
# #     return {
# #         "to": to_email,
# #         "subject": subject,
# #         "sent_at": datetime.now(timezone.utc).isoformat(),
# #         "provider": "smtp",
# #         "server": smtp_server,
# #         "port": smtp_port,
# #     }


# # def send_email_to_client(client_ref: Optional[str], subject: str, body: str, fallback_email: Optional[str] = None):
# #     """
# #     Look up client by TEXT client_id first (e.g., "ACC002"). If not found, try business_name.
# #     If DB lookup fails/unreachable or client not found, and fallback_email is provided, use it.
# #     Returns a small metadata dict on success, or False on failure.
# #     """
# #     # If DB host doesn't resolve, skip straight to fallback
# #     if not _host_resolves(SYNC_DB_URL):
# #         print("⚠️ Postgres host DNS lookup failed. Using fallback email if available.")
# #         if fallback_email:
# #             return _smtp_send(fallback_email, subject, body)
# #         return False

# #     db = SessionLocal()
# #     try:
# #         ref = (client_ref or "").strip()

# #         # 1) match by TEXT client_id exactly (your table shows client_id is text)
# #         client = db.query(Client).filter(Client.client_id == ref).first()

# #         # 2) optional fallback by business_name
# #         if not client:
# #             client = db.query(Client).filter(Client.business_name == ref).first()

# #         if not client or not getattr(client, "email", None):
# #             print(f"⚠️ Client not found or has no email in DB for ref={client_ref}")
# #             if fallback_email:
# #                 return _smtp_send(fallback_email, subject, body)
# #             return False

# #         return _smtp_send(client.email, subject, body)

# #     except Exception as e:
# #         print(f"❌ DB lookup failed for ref={client_ref}: {e}")
# #         traceback.print_exc()
# #         if fallback_email:
# #             print("➡️ Using fallback email from draft.")
# #             return _smtp_send(fallback_email, subject, body)
# #         return False
# #     finally:
# #         try:
# #             db.close()
# #         except Exception:
# #             pass


# # # ---------------- Draft fetching ----------------

# # def fetch_drafts():
# #     """Fetch all draft orders from MongoDB with status='draft'."""
# #     collection = get_collection("order_drafts")
# #     drafts = list(collection.find({"status": "draft"}))
# #     print(f"✅ Found {len(drafts)} draft(s)")
# #     return drafts


# # # ---------------- Draft processing ----------------

# # async def process_draft(draft: dict):
# #     collection = get_collection("order_drafts")
# #     client_ref = (
# #         draft.get("client_id")
# #         or draft.get("customer_id")
# #         or draft.get("customer_code")
# #         or draft.get("code")
# #     )
# #     draft_id = draft.get("_id")

# #     print(f"\n📦 Processing Draft for Client {client_ref} (id={draft_id}) ...")

# #     try:
# #         items = draft.get("items")
# #         if not items:
# #             raise ValueError("Draft has no items to quote. Provide at least one item.")

# #         # 1) Live quotation (requires items + customer_id)
# #         quotation = await make_live_quotation(
# #             requested_items=items,
# #             customer_id=str(client_ref)
# #         )
# #         try:
# #             print("🧾 Quotation:\n" + json.dumps(quotation, indent=2, ensure_ascii=False, default=str))
# #         except Exception:
# #             print(f"🧾 Quotation (raw): {quotation}")

# #         # 2) LLM vendor quotation (plain text)
# #         try:
# #             llm_text, llm_meta = generate_vendor_quotation_text(quotation, draft)
# #             preview = llm_text[:2000] + ("...[truncated]..." if len(llm_text) > 2000 else "")
# #             print("📝 LLM Vendor Quotation (plain text):\n" + preview)
# #         except Exception as _e:
# #             llm_text = ""
# #             llm_meta = {"error": f"{type(_e).__name__}: {_e}"}
# #             print(f"⚠️ LLM vendor quotation generation failed: {llm_meta}")

# #         # 3) Save quotation & logs to Mongo
# #         update_doc = {
# #             "$set": {
# #                 "status": "quoted",
# #                 "quote_status": quotation.get("status"),
# #                 "quotation": quotation,
# #                 "llm_vendor_quotation": {
# #                     "text": llm_text,
# #                     "meta": llm_meta,
# #                     "generated_at": datetime.now(timezone.utc),
# #                 },
# #                 "updated_at": datetime.now(timezone.utc),
# #             }
# #         }
# #         collection.update_one({"_id": draft_id}, update_doc)
# #         print(f"✅ Quotation prepared & saved for client {client_ref}")

# #         # 4) Figure out a fallback email (if DB fails)
# #         fallback_email = (
# #             _extract_fallback_email_from_draft(draft)
# #             or _lookup_email_from_mongo(client_ref)
# #             or os.getenv("DEV_TEST_TO")  # last resort for testing
# #         )
# #         if fallback_email:
# #             print(f"ℹ️ Fallback email candidate: {fallback_email}")

# #         # 5) Send email off-thread
# #         if llm_text and (client_ref or fallback_email):
# #             email_meta = await asyncio.to_thread(
# #                 send_email_to_client,
# #                 client_ref,
# #                 "Your Quotation from One Table",
# #                 llm_text,
# #                 fallback_email,
# #             )

# #             # Save email log if successful
# #             if email_meta:
# #                 collection.update_one(
# #                     {"_id": draft_id},
# #                     {
# #                         "$set": {"last_emailed_at": datetime.now(timezone.utc)},
# #                         "$push": {"email_log": email_meta},
# #                     },
# #                 )
# #                 print(f"📬 Email log saved: {email_meta}")
# #             else:
# #                 print("📬 Email log: <none> (send failed)")

# #     except Exception as e:
# #         print(f"❌ Error processing draft {draft_id}: {e}")
# #         traceback.print_exc()
# #         collection.update_one(
# #             {"_id": draft_id},
# #             {"$set": {
# #                 "status": "error",
# #                 "error_message": f"{type(e).__name__}: {e}",
# #                 "updated_at": datetime.now(timezone.utc),
# #             }}
# #         )


# # # ---------------- Entrypoint ----------------

# # async def process_all_drafts(concurrency: int = 5):
# #     drafts = fetch_drafts()
# #     if not drafts:
# #         return

# #     sem = asyncio.Semaphore(concurrency)

# #     async def _runner(d):
# #         async with sem:
# #             await process_draft(d)

# #     await asyncio.gather(*(_runner(d) for d in drafts))


# # if __name__ == "__main__":
# #     asyncio.run(process_all_drafts())

# """
# quotation_pipeline.py
# ---------------------
# Test version: fetch draft orders, generate quotation,
# and send the LLM quotation text directly to a fixed email
# address (0331extacc@gmail.com) via Gmail SMTP.
# """

# import os
# import sys
# import json
# import asyncio
# import traceback
# import smtplib
# from email.mime.text import MIMEText
# from datetime import datetime, timezone
# from pathlib import Path

# # --- Load .env early (SMTP_* vars) ---
# try:
#     from dotenv import load_dotenv
#     load_dotenv()
# except Exception:
#     pass

# # --- Ensure 'app/' is importable ---
# _CURR = Path(__file__).resolve()
# for p in [_CURR.parent, *_CURR.parents]:
#     if (p / "app").is_dir():
#         sys.path.insert(0, str(p))
#         break
# else:
#     raise RuntimeError("Could not find a parent directory containing 'app/'.")

# # --- App imports ---
# from app.db.session import get_collection
# from app.services.live_quotation_service import make_live_quotation
# from app.services.llm_vendor_quotation import generate_vendor_quotation_text

# # ---------------- SMTP ----------------
# def _smtp_send(to_email: str, subject: str, body: str) -> dict:
#     smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
#     smtp_port = int(os.getenv("SMTP_PORT", 587))
#     smtp_user = os.getenv("SMTP_USERNAME")
#     smtp_pass = (os.getenv("SMTP_PASSWORD") or "").replace(" ", "")

#     if not smtp_user or not smtp_pass:
#         raise RuntimeError("Missing SMTP_USERNAME/SMTP_PASSWORD in environment.")

#     msg = MIMEText(body or "", "plain")
#     msg["Subject"] = subject
#     msg["From"] = smtp_user
#     msg["To"] = to_email

#     print("\n📤 Sending Email:")
#     print(f"To: {to_email}")
#     print(f"Subject: {subject}")
#     print("Body:\n" + ("-" * 40) + f"\n{body}\n" + ("-" * 40))

#     with smtplib.SMTP(smtp_server, smtp_port) as server:
#         try:
#             server.starttls()
#         except smtplib.SMTPNotSupportedError:
#             pass
#         server.login(smtp_user, smtp_pass)
#         server.sendmail(smtp_user, [to_email], msg.as_string())

#     print(f"✅ Email sent successfully to {to_email}")
#     return {
#         "to": to_email,
#         "subject": subject,
#         "sent_at": datetime.now(timezone.utc).isoformat(),
#     }

# # ---------------- Draft fetching ----------------
# def fetch_drafts():
#     collection = get_collection("order_drafts")
#     drafts = list(collection.find({"status": "draft"}))
#     print(f"✅ Found {len(drafts)} draft(s)")
#     return drafts

# # ---------------- Draft processing ----------------
# async def process_draft(draft: dict):
#     collection = get_collection("order_drafts")
#     draft_id = draft.get("_id")
#     print(f"\n📦 Processing Draft id={draft_id} ...")

#     try:
#         items = draft.get("items")
#         if not items:
#             raise ValueError("Draft has no items to quote. Provide at least one item.")

#         # 1) Live quotation
#         quotation = await make_live_quotation(
#             requested_items=items,
#             customer_id=str(draft.get("customer_id") or draft.get("client_id"))
#         )
#         print("🧾 Quotation:\n" + json.dumps(quotation, indent=2, ensure_ascii=False, default=str))

#         # 2) LLM vendor quotation (plain text)
#         llm_text, llm_meta = generate_vendor_quotation_text(quotation, draft)
#         preview = llm_text[:2000] + ("...[truncated]..." if len(llm_text) > 2000 else "")
#         print("📝 LLM Vendor Quotation (plain text):\n" + preview)

#         # 3) Save quotation back to Mongo
#         update_doc = {
#             "$set": {
#                 "status": "quoted",
#                 "quotation": quotation,
#                 "llm_vendor_quotation": {
#                     "text": llm_text,
#                     "meta": llm_meta,
#                     "generated_at": datetime.now(timezone.utc),
#                 },
#                 "updated_at": datetime.now(timezone.utc),
#             }
#         }
#         collection.update_one({"_id": draft_id}, update_doc)
#         print("✅ Quotation prepared & saved")

#         # 4) Send the LLM text to fixed test email
#         await asyncio.to_thread(
#             _smtp_send,
#             "0331extacc@gmail.com",  # fixed test recipient
#             "Test Quotation from One Table",
#             llm_text,
#         )

#     except Exception as e:
#         print(f"❌ Error processing draft {draft_id}: {e}")
#         traceback.print_exc()
#         collection.update_one(
#             {"_id": draft_id},
#             {"$set": {
#                 "status": "error",
#                 "error_message": f"{type(e).__name__}: {e}",
#                 "updated_at": datetime.now(timezone.utc),
#             }}
#         )

# # ---------------- Entrypoint ----------------
# async def process_all_drafts(concurrency: int = 5):
#     drafts = fetch_drafts()
#     if not drafts:
#         return
#     sem = asyncio.Semaphore(concurrency)
#     async def _runner(d):
#         async with sem:
#             await process_draft(d)
#     await asyncio.gather(*(_runner(d) for d in drafts))

# if __name__ == "__main__":
#     asyncio.run(process_all_drafts())

"""
quotation_pipeline.py
---------------------
Async pipeline: fetch draft orders from MongoDB,
run live quotation, generate vendor-style quotation,
use Groq LLM to create the *email body*, and send it via Gmail SMTP.
"""

import os
import sys
import json
import asyncio
import traceback
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone
from pathlib import Path

# --- Load .env early (SMTP_* vars, GROQ_API_KEY, etc.) ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# --- Ensure 'app/' is importable ---
_CURR = Path(__file__).resolve()
for p in [_CURR.parent, *_CURR.parents]:
    if (p / "app").is_dir():
        sys.path.insert(0, str(p))
        break
else:
    raise RuntimeError("Could not find a parent directory containing 'app/'.")

# --- App imports ---
from app.db.session import get_collection
from app.services.live_quotation_service import make_live_quotation
from app.services.llm_vendor_quotation import generate_vendor_quotation_text, generate_vendor_email


# ---------------- SMTP ----------------
def _smtp_send(to_email: str, subject: str, body: str) -> dict:
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_pass = (os.getenv("SMTP_PASSWORD") or "").replace(" ", "")

    if not smtp_user or not smtp_pass:
        raise RuntimeError("Missing SMTP_USERNAME/SMTP_PASSWORD in environment.")

    msg = MIMEText(body or "", "plain")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email

    print("\n📤 Sending Email:")
    print(f"To: {to_email}")
    print(f"Subject: {subject}")
    print("Body:\n" + ("-" * 40) + f"\n{body}\n" + ("-" * 40))

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        try:
            server.starttls()
        except smtplib.SMTPNotSupportedError:
            pass
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [to_email], msg.as_string())

    print(f"✅ Email sent successfully to {to_email}")
    return {
        "to": to_email,
        "subject": subject,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------- Draft fetching ----------------
def fetch_drafts():
    collection = get_collection("order_drafts")
    drafts = list(collection.find({"status": "draft"}))
    print(f"✅ Found {len(drafts)} draft(s)")
    return drafts


# ---------------- Draft processing ----------------
async def process_draft(draft: dict):
    collection = get_collection("order_drafts")
    draft_id = draft.get("_id")
    client_ref = draft.get("client_id") or draft.get("customer_id") or draft.get("customer_code")

    print(f"\n📦 Processing Draft for Client {client_ref} (id={draft_id}) ...")

    try:
        items = draft.get("items")
        if not items:
            raise ValueError("Draft has no items to quote. Provide at least one item.")

        # 1) Live quotation
        quotation = await make_live_quotation(
            requested_items=items,
            customer_id=str(client_ref),
        )
        print("🧾 Quotation:\n" + json.dumps(quotation, indent=2, ensure_ascii=False, default=str))

        # 2) LLM vendor quotation (plain text for record)
        try:
            llm_text, llm_meta = generate_vendor_quotation_text(quotation, draft)
            preview = llm_text[:2000] + ("...[truncated]..." if len(llm_text) > 2000 else "")
            print("📝 LLM Vendor Quotation (plain text):\n" + preview)
        except Exception as _e:
            llm_text = ""
            llm_meta = {"error": f"{type(_e).__name__}: {_e}"}
            print(f"⚠️ LLM vendor quotation generation failed: {llm_meta}")

        # 3) Save quotation & LLM output to Mongo
        update_doc = {
            "$set": {
                "status": "quoted",
                "quote_status": quotation.get("status"),
                "quotation": quotation,
                "llm_vendor_quotation": {
                    "text": llm_text,
                    "meta": llm_meta,
                    "generated_at": datetime.now(timezone.utc),
                },
                "updated_at": datetime.now(timezone.utc),
            }
        }
        collection.update_one({"_id": draft_id}, update_doc)
        print(f"✅ Quotation prepared & saved for client {client_ref}")

        # 4) Generate the *email body* with Groq LLM
        try:
            email_body = await generate_vendor_email(quotation, draft)
        except Exception as e:
            print(f"❌ Failed to generate vendor email body: {e}")
            email_body = llm_text or "Quotation attached."

        # 5) Send email to fixed test recipient
        await asyncio.to_thread(
            _smtp_send,
            "0331extacc@gmail.com",  # test address
            "Your Quotation from One Table",
            email_body,
        )

        # 6) Save email log to Mongo
        collection.update_one(
            {"_id": draft_id},
            {
                "$set": {"last_emailed_at": datetime.now(timezone.utc)},
                "$push": {"email_log": {
                    "to": "0331extacc@gmail.com",
                    "subject": "Your Quotation from One Table",
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                }},
            },
        )

    except Exception as e:
        print(f"❌ Error processing draft {draft_id}: {e}")
        traceback.print_exc()
        collection.update_one(
            {"_id": draft_id},
            {"$set": {
                "status": "error",
                "error_message": f"{type(e).__name__}: {e}",
                "updated_at": datetime.now(timezone.utc),
            }}
        )


# ---------------- Entrypoint ----------------
async def process_all_drafts(concurrency: int = 5):
    drafts = fetch_drafts()
    if not drafts:
        return

    sem = asyncio.Semaphore(concurrency)

    async def _runner(d):
        async with sem:
            await process_draft(d)

    await asyncio.gather(*(_runner(d) for d in drafts))


if __name__ == "__main__":
    asyncio.run(process_all_drafts())
