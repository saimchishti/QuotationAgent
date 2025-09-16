# app/db/vendor_models_new.py

from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    DateTime,
    Text,
    Numeric,
    Boolean,
    ForeignKey,
    CheckConstraint,
    func
)

# ========================
# Vendor DB Declarative Base
# ========================
class VendorBase(DeclarativeBase):
    """Declarative base for the VENDORS database."""
    pass


# ========================
# Clients Table
# ========================
class Client(VendorBase):
    __tablename__ = "clients"

    # client_id is TEXT in your DB (e.g., "ACC002")
    client_id = Column(String, primary_key=True)  # <-- was Integer/autoincrement; fix it
    lifecycle_state = Column(String(20), nullable=False)
    is_business = Column(Boolean, default=False)
    business_name = Column(String(200))
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(150))
    phone = Column(String(50))
    billing_address = Column(Text)
    shipping_address = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    quotations = relationship("Quotation", back_populates="client")
    orders = relationship("OrderTable", back_populates="client")
    invoices = relationship("Invoice", back_populates="client")
    calls = relationship("Call", back_populates="client")
    emails = relationship("Email", back_populates="client")

# ========================
# Products Table
# ========================
class Product(VendorBase):
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    sku = Column(String(100), unique=True)
    price = Column(Numeric(12, 2), nullable=False)
    tax_rate = Column(Numeric(5, 2), default=0.00)
    stock_quantity = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order_items = relationship("OrderItem", back_populates="product")


# ========================
# Quotations Table
# ========================
class Quotation(VendorBase):
    __tablename__ = "quotations"

    quotation_id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.client_id", ondelete="CASCADE"))
    call_id = Column(Integer, ForeignKey("calls.call_id", ondelete="SET NULL"))   # ✅ add this
    prepared_by = Column(String(100))
    quotation_date = Column(DateTime(timezone=True), server_default=func.now())
    valid_until = Column(Date)
    total_amount = Column(Numeric(12, 2), nullable=False)
    discount_amount = Column(Numeric(12, 2), default=0.00)
    tax_amount = Column(Numeric(12, 2), default=0.00)
    grand_total = Column(Numeric(12, 2), nullable=False)
    status = Column(String(20), nullable=False)

    client = relationship("Client", back_populates="quotations")
    orders = relationship("OrderTable", back_populates="quotation")
    call = relationship("Call", back_populates="quotations")   # ✅ fix backref



# ========================
# Orders Table
# ========================
class OrderTable(VendorBase):
    __tablename__ = "order_table"

    order_id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.client_id", ondelete="CASCADE"))
    quotation_id = Column(Integer, ForeignKey("quotations.quotation_id", ondelete="SET NULL"))
    origin = Column(String(20), nullable=False)
    review_status = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    created_by = Column(String(100))
    reviewed_by = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 🔹 New columns to store generated document URLs
    sales_order_url = Column(String, nullable=True)
    invoice_url = Column(String, nullable=True)
    delivery_note_url = Column(String, nullable=True)

    # Relationships
    client = relationship("Client", back_populates="orders")
    quotation = relationship("Quotation", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")
    invoices = relationship("Invoice", back_populates="order")




# ========================
# Order Items Table
# ========================
class OrderItem(VendorBase):
    __tablename__ = "order_items"

    order_item_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("order_table.order_id", ondelete="CASCADE"))
    product_id = Column(Integer, ForeignKey("products.product_id", ondelete="CASCADE"))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    discount = Column(Numeric(12, 2), default=0.00)
    tax_amount = Column(Numeric(12, 2), default=0.00)
    line_total = Column(Numeric(12, 2), nullable=False)

    order = relationship("OrderTable", back_populates="items")
    product = relationship("Product", back_populates="order_items")


# ========================
# Invoices Table
# ========================
class Invoice(VendorBase):
    __tablename__ = "invoices"

    invoice_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("order_table.order_id", ondelete="CASCADE"))
    client_id = Column(Integer, ForeignKey("clients.client_id", ondelete="CASCADE"))
    invoice_date = Column(DateTime(timezone=True), server_default=func.now())
    due_date = Column(Date)
    total_amount = Column(Numeric(12, 2), nullable=False)
    discount_amount = Column(Numeric(12, 2), default=0.00)
    tax_amount = Column(Numeric(12, 2), default=0.00)
    grand_total = Column(Numeric(12, 2), nullable=False)
    status = Column(String(20), nullable=False)

    order = relationship("OrderTable", back_populates="invoices")
    client = relationship("Client", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice")


# ========================
# Payments Table
# ========================
class Payment(VendorBase):
    __tablename__ = "payments"

    payment_id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoices.invoice_id", ondelete="CASCADE"))
    payment_date = Column(DateTime(timezone=True), server_default=func.now())
    amount = Column(Numeric(12, 2), nullable=False)
    method = Column(String(20), nullable=False)
    transaction_id = Column(String(255))
    status = Column(String(20), nullable=False)

    invoice = relationship("Invoice", back_populates="payments")


# ========================
# Taxes Table
# ========================
class Tax(VendorBase):
    __tablename__ = "taxes"

    tax_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    rate = Column(Numeric(5, 2), nullable=False)

# ========================
# Emails Table
# ========================
class Email(VendorBase):
    __tablename__ = "emails"

    email_id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.client_id", ondelete="CASCADE"))
    quotation_id = Column(Integer, ForeignKey("quotations.quotation_id", ondelete="SET NULL"))
    order_id = Column(Integer, ForeignKey("order_table.order_id", ondelete="SET NULL"))

    direction = Column(String(10), nullable=False)  # inbound / outbound
    subject = Column(String(255), nullable=False)
    body_text = Column(Text)
    status = Column(String(20), nullable=False)  # queued / sent / failed / received / replied

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True))
    received_at = Column(DateTime(timezone=True))

    # Relationships
    client = relationship("Client", back_populates="emails")
    quotation = relationship("Quotation")
    order = relationship("OrderTable")


# ========================
# Calls Table
# ========================
class Call(VendorBase):
    __tablename__ = "calls"

    call_id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.client_id", ondelete="CASCADE"))
    summary = Column(Text, nullable=False)
    budget = Column(Numeric(12, 2))
    source = Column(String(50), default="phone")
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    client = relationship("Client", back_populates="calls")
    quotations = relationship("Quotation", back_populates="call")
