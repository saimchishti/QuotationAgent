import os
import asyncio
import pathlib
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import text
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.db.session import VendorSessionLocal  # <- keep this import path


# ---------------- Paths / constants ----------------

PDF_DIR = str((pathlib.Path(__file__).resolve().parents[2] / "pdfs"))
DEFAULT_CURRENCY = "PKR"

DN_STATUSES = {"processing", "completed", "dispatched"}
INVOICE_ELIGIBLE = {"pending", "confirmed", "processing", "completed"}

INVOICE_TERMS = "Net 7"
SELLER_INFO = {
    "name": "FreshFarm Vendors (Pvt) Ltd",
    "address_lines": ["Plot #21, Industrial Area", "Karachi", "PK"],
    "tax_label": "Tax ID",
    "tax_value": "GST-1234567",
}
PAYMENT_INFO = {
    "method": "Bank Transfer",
    "account_name": "FreshFarm Vendors",
    "iban": "PK00BANK0000000000000000",
}


# ---------------- PDF helpers ----------------

def _fmt_currency(x: Optional[float], currency: str = DEFAULT_CURRENCY) -> str:
    try:
        return f"{currency} {float(x):,.2f}"
    except Exception:
        return f"{currency} 0.00"


def _build_invoice_pdf(
    filepath: str,
    *,
    invoice_no: str,
    issued_str: str,
    due_str: str,
    currency: str,
    terms: str,
    seller: Dict[str, Any],
    buyer: Dict[str, Any],
    items: List[List[str]],   # includes header
    totals: Dict[str, float],
    amount_paid: float,
    notes: Optional[str],
    payment_info: Dict[str, str],
) -> str:
    os.makedirs(PDF_DIR, exist_ok=True)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=9, leading=12))
    styles.add(ParagraphStyle(name="Header", parent=styles["Normal"], fontSize=12, leading=15))
    styles.add(ParagraphStyle(name="DocTitle", parent=styles["Title"], fontSize=20, leading=24))
    styles.add(ParagraphStyle(name="Right", parent=styles["Normal"], alignment=2))

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm
    )
    story: List = []

    # Title + meta
    story.append(Paragraph(f"<b>Invoice {invoice_no}</b>", styles["DocTitle"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Issued: {issued_str} • Due: {due_str} • Currency: {currency} • Terms: {terms}",
        styles["Small"]
    ))
    story.append(Spacer(1, 10))

    # Seller / Buyer blocks
    seller_col = [Paragraph("<b>Seller</b>", styles["Header"]), Paragraph(seller.get("name", "-"), styles["Normal"])]
    for line in seller.get("address_lines", []):
        seller_col.append(Paragraph(line, styles["Normal"]))
    if seller.get("tax_label") and seller.get("tax_value"):
        seller_col.append(Paragraph(f"{seller['tax_label']}: {seller['tax_value']}", styles["Normal"]))

    buyer_col = [Paragraph("<b>Buyer</b>", styles["Header"]), Paragraph(buyer.get("name", "-"), styles["Normal"])]
    for line in buyer.get("address_lines", []):
        buyer_col.append(Paragraph(line, styles["Normal"]))
    if buyer.get("tax_label") and buyer.get("tax_value"):
        buyer_col.append(Paragraph(f"{buyer['tax_label']}: {buyer['tax_value']}", styles["Normal"]))

    sb_table = Table([[seller_col, buyer_col]], colWidths=[86*mm, 86*mm], hAlign="LEFT")
    sb_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(sb_table)
    story.append(Spacer(1, 8))

    # Items table
    col_widths_mm = [25, 70, 12, 22, 15, 15, 20]
    table = Table(items, colWidths=[w*mm for w in col_widths_mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.Color(0.98, 0.98, 0.98)]),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
    ]))
    story.append(table)
    story.append(Spacer(1, 10))

    # Totals
    subtotal = totals.get("subtotal", 0.0)
    discount = totals.get("discount", 0.0)
    tax = totals.get("tax", 0.0)
    shipping = totals.get("shipping", 0.0)
    handling = totals.get("handling", 0.0)
    other = totals.get("other", 0.0)
    grand_total = subtotal - discount + tax + shipping + handling + other
    amount_due = grand_total - amount_paid

    totals_rows = [
        ["Subtotal", _fmt_currency(subtotal, currency)],
        ["Discounts", _fmt_currency(-abs(discount), currency) if discount else _fmt_currency(0, currency)],
        ["Tax", _fmt_currency(tax, currency)],
        ["Shipping", _fmt_currency(shipping, currency)],
        ["Handling", _fmt_currency(handling, currency)],
        ["Other", _fmt_currency(other, currency)],
        ["Grand Total", _fmt_currency(grand_total, currency)],
        ["Amount Paid", _fmt_currency(amount_paid, currency)],
        ["Amount Due", _fmt_currency(amount_due, currency)],
    ]

    totals_table = Table(totals_rows, colWidths=[120*mm, 50*mm], hAlign="LEFT")
    totals_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, 6), (-1, 6), 0.5, colors.grey),
        ("FONTNAME", (0, 6), (-1, 6), "Helvetica-Bold"),
        ("FONTNAME", (0, 8), (-1, 8), "Helvetica-Bold"),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 8))

    if notes:
        story.append(Paragraph("<b>Notes:</b>", styles["Header"]))
        story.append(Paragraph(notes, styles["Normal"]))
        story.append(Spacer(1, 6))

    # Payment block
    story.append(Paragraph("<b>Payment:</b>", styles["Header"]))
    pay_lines = [
        f"Method: {payment_info.get('method', '-')}",
        f"Account Name: {payment_info.get('account_name', '-')}",
        f"IBAN: {payment_info.get('iban', '-')}",
        f"Ref: {invoice_no}",
    ]
    for pl in pay_lines:
        story.append(Paragraph(pl, styles["Normal"]))

    doc.build(story)
    return filepath


def _build_pdf(filepath: str, title: str, info_lines: List[str],
               table_data: Optional[List[List]] = None,
               totals_lines: Optional[List[str]] = None) -> str:
    os.makedirs(PDF_DIR, exist_ok=True)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=9, leading=12))
    styles.add(ParagraphStyle(name="Header", parent=styles["Normal"], fontSize=12, leading=15))
    styles.add(ParagraphStyle(name="DocTitle", parent=styles["Title"], fontSize=20, leading=24))

    doc = SimpleDocTemplate(filepath, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
    story: List = []

    story.append(Paragraph(f"<b>{title}</b>", styles["DocTitle"]))
    story.append(Spacer(1, 6))
    for line in info_lines:
        story.append(Paragraph(line, styles["Header"]))
    story.append(Spacer(1, 6))
    story.append(Spacer(1, 10))

    if table_data:
        table = Table(table_data, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.Color(0.98, 0.98, 0.98)]),
        ]))
        story.append(table)
        story.append(Spacer(1, 10))

    if totals_lines:
        for line in totals_lines:
            story.append(Paragraph(line, styles["Normal"]))

    doc.build(story)
    return filepath


# ---------------- Data Access ----------------

class DocumentService:
    def __init__(self, session):
        self.session = session

    async def _fetch_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        sql = text("""
            SELECT
                o.order_id, o.client_id, o.quotation_id, o.origin, o.review_status, o.status,
                o.total_amount, o.created_by, o.reviewed_by, o.created_at,
                o.sales_order_url, o.invoice_url, o.delivery_note_url,
                c.is_business, c.business_name, c.first_name, c.last_name,
                c.email, c.phone, c.billing_address, c.shipping_address
            FROM order_table o
            JOIN clients c ON c.client_id = o.client_id
            WHERE o.order_id = :oid
        """)
        row = (await self.session.execute(sql, {"oid": int(order_id)})).mappings().first()
        return dict(row) if row else None

    async def _fetch_order_items(self, order_id: int) -> List[Dict[str, Any]]:
        sql = text("""
            SELECT
                oi.order_item_id, oi.product_id, oi.quantity, oi.unit_price, oi.discount, oi.tax_amount, oi.line_total,
                p.sku, p.name AS product_name
            FROM order_items oi
            JOIN products p ON p.product_id = oi.product_id
            WHERE oi.order_id = :oid
            ORDER BY oi.order_item_id ASC
        """)
        rows = (await self.session.execute(sql, {"oid": int(order_id)})).mappings().all()
        return [dict(r) for r in rows]

    async def _set_doc_url(self, order_id: int, column_name: str, url: str) -> None:
        await self.session.execute(
            text(f"UPDATE order_table SET {column_name} = :url WHERE order_id = :oid"),
            {"url": url, "oid": int(order_id)},
        )
        await self.session.commit()

    async def generate_sales_order_pdf(self, order_id: int) -> Optional[str]:
        # same as before using _build_pdf
        ...

    async def generate_invoice_pdf(self, order_id: int) -> Optional[str]:
        order = await self._fetch_order(order_id)
        if not order or order.get("invoice_url"):
            return None

        status = (order.get("status") or "").strip().lower()
        if INVOICE_ELIGIBLE and status not in {s.lower() for s in INVOICE_ELIGIBLE}:
            return None

        items = await self._fetch_order_items(order_id)

        issued = datetime.now(timezone.utc)
        due = issued + timedelta(days=7)
        issued_str = issued.strftime("%Y-%m-%d")
        due_str = due.strftime("%Y-%m-%d")

        customer_name = (order["business_name"] + " (Business)") if order.get("is_business") else (
            ((order.get("first_name") or "") + " " + (order.get("last_name") or "")).strip() or "(Unnamed)"
        )

        buyer = {
            "name": customer_name,
            "address_lines": [(order.get("billing_address") or "-")],
            "tax_label": "Tax ID",
            "tax_value": "00",
        }

        header = ["SKU", "Description", "Qty", "Unit", "Disc %", "Tax %", "Line Total"]
        rows: List[List[str]] = [header]

        subtotal = discount = tax = 0.0
        for it in items:
            qty = float(it.get("quantity") or 0)
            unit = float(it.get("unit_price") or 0)
            disc_amt = float(it.get("discount") or 0)
            tax_amt = float(it.get("tax_amount") or 0)
            base = qty * unit
            disc_pct = (disc_amt / base * 100) if base else 0
            taxable = max(base - disc_amt, 0)
            tax_pct = (tax_amt / taxable * 100) if taxable else 0
            line_total = float(it.get("line_total") or (base - disc_amt + tax_amt))
            subtotal += base
            discount += disc_amt
            tax += tax_amt
            rows.append([
                str(it.get("sku") or ""),
                str(it.get("product_name") or ""),
                f"{qty:.2f}",
                f"{unit:,.2f}",
                f"{disc_pct:.0f}%",
                f"{tax_pct:.2f}%",
                f"{line_total:,.2f}",
            ])

        totals = {
            "subtotal": subtotal,
            "discount": discount,
            "tax": tax,
            "shipping": 500.0,    # example
            "handling": 0.0,
            "other": 0.0,
        }
        amount_paid = 0.0

        invoice_no = f"INV-{order['order_id']}"
        filepath = os.path.join(PDF_DIR, f"{invoice_no}.pdf")
        url = _build_invoice_pdf(
            filepath,
            invoice_no=invoice_no,
            issued_str=issued_str,
            due_str=due_str,
            currency=DEFAULT_CURRENCY,
            terms=INVOICE_TERMS,
            seller=SELLER_INFO,
            buyer=buyer,
            items=rows,
            totals=totals,
            amount_paid=amount_paid,
            notes="Thank you for your business. Please reference the invoice number on payment.",
            payment_info=PAYMENT_INFO,
        )
        await self._set_doc_url(order_id, "invoice_url", url)
        print(f"[INV] Saved: {url}")
        return url

    async def generate_delivery_note_pdf(self, order_id: int) -> Optional[str]:
        # same as before using _build_pdf
        ...


# ---------------- Watcher ----------------

async def watch_orders(check_interval: int = 5):
    while True:
        async with VendorSessionLocal() as session:
            svc = DocumentService(session)
            rows = await session.execute(text("""
                SELECT order_id, sales_order_url, invoice_url, delivery_note_url, status
                FROM order_table
                WHERE (sales_order_url IS NULL)
                   OR (invoice_url IS NULL)
                   OR (delivery_note_url IS NULL AND LOWER(status) IN ('processing','completed','dispatched'))
                ORDER BY order_id ASC
            """))
            rows = rows.mappings().all()
            if not rows:
                await asyncio.sleep(check_interval)
                continue

            for row in rows:
                oid = int(row["order_id"])
                if row["sales_order_url"] is None:
                    await svc.generate_sales_order_pdf(oid)
                if row["invoice_url"] is None:
                    await svc.generate_invoice_pdf(oid)
                st = (row.get("status") or "").strip().lower()
                if row["delivery_note_url"] is None and st in DN_STATUSES:
                    await svc.generate_delivery_note_pdf(oid)
        await asyncio.sleep(check_interval)


if __name__ == "__main__":
    print("[Watcher] Document Service (Vendor DB) running…")
    asyncio.run(watch_orders())
