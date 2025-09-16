# app/tools/document_langchain_tools.py
from langchain.tools import tool
from app.db.session import SessionLocal
from app.services.document_services import DocumentService

@tool("generate_sales_order_pdf", return_direct=True)
def generate_sales_order_tool(order_id: str) -> str:
    """
    Generate a Sales Order PDF for the given order_id.
    Returns the local file path to the generated PDF.
    """
    with SessionLocal() as session:
        doc_service = DocumentService(session)
        path = doc_service.generate_sales_order_pdf(order_id)
    return path or f"Sales Order for order_id={order_id} could not be generated."

@tool("generate_delivery_note_pdf", return_direct=True)
def generate_delivery_note_tool(order_id: str) -> str:
    """
    Generate a Delivery Note PDF for the given order_id.
    Returns the local file path to the generated PDF.
    """
    with SessionLocal() as session:
        doc_service = DocumentService(session)
        path = doc_service.generate_delivery_note_pdf(order_id)
    return path or f"Delivery Note for order_id={order_id} could not be generated."

@tool("generate_invoice_pdf", return_direct=True)
def generate_invoice_tool(order_id: str) -> str:
    """
    Generate an Invoice PDF for the given order_id (if payment status is pending/unpaid/partial).
    Returns the local file path to the generated PDF.
    """
    with SessionLocal() as session:
        doc_service = DocumentService(session)
        path = doc_service.generate_invoice_pdf(order_id)
    return path or f"Invoice for order_id={order_id} could not be generated."
