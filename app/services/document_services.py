# app/services/document_services.py

import os
import asyncio
import pathlib
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from sqlalchemy import text
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.db.session import VendorSessionLocal  # Vendor DB session


# ---------------- Paths / constants ----------------

# Save PDFs in "<project_root>/pdfs"
PDF_DIR = str((pathlib.Path(__file__).resolve().parents[2] / "pdfs"))

DOC_TYPES = {
    "SO": "SO_URL:",
    "DN": "DN_URL:",
    "INV": "INV_URL:",
}

INVOICE_ELIGIBLE = {"pending", "unpaid", "partial"}
DEFAULT_CURRENCY = "PKR"


# ---------------- PDF helpers (formatted with Platypus) ----------------

def _fmt_currency(x: Optional[float], currency: str = DEFAULT_CURRENCY) -> str:
    try:
        return f"{currency} {float(x):,.2f}"
    except Exception:
        return f"{currency} 0.00"

def _p(text: str, style_name: str, styles) -> Paragraph:
    return Paragraph(text, styles[style_name])

def _hline() -> Table:
    t = Table([[""]], colWidths=[170 * mm], rowHeights=[2])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.grey)]))
    return t

def _build_pdf(filepath: str, title: str, info_lines: List[str], table_data: Optional[List[List]] = None, totals_lines: Optional[List[str]] = None) -> str:
    os.makedirs(PDF_DIR, exist_ok=True)

    styles = getSampleStyleSheet()
    # Tweak base styles a bit
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=9, leading=12))
    styles.add(ParagraphStyle(name="Header", parent=styles["Normal"], fontSize=12, leading=15))
    styles.add(ParagraphStyle(name="DocTitle", parent=styles["Title"], fontSize=20, leading=24))

    doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
    story: List = []

    # Title
    story.append(_p(f"<b>{title}</b>", "DocTitle", styles))
    story.append(Spacer(1, 6))

    # Header / info block
    for line in info_lines:
        story.append(_p(line, "Header", styles))
    story.append(Spacer(1, 6))
    story.append(_hline())
    story.append(Spacer(1, 10))

    # Table (if any)
    if table_data:
        table = Table(table_data, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.Color(0.98, 0.98, 0.98)]),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
        ]))
        story.append(table)
        story.append(Spacer(1, 10))

    # Totals / footer lines (if any)
    if totals_lines:
        for line in totals_lines:
            story.append(_p(line, "Normal", styles))

    doc.build(story)
    return filepath


# ---------------- Document service (async) ----------------

class DocumentService:
    def __init__(self, session):
        self.session = session

    async def _fetch_order(self, order_id):
        result = await self.session.execute(text("SELECT * FROM orders WHERE order_id = :oid"), {"oid": order_id})
        row = result.mappings().first()
        return dict(row) if row else None

    async def _update_notes(self, order_id, prefix, url):
        # Avoid CONCAT type issues with asyncpg: use || and cast UUID
        await self.session.execute(
            text("""
                UPDATE orders
                SET notes = :marker || E'\n' || COALESCE(notes, '')
                WHERE order_id = CAST(:oid AS uuid)
            """),
            {"marker": f"{prefix}{url}", "oid": order_id},
        )
        await self.session.commit()

    def _already_has(self, notes, prefix) -> bool:
        return bool(notes and prefix in notes)

    # --------- Generators (formatted) ---------

    async def generate_sales_order_pdf(self, order_id: str) -> Optional[str]:
        order = await self._fetch_order(order_id)
        if not order:
            return None

        prefix = DOC_TYPES["SO"]
        if self._already_has(order.get("notes"), prefix):
            return None

        number = order.get("order_number") or str(order_id)[:8]
        filename = f"SO-{number}.pdf"
        filepath = os.path.join(PDF_DIR, filename)

        info = [
            f"<b>Order Number:</b> {number}",
            f"<b>Order Date:</b> {order.get('order_date')}",
            f"<b>Customer:</b> {order.get('customer_name')}",
        ]

        # One-line item table – extend later if you add multi-line items
        subtotal = float(order.get("quantity") or 0) * float(order.get("price_per_unit") or 0)
        total = float(order.get("total_amount") or subtotal)

        table = [
            ["Item / Service", "Qty", "Unit Price", "Line Total"],
            [str(order.get("service_or_item") or ""), str(order.get("quantity") or 0), _fmt_currency(order.get("price_per_unit")), _fmt_currency(subtotal)],
        ]

        totals = [
            f"<b>Grand Total:</b> {_fmt_currency(total)}",
        ]

        url = _build_pdf(filepath, "Sales Order", info, table, totals)
        await self._update_notes(order_id, prefix, url)
        print(f"[SO] Saved: {url}")
        return url

    async def generate_delivery_note_pdf(self, order_id: str) -> Optional[str]:
        order = await self._fetch_order(order_id)
        if not order:
            return None

        prefix = DOC_TYPES["DN"]
        if self._already_has(order.get("notes"), prefix):
            return None

        number = order.get("order_number") or str(order_id)[:8]
        filename = f"DN-{number}.pdf"
        filepath = os.path.join(PDF_DIR, filename)

        qty_ordered = float(order.get("quantity") or 0)
        qty_delivered = qty_ordered  # minimal logic; adapt when you store actual delivered qty
        backorder = max(qty_ordered - qty_delivered, 0.0)
        over = max(qty_delivered - qty_ordered, 0.0)

        info = [
            f"<b>Related Order:</b> {number}",
            f"<b>Delivery Date:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            f"<b>Customer:</b> {order.get('customer_name')}",
        ]

        table = [
            ["Item", "Ordered", "Delivered", "Backorder", "Over"],
            [str(order.get("service_or_item") or ""), f"{qty_ordered:g}", f"{qty_delivered:g}", f"{backorder:g}", f"{over:g}"],
        ]

        url = _build_pdf(filepath, "Delivery Note", info, table, None)
        await self._update_notes(order_id, prefix, url)
        print(f"[DN] Saved: {url}")
        return url

    async def generate_invoice_pdf(self, order_id: str) -> Optional[str]:
        order = await self._fetch_order(order_id)
        if not order:
            return None

        prefix = DOC_TYPES["INV"]
        if self._already_has(order.get("notes"), prefix):
            return None

        status = (order.get("payment_status") or "").strip().lower()
        if status not in INVOICE_ELIGIBLE:
            print(f"[INV] Skipping for status={status}")
            return None

        number = order.get("order_number") or str(order_id)[:8]
        filename = f"INV-{number}.pdf"
        filepath = os.path.join(PDF_DIR, filename)

        issued = datetime.now(timezone.utc)
        due = issued + timedelta(days=7)

        qty = float(order.get("quantity") or 0)
        unit = float(order.get("price_per_unit") or 0)
        subtotal = qty * unit
        total = float(order.get("total_amount") or subtotal)

        info = [
            f"<b>Invoice No.:</b> INV-{number}",
            f"<b>Issued:</b> {issued.strftime('%Y-%m-%d')} &nbsp;&nbsp; <b>Due:</b> {due.strftime('%Y-%m-%d')}",
            f"<b>Customer:</b> {order.get('customer_name')}",
            f"<b>Payment Status:</b> {order.get('payment_status')}",
        ]

        table = [
            ["Item / Service", "Qty", "Unit Price", "Line Total"],
            [str(order.get("service_or_item") or ""), f"{qty:g}", _fmt_currency(unit), _fmt_currency(subtotal)],
        ]

        totals = [
            f"<b>Grand Total:</b> {_fmt_currency(total)}",
            "<i>Payment Instructions:</i> Please reference the Invoice No. when paying.",
        ]

        url = _build_pdf(filepath, "Invoice", info, table, totals)
        await self._update_notes(order_id, prefix, url)
        print(f"[INV] Saved: {url}")
        return url


# ---------------- Watcher logic ----------------

async def get_initial_last_time(session):
    """On first run, start after the newest order so we don't process history."""
    result = await session.execute(text("SELECT MAX(order_date) FROM orders"))
    max_time = result.scalar()
    if not max_time:
        return datetime.now(timezone.utc)
    print(f"[Watcher] Skipping orders with order_date <= {max_time}")
    return max_time

async def watch_orders(check_interval: int = 5):
    # Establish initial cursor time
    async with VendorSessionLocal() as session:
        last_time = await get_initial_last_time(session)
        print(f"[Watcher] Starting from {last_time}")

    while True:
        async with VendorSessionLocal() as session:
            svc = DocumentService(session)

            # 1) New/mutated orders missing SO or INV
            rows = await session.execute(text("""
                SELECT order_id, order_date, notes
                FROM orders
                WHERE order_date > :last_time
                  AND (
                      notes IS NULL
                      OR notes NOT LIKE '%SO_URL:%'
                      OR notes NOT LIKE '%INV_URL:%'
                  )
                ORDER BY order_date ASC
            """), {"last_time": last_time.replace(tzinfo=None)})
            rows = rows.mappings().all()

            processed_times = []
            for row in rows:
                oid = str(row["order_id"])
                print(f"[Watcher] New order: {oid}")
                await svc.generate_sales_order_pdf(oid)
                await svc.generate_invoice_pdf(oid)
                processed_times.append(row["order_date"].astimezone(timezone.utc))

            if processed_times:
                last_time = max(processed_times)

            # 2) Delivery notes for dispatched orders (generate once)
            rows_dn = await session.execute(text("""
                SELECT order_id
                FROM orders
                WHERE delivery_status = 'dispatched'
                  AND (notes IS NULL OR notes NOT LIKE '%DN_URL:%')
                ORDER BY order_date ASC
            """))
            for row in rows_dn.mappings().all():
                oid = str(row["order_id"])
                print(f"[Watcher] Generating Delivery Note for: {oid}")
                await svc.generate_delivery_note_pdf(oid)

        await asyncio.sleep(check_interval)


# ---------------- Script entrypoint ----------------

if __name__ == "__main__":
    print("[Watcher] Document Service (Vendor DB) running...")
    asyncio.run(watch_orders())
