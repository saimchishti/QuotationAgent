"""
Gmail/SMTP email helper for the quotation pipeline.

Exports
-------
- send_email(to, subject, html_body, text_body=None, cc=None, bcc=None, reply_to=None, headers=None) -> dict
  Returns a metadata dict (message_id, provider, to, cc, subject, sent_at).

Environment (.env)
------------------
# Generic SMTP (recommended with Gmail App Password)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=you@example.com
SMTP_PASSWORD=xxxxxxxxxxxxxxxx   # Use your 16-char Gmail App Password (no spaces)
EMAIL_FROM_NAME=Vendor Team      # Optional display name
EMAIL_FROM=you@example.com       # Optional; defaults to SMTP_USERNAME

Notes
-----
- Uses STARTTLS for ports other than 465. Uses SSL when port == 465.
- Trims spaces from SMTP_PASSWORD to avoid common Gmail App Password pitfalls.
- Keep this module focused on sending; your pipeline resolves the recipient email from the DB.
"""
from __future__ import annotations

# Load .env early so SMTP_* vars are available even in tools/one-off runs
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from typing import List, Optional, Dict
from datetime import datetime, timezone

# ---------------- Settings ----------------
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587").strip() or 587)
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
# Gmail App Passwords are usually shown with spaces; strip them for reliability
SMTP_PASSWORD = (os.getenv("SMTP_PASSWORD", "") or "").replace(" ", "").strip()
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Vendor Team").strip()
EMAIL_FROM = os.getenv("EMAIL_FROM", "").strip() or SMTP_USERNAME

if not SMTP_USERNAME or not SMTP_PASSWORD:
    # Intentionally no hard exception at import time; we raise when sending.
    pass


# ---------------- Core helper ----------------
def send_email(
    to: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    reply_to: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Send an email via SMTP and return metadata.

    Parameters
    ----------
    to : recipient email
    subject : subject line
    html_body : HTML body
    text_body : optional plain-text fallback (auto-generated if omitted)
    cc, bcc : optional recipient lists
    reply_to : optional reply-to address
    headers : optional extra headers

    Returns
    -------
    dict : {"provider", "server", "port", "message_id", "to", "cc", "subject", "sent_at"}
    """
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        raise RuntimeError("SMTP_USERNAME/SMTP_PASSWORD not configured for SMTP sending.")

    cc = cc or []
    bcc = bcc or []

    # Build the MIME message
    msg = MIMEMultipart("alternative")
    msg_id = make_msgid(domain=SMTP_USERNAME.split("@")[-1] if "@" in SMTP_USERNAME else None)
    msg["Message-ID"] = msg_id
    msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>" if EMAIL_FROM_NAME else EMAIL_FROM
    msg["To"] = to
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    if reply_to:
        msg["Reply-To"] = reply_to

    if headers:
        for k, v in headers.items():
            # Avoid overriding core headers
            if k.lower() not in {"from", "to", "cc", "bcc", "subject", "date", "message-id", "reply-to"}:
                msg[k] = str(v)

    # Plain-text part
    if not text_body:
        # crude fallback: strip tags
        import re
        text_body = re.sub("<[^>]+>", "", html_body or "").replace("&nbsp;", " ").strip()
    msg.attach(MIMEText(text_body, "plain", _charset="utf-8"))

    # HTML part
    msg.attach(MIMEText(html_body or "", "html", _charset="utf-8"))

    recipients = [to] + cc + bcc

    # Send: SSL for 465, otherwise STARTTLS
    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
            smtp.sendmail(EMAIL_FROM, recipients, msg.as_string())
    else:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.ehlo()
            try:
                smtp.starttls()
                smtp.ehlo()
            except smtplib.SMTPNotSupportedError:
                # Server may not support STARTTLS; proceed without if necessary
                pass
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
            smtp.sendmail(EMAIL_FROM, recipients, msg.as_string())

    meta = {
        "provider": "smtp",
        "server": SMTP_SERVER,
        "port": str(SMTP_PORT),
        "message_id": msg_id.strip("<>"),
        "to": to,
        "cc": ", ".join(cc) if cc else "",
        "subject": subject,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "from": EMAIL_FROM,
        "from_name": EMAIL_FROM_NAME,
    }
    return meta
