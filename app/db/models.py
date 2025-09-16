from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, Date, Text, Double, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

Base = declarative_base()

# Base reference tables
class Country(Base):
    __tablename__ = "country"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    provinces = relationship("Province", back_populates="country")
    business_owners = relationship("BusinessOwnerCase1", back_populates="country")
    customers = relationship("Customer", back_populates="country")
    vendors = relationship("VendorCase1", back_populates="country")
    taxes = relationship("TaxesType", back_populates="country")
    vendor_case1 = relationship("app.db.models.VendorCase1", back_populates="country")


class Province(Base):
    __tablename__ = "province"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    country_id = Column(Integer, ForeignKey("country.id"), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    country = relationship("Country", back_populates="provinces")
    business_owners = relationship("BusinessOwnerCase1", back_populates="province")
    customers = relationship("Customer", back_populates="province")
    vendors = relationship("VendorCase1", back_populates="province")
    taxes = relationship("TaxesType", back_populates="province")


# Type tables
class RestaurantType(Base):
    __tablename__ = "restaurant_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    business_owners = relationship("BusinessOwnerCase1", back_populates="restaurant_type")


class CuisineType(Base):
    __tablename__ = "cuisine_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    business_owners = relationship("BusinessOwnerCase1", back_populates="cuisine_type")


class DeliveryTimeType(Base):
    __tablename__ = "deliverytime_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    business_owners = relationship("BusinessOwnerCase1", back_populates="delivery_time_type")
    vendors = relationship("VendorCase1", back_populates="delivery_time_type")


class DeliveryChargesType(Base):
    __tablename__ = "deliverycharges_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    business_owners = relationship("BusinessOwnerCase1", back_populates="delivery_charges_type")
    vendors = relationship("VendorCase1", back_populates="delivery_charges_type")


class PaymentModeType(Base):
    __tablename__ = "paymentmode_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    vendors = relationship("VendorCase1", back_populates="payment_mode_type")


class TransportType(Base):
    __tablename__ = "transport_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    vendors = relationship("VendorCase1", back_populates="transport_type")


class RequestType(Base):
    __tablename__ = "request_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    vendor_business_cert_changes = relationship("VendorCase1", foreign_keys="VendorCase1.business_cert_url_change_status_id", back_populates="business_cert_change_status")
    vendor_license_cert_changes = relationship("VendorCase1", foreign_keys="VendorCase1.license_cert_url_change_status_id", back_populates="license_cert_change_status")
    vendor_delivery_time_changes = relationship("VendorCase1", foreign_keys="VendorCase1.delivery_time_change_status_id", back_populates="delivery_time_change_status")
    vendor_radius_changes = relationship("VendorCase1", foreign_keys="VendorCase1.covering_radius_change_status_id", back_populates="covering_radius_change_status")


class RoleType(Base):
    __tablename__ = "role_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())


class RolesCase1Type(Base):
    __tablename__ = "rolescase1_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())


class CapabilityType(Base):
    __tablename__ = "capability_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    create = Column(Boolean, nullable=False, default=True)
    read = Column(Boolean, nullable=False, default=True)
    update = Column(Boolean, nullable=False, default=True)
    delete = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())


class RoleCapabilityMapping(Base):
    __tablename__ = "role_capability_mapping"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    role_id = Column(String, nullable=False)
    capability_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())


# Inventory and ingredient types
class IngredientType(Base):
    __tablename__ = "ingredient_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    inventories = relationship("Inventory", back_populates="ingredient_type")


class IngredientTypeC1(Base):
    __tablename__ = "ingredient_typec1"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())


class IngredientCase1Type(Base):
    __tablename__ = "ingredientcase1_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    inventory_case1 = relationship("InventoryCase1", back_populates="ingredient_type")


class UnitType(Base):
    __tablename__ = "unit_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    inventories = relationship("Inventory", back_populates="unit_type")


class UnitCase1Type(Base):
    __tablename__ = "unitcase1_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    inventory_case1 = relationship("InventoryCase1", back_populates="unit_type")


class DishIngredientUnitType(Base):
    __tablename__ = "dish_ingredient_unit_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    menu_ingredients = relationship("MenuIngredient", back_populates="unit_type")


# Menu and order types
class MenuCategory(Base):
    __tablename__ = "menu_category"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    menus = relationship("Menu", back_populates="menu_category")
    customer_orders = relationship("CustomerOrder", back_populates="menu_category")


class OrderStatusType(Base):
    __tablename__ = "order_status_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    customer_orders = relationship("CustomerOrder", back_populates="status_type")
    order_status_history = relationship("CustomerOrderStatusHist", back_populates="status_type")


class OrderType(Base):
    __tablename__ = "order_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    customer_orders = relationship("CustomerOrder", back_populates="order_type")


class StatusType(Base):
    __tablename__ = "status_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    orders = relationship("Order", back_populates="status_type")


class StatusCase1Type(Base):
    __tablename__ = "statuscase1_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    orders_case1 = relationship("OrderCase1", back_populates="status_type")


# Tax types
class TaxType(Base):
    __tablename__ = "tax_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    percentage = Column(String, nullable=False)
    validity = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    order_tax_mappings = relationship("OrderTaxMapping", back_populates="tax_type")


class TaxCase1Type(Base):
    __tablename__ = "taxcase1_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    percentage = Column(String, nullable=False)
    validity = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    order_case1_tax_mappings = relationship("OrderCase1TaxMapping", back_populates="tax_type")


class TaxesC1(Base):
    __tablename__ = "taxesC1"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    percentage = Column(Numeric, nullable=False)
    tax_code = Column(String, nullable=False)
    validity = Column(Date, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())


class TaxesType(Base):
    __tablename__ = "taxes_type"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    percentage = Column(String, nullable=False)
    country_id = Column(Integer, ForeignKey("country.id"), nullable=False)
    province_id = Column(Integer, ForeignKey("province.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    country = relationship("Country", back_populates="taxes")
    province = relationship("Province", back_populates="taxes")


# User tables
class User(Base):
    __tablename__ = "user"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    otp = Column(Integer)
    email_verified = Column(Boolean, nullable=False, default=False)
    retry = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    menus = relationship("Menu", back_populates="user")


class UserCase1(Base):
    __tablename__ = "usercase1"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    otp = Column(Integer)
    email_verified = Column(Boolean, nullable=False, default=False)
    retry = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    token = Column(String)
    role_type = Column(Integer)


class Tester(Base):
    __tablename__ = "tester"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())


class OtpVerifications(Base):
    __tablename__ = "otp_verifications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    otp = Column(Integer)
    created_at = Column(DateTime, default=func.current_timestamp())
    expires_at = Column(DateTime)
    is_verified = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)
    updated_at = Column(DateTime, default=func.current_timestamp())
    email = Column(String, nullable=False)
    role_type = Column(Integer)


# Business Owner
class BusinessOwnerCase1(Base):
    __tablename__ = "business_ownercase1"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    restaurant_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    otp = Column(Integer)
    email_verified = Column(Boolean, nullable=False, default=False)
    retry = Column(Integer)
    phone = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    role_type = Column(Integer)
    lat = Column(Double)
    lon = Column(Double)
    legal_business_name = Column(String)
    business_reg_no = Column(String)
    restaurant_type_id = Column(Integer, ForeignKey("restaurant_type.id"))
    cuisine_type_id = Column(Integer, ForeignKey("cuisine_type.id"))
    website_url = Column(String)
    instagram_url = Column(String)
    facebook_url = Column(String)
    yelp_url = Column(String)
    restaurant_address = Column(String)
    city = Column(String)
    postal_code = Column(Integer)
    country_id = Column(Integer, ForeignKey("country.id"))
    map_url = Column(String)
    delivery_time_type_id = Column(Integer, ForeignKey("deliverytime_type.id"))
    delivery_time = Column(Integer)
    delivery_charges_type_id = Column(Integer, ForeignKey("deliverycharges_type.id"))
    delivery_charges = Column(Integer)
    covering_radius = Column(Double)
    password_setup_token = Column(String)
    reactivation_date = Column(DateTime)
    token = Column(String)
    food_safety_lic_url = Column(String)
    food_authority_lic_url = Column(String)
    business_lic_url = Column(String)
    gst_regn_cert_url = Column(String)
    tax_cert_url = Column(String)
    cash = Column(Boolean, default=False)
    card = Column(Boolean, default=False)
    bank_transfer = Column(Boolean, default=False)
    active = Column(Boolean)
    province_id = Column(Integer, ForeignKey("province.id"))
    
    # Relationships
    restaurant_type = relationship("RestaurantType", back_populates="business_owners")
    province = relationship("Province", back_populates="business_owners")
    country = relationship("Country", back_populates="business_owners")
    delivery_time_type = relationship("DeliveryTimeType", back_populates="business_owners")
    delivery_charges_type = relationship("DeliveryChargesType", back_populates="business_owners")
    cuisine_type = relationship("CuisineType", back_populates="business_owners")
    
    bank_accounts = relationship("BankAccounts", back_populates="business_owner")
    business_owner_inventory = relationship("BusinessOwnerInventory", back_populates="business_owner")
    customers = relationship("Customer", back_populates="business_owner")
    customer_orders = relationship("CustomerOrder", back_populates="business_owner")
    menus = relationship("Menu", back_populates="business_owner")
    orders_case1 = relationship("OrderCase1", back_populates="business_owner")
    vendor_orders = relationship("VendorOrders", back_populates="restaurant")
    sm_employees = relationship("SmEmployee", back_populates="business_owner")
    sm_employee_role_types = relationship("SmEmployeeRoleType", back_populates="business_owner")
    wastages = relationship("Wastage", back_populates="business_owner")


# Vendor tables
class Vendor(Base):
    __tablename__ = "vendor"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    contact_person = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    phone = Column(String, nullable=False)
    logo = Column(String)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    user_id = Column(Integer)


class VendorCase1(Base):
    __tablename__ = "vendor_case1"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)


class VendorCase1(Base):
    __tablename__ = "vendorcase1"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    contact_person = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    email_verified = Column(Boolean, nullable=False, default=False)
    phone = Column(String, nullable=False)
    logo = Column(String)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    password_setup_token = Column(String)
    reactivation_date = Column(String)
    role_type = Column(Integer)
    lat = Column(Double)
    lon = Column(Double)
    payment_mode_type_id = Column(Integer, ForeignKey("paymentmode_type.id"))
    business_cert_url = Column(String)
    license_cert_url = Column(String)
    delivery_time = Column(Integer)
    delivery_time_type_id = Column(Integer, ForeignKey("deliverytime_type.id"))
    delivery_charges_type_id = Column(Integer, ForeignKey("deliverycharges_type.id"))
    delivery_charges = Column(Integer)
    covering_radius = Column(Double)
    business_cert_url_change_status_id = Column(Integer, ForeignKey("request_type.id"))
    license_cert_url_change_status_id = Column(Integer, ForeignKey("request_type.id"))
    delivery_time_change_status_id = Column(Integer, ForeignKey("request_type.id"))
    covering_radius_change_status_id = Column(Integer, ForeignKey("request_type.id"))
    transport_type_id = Column(Integer, ForeignKey("transport_type.id"))
    cash = Column(Boolean)
    card = Column(Boolean)
    bank_transfer = Column(Boolean)
    token = Column(String)
    business_name = Column(String)
    shop_address = Column(String)
    city = Column(String)
    province_id = Column(Integer, ForeignKey("province.id"))
    postal_code = Column(Integer)
    country_id = Column(Integer, ForeignKey("country.id"))
    description = Column(String)
    reason = Column(String)
    inactive_date = Column(String)
    
    # Relationships
    province = relationship("Province", back_populates="vendors")
    payment_mode_type = relationship("PaymentModeType", back_populates="vendors")
    delivery_time_type = relationship("DeliveryTimeType", back_populates="vendors")
    delivery_charges_type = relationship("DeliveryChargesType", back_populates="vendors")
    country = relationship("Country", back_populates="vendors")
    transport_type = relationship("TransportType", back_populates="vendors")
    
    business_cert_change_status = relationship("RequestType", foreign_keys=[business_cert_url_change_status_id], back_populates="vendor_business_cert_changes")
    license_cert_change_status = relationship("RequestType", foreign_keys=[license_cert_url_change_status_id], back_populates="vendor_license_cert_changes")
    delivery_time_change_status = relationship("RequestType", foreign_keys=[delivery_time_change_status_id], back_populates="vendor_delivery_time_changes")
    covering_radius_change_status = relationship("RequestType", foreign_keys=[covering_radius_change_status_id], back_populates="vendor_radius_changes")
    
    inventory_case1 = relationship("InventoryCase1", back_populates="vendor")
    orders_case1 = relationship("OrderCase1", back_populates="vendor")
    vendor_inventory = relationship("VendorInventory", back_populates="vendor")
    vendor_orders = relationship("VendorOrders", back_populates="vendor")


# Bank accounts
class BankAccounts(Base):
    __tablename__ = "bank_accounts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("business_ownercase1.id"), nullable=False)
    role_type_id = Column(Integer, nullable=False)
    account_holder_name = Column(String, nullable=False)
    bank_name = Column(String, nullable=False)
    account_number = Column(String)
    iban_number = Column(String)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    business_owner = relationship("BusinessOwnerCase1", back_populates="bank_accounts")


# Inventory tables
class Inventory(Base):
    __tablename__ = "inventory"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    photo_url = Column(String)
    ingredient_type_id = Column(Integer, ForeignKey("ingredient_type.id"), nullable=False)
    price_per_unit = Column(String, nullable=False)
    barcode = Column(String, nullable=False)
    unit_quantity = Column(Integer, nullable=False)
    unit_type_id = Column(Integer, ForeignKey("unit_type.id"), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    is_assigned = Column(Boolean, nullable=False, default=False)
    available = Column(Boolean, default=True)
    min_threshold = Column(Integer)
    max_threshold = Column(Integer)
    vendor_id = Column(Integer)
    current_stock = Column(Double)
    user_id = Column(Integer)
    
    # Relationships
    ingredient_type = relationship("IngredientType", back_populates="inventories")
    unit_type = relationship("UnitType", back_populates="inventories")
    order_inventory_mappings = relationship("OrderInventoryMapping", back_populates="inventory")


class InventoryCase1(Base):
    __tablename__ = "inventorycase1"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    photo_url = Column(String)
    ingredient_type_id = Column(Integer, ForeignKey("ingredientcase1_type.id"), nullable=False)
    price_per_unit = Column(String, nullable=False)
    barcode = Column(String, nullable=False, unique=True)
    unit_quantity = Column(Integer, nullable=False)
    unit_type_id = Column(Integer, ForeignKey("unitcase1_type.id"), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    available = Column(Boolean, default=True)
    vendor_id = Column(Integer, ForeignKey("vendorcase1.id"), nullable=False)
    barcode_url = Column(String)
    min_order_quantity = Column(Integer)
    shelf_life = Column(String)
    delivery_time_frame = Column(String)
    photo_url1 = Column(String)
    photo_url2 = Column(String)
    photo_url3 = Column(String)
    
    # Relationships
    unit_type = relationship("UnitCase1Type", back_populates="inventory_case1")
    ingredient_type = relationship("IngredientCase1Type", back_populates="inventory_case1")
    vendor = relationship("VendorCase1", back_populates="inventory_case1")
    business_owner_inventory = relationship("BusinessOwnerInventory", back_populates="inventory")
    menu_ingredients = relationship("MenuIngredient", back_populates="ingredient")
    order_case1_inventory_mappings = relationship("OrderCase1InventoryMapping", back_populates="inventory")
    wastages = relationship("Wastage", back_populates="ingredient")


class InventoryItems(Base):
    __tablename__ = "inventory_items"
    
    item_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    current_quantity = Column(Double, nullable=False)
    unit = Column(String, nullable=False)
    reorder_point = Column(Double, nullable=False)
    average_daily_usage = Column(Double, nullable=False)
    last_updated = Column(DateTime, nullable=False)


class BusinessOwnerInventory(Base):
    __tablename__ = "business_owner_inventory"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_owner_id = Column(Integer, ForeignKey("business_ownercase1.id"), nullable=False)
    inventory_id = Column(Integer, ForeignKey("inventorycase1.id"))
    stock_quantity = Column(Integer, nullable=False, default=0)
    expiry_date = Column(String)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    vendor_id = Column(Integer)
    min_quantity_level = Column(Integer)
    automate_order_quantity = Column(Integer)
    automate_order = Column(Boolean, default=False)
    in_radius = Column(Boolean)
    
    # Relationships
    inventory = relationship("InventoryCase1", back_populates="business_owner_inventory")
    business_owner = relationship("BusinessOwnerCase1", back_populates="business_owner_inventory")


class VendorInventory(Base):
    __tablename__ = "vendor_inventory"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vendor_id = Column(Integer, ForeignKey("vendorcase1.id"))
    ingredient_name = Column(Text, nullable=False)
    unit = Column(Text)
    stock_quantity = Column(Numeric)
    cost_price = Column(Numeric)
    reorder_threshold = Column(Numeric)
    expiry_date = Column(Date)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    vendor = relationship("VendorCase1", back_populates="vendor_inventory")


class Wastage(Base):
    __tablename__ = "wastage"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_owner_id = Column(Integer, ForeignKey("business_ownercase1.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("inventorycase1.id"), nullable=False)
    unit_type = Column(String, nullable=False)
    wastage_qty = Column(Double, nullable=False)
    loss_value = Column(Double, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    business_owner = relationship("BusinessOwnerCase1", back_populates="wastages")
    ingredient = relationship("InventoryCase1", back_populates="wastages")


# Customer tables
class Customer(Base):
    __tablename__ = "customer"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    photo = Column(String)
    email = Column(String)
    phone = Column(String)
    address = Column(String)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    user_id = Column(Integer)
    city = Column(String)
    province_id = Column(Integer, ForeignKey("province.id"))
    country_id = Column(Integer, ForeignKey("country.id"))
    business_owner_id = Column(Integer, ForeignKey("business_ownercase1.id"), default=3)
    
    # Relationships
    business_owner = relationship("BusinessOwnerCase1", back_populates="customers")
    country = relationship("Country", back_populates="customers")
    province = relationship("Province", back_populates="customers")
    customer_orders = relationship("CustomerOrder", back_populates="customer")
    reviews = relationship("Review", back_populates="customer")


# Menu tables
class Menu(Base):
    __tablename__ = "menu"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    photo = Column(String)
    price = Column(Integer, nullable=False)
    currency = Column(String, default='USD')
    quantity = Column(Integer, default=0)
    weight = Column(String)
    menu_category_id = Column(Integer, ForeignKey("menu_category.id"))
    datetime = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    business_owner_id = Column(Integer, ForeignKey("business_ownercase1.id"), default=3)
    
    # Relationships
    menu_category = relationship("MenuCategory", back_populates="menus")
    user = relationship("User", back_populates="menus")
    business_owner = relationship("BusinessOwnerCase1", back_populates="menus")
    menu_ingredients = relationship("MenuIngredient", back_populates="menu")
    customer_order_menu_mappings = relationship("CustomerOrderMenuMapping", back_populates="menu")
    reviews = relationship("Review", back_populates="menu")
    menu_price_history = relationship("MenuPriceHistory", back_populates="menu")


class MenuIngredient(Base):
    __tablename__ = "menu_ingredient"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    menu_id = Column(Integer, ForeignKey("menu.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("inventorycase1.id"), nullable=False)
    quantity = Column(String)
    unit_type_id = Column(Integer, ForeignKey("dish_ingredient_unit_type.id"))
    
    # Relationships
    unit_type = relationship("DishIngredientUnitType", back_populates="menu_ingredients")
    ingredient = relationship("InventoryCase1", back_populates="menu_ingredients")
    menu = relationship("Menu", back_populates="menu_ingredients")


class MenuPriceHistory(Base):
    __tablename__ = "menu_price_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    menu_id = Column(Integer, ForeignKey("menu.id"), nullable=False)
    old_price = Column(Numeric)
    new_price = Column(Numeric, nullable=False)
    effective_date = Column(DateTime, nullable=False, default=func.now())
    reason = Column(Text)
    changed_by = Column(String)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())
    
    # Relationships
    menu = relationship("Menu", back_populates="menu_price_history")


# Customer order tables
class CustomerOrder(Base):
    __tablename__ = "customer_order"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    delivery_datetime = Column(String, nullable=False)
    status_type_id = Column(Integer, ForeignKey("order_status_type.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customer.id"))
    employee_id = Column(Integer)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    user_id = Column(Integer)
    menu_category_id = Column(Integer, ForeignKey("menu_category.id"))
    order_type_id = Column(Integer, ForeignKey("order_type.id"))
    price = Column(Integer)
    business_owner_id = Column(Integer, ForeignKey("business_ownercase1.id"), default=3)
    
    # Relationships
    customer = relationship("Customer", back_populates="customer_orders")
    status_type = relationship("OrderStatusType", back_populates="customer_orders")
    business_owner = relationship("BusinessOwnerCase1", back_populates="customer_orders")
    order_type = relationship("OrderType", back_populates="customer_orders")
    menu_category = relationship("MenuCategory", back_populates="customer_orders")
    customer_order_menu_mappings = relationship("CustomerOrderMenuMapping", back_populates="customer_order")
    order_status_history = relationship("CustomerOrderStatusHist", back_populates="customer_order")


class CustomerOrderMenuMapping(Base):
    __tablename__ = "customer_order_menu_mapping"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    menu_id = Column(Integer, ForeignKey("menu.id"), nullable=False)
    customer_order_id = Column(Integer, ForeignKey("customer_order.id"), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    menu = relationship("Menu", back_populates="customer_order_menu_mappings")
    customer_order = relationship("CustomerOrder", back_populates="customer_order_menu_mappings")


class CustomerOrderStatusHist(Base):
    __tablename__ = "customer_order_status_hist"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_order_id = Column(Integer, ForeignKey("customer_order.id"), nullable=False)
    status_type_id = Column(Integer, ForeignKey("order_status_type.id"), nullable=False)
    status_datetime = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    customer_order = relationship("CustomerOrder", back_populates="order_status_history")
    status_type = relationship("OrderStatusType", back_populates="order_status_history")


# Review table
class Review(Base):
    __tablename__ = "review"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    menu_id = Column(Integer, ForeignKey("menu.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False)
    description = Column(String, nullable=False)
    rating = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    customer = relationship("Customer", back_populates="reviews")
    menu = relationship("Menu", back_populates="reviews")


# Order tables
class Order(Base):
    __tablename__ = "order"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    delivery_date = Column(String, nullable=False)
    status_type_id = Column(Integer, ForeignKey("status_type.id"), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    user_id = Column(Integer)
    comment = Column(String)
    
    # Relationships
    status_type = relationship("StatusType", back_populates="orders")
    order_inventory_mappings = relationship("OrderInventoryMapping", back_populates="order")
    order_tax_mappings = relationship("OrderTaxMapping", back_populates="order")


class OrderCase_1(Base):
    __tablename__ = "order_case1"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vendor_id = Column(Integer, ForeignKey("vendor_case1.id"))
    status_type_id = Column(Integer)
    order_date = Column(DateTime)
    actual_delivery_date = Column(DateTime)
    expected_delivery_date = Column(DateTime)
    order_cost = Column(Numeric)
    
    # Note: This table has minimal relationships due to limited foreign key constraints in schema


class OrderCase1(Base):
    __tablename__ = "ordercase1"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    delivery_date = Column(Text, nullable=False)
    status_type_id = Column(Integer, ForeignKey("statuscase1_type.id"), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    business_owner_id = Column(Integer, ForeignKey("business_ownercase1.id"))
    comment = Column(String)
    vendor_id = Column(Integer, ForeignKey("vendorcase1.id"))
    payment_invoice_url = Column(String)
    
    # Relationships
    status_type = relationship("StatusCase1Type", back_populates="orders_case1")
    vendor = relationship("VendorCase1", back_populates="orders_case1")
    business_owner = relationship("BusinessOwnerCase1", back_populates="orders_case1")
    order_case1_inventory_mappings = relationship("OrderCase1InventoryMapping", back_populates="order")
    order_case1_tax_mappings = relationship("OrderCase1TaxMapping", back_populates="order")


class OrderInventoryMapping(Base):
    __tablename__ = "order_inventory_mapping"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("order.id"), nullable=False)
    inventory_id = Column(Integer, ForeignKey("inventory.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    expiry_date = Column(String)
    batch = Column(String)
    
    # Relationships
    inventory = relationship("Inventory", back_populates="order_inventory_mappings")
    order = relationship("Order", back_populates="order_inventory_mappings")


class OrderCase1InventoryMapping(Base):
    __tablename__ = "ordercase1_inventory_mapping"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("ordercase1.id"), nullable=False)
    inventory_id = Column(Integer, ForeignKey("inventorycase1.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    expiry_date = Column(String)
    batch = Column(String)
    
    # Relationships
    inventory = relationship("InventoryCase1", back_populates="order_case1_inventory_mappings")
    order = relationship("OrderCase1", back_populates="order_case1_inventory_mappings")


class OrderTaxMapping(Base):
    __tablename__ = "order_tax_mapping"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("order.id"), nullable=False)
    tax_type_id = Column(Integer, ForeignKey("tax_type.id"), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    tax_type = relationship("TaxType", back_populates="order_tax_mappings")
    order = relationship("Order", back_populates="order_tax_mappings")


class OrderCase1TaxMapping(Base):
    __tablename__ = "ordercase1_tax_mapping"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("ordercase1.id"), nullable=False)
    tax_type_id = Column(Integer, ForeignKey("taxcase1_type.id"), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    tax_type = relationship("TaxCase1Type", back_populates="order_case1_tax_mappings")
    order = relationship("OrderCase1", back_populates="order_case1_tax_mappings")


class VendorOrders(Base):
    __tablename__ = "vendor_orders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vendor_id = Column(Integer, ForeignKey("vendorcase1.id"))
    restaurant_id = Column(Integer, ForeignKey("business_ownercase1.id"))
    order_date = Column(Date, nullable=False)
    status = Column(Text, default='pending')
    total_cost = Column(Numeric)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    vendor = relationship("VendorCase1", back_populates="vendor_orders")
    restaurant = relationship("BusinessOwnerCase1", back_populates="vendor_orders")


# Employee tables
class Employee(Base):
    __tablename__ = "employee"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    photo = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    role_type = Column(Integer, nullable=False)
    date_of_joining = Column(String, nullable=False)
    department = Column(String, nullable=False)
    salary = Column(String, nullable=False)
    active = Column(Boolean, default=True)
    on_leave = Column(Boolean, default=False)
    terminated = Column(Boolean, default=False)
    termination_date = Column(String)
    active_manager = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    otp = Column(Integer)
    email_verified = Column(Boolean)
    password = Column(String)
    
    # Relationships
    employee_benefits = relationship("EmployeeBenefits", back_populates="employee")
    employee_documents = relationship("EmployeeDocument", back_populates="employee")
    employee_shifts = relationship("EmployeeShift", back_populates="employee")


class SmEmployee(Base):
    __tablename__ = "sm_employee"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    photo = Column(String)
    email = Column(String)
    phone = Column(String)
    role_type = Column(String)
    date_of_joining = Column(Date)
    department = Column(String)
    salary = Column(Numeric)
    active = Column(Boolean, default=True)
    on_leave = Column(Boolean, default=False)
    terminated = Column(Boolean, default=False)
    termination_date = Column(Date)
    active_manager = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    otp = Column(String)
    email_verified = Column(Boolean, default=False)
    password = Column(String)
    business_owner_id = Column(Integer, ForeignKey("business_ownercase1.id"))
    
    # Relationships
    business_owner = relationship("BusinessOwnerCase1", back_populates="sm_employees")


class SmEmployeeRoleType(Base):
    __tablename__ = "sm_employeeroletype"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_owner_id = Column(Integer, ForeignKey("business_ownercase1.id"))
    value = Column(String, nullable=False)
    code = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    
    # Relationships
    business_owner = relationship("BusinessOwnerCase1", back_populates="sm_employee_role_types")


class EmployeeBenefits(Base):
    __tablename__ = "employee_benefits"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employee.id"), nullable=False)
    name = Column(String, nullable=False)
    amount = Column(String, nullable=False)
    currency = Column(String, nullable=False)
    type = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    employee = relationship("Employee", back_populates="employee_benefits")


class EmployeeDocument(Base):
    __tablename__ = "employee_document"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employee.id"), nullable=False)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    employee = relationship("Employee", back_populates="employee_documents")


class EmployeeShift(Base):
    __tablename__ = "employee_shift"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employee.id"), nullable=False)
    day = Column(String, nullable=False)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)
    duration = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    employee = relationship("Employee", back_populates="employee_shifts")


# Day and timing tables
class DayTable(Base):
    __tablename__ = "day_table"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    roles_type_id = Column(Integer, nullable=False)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    day_timing_tables = relationship("DayTimingTable", back_populates="day_table")


class DayTimingTable(Base):
    __tablename__ = "day_timing_table"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    day_table_id = Column(Integer, ForeignKey("day_table.id"), nullable=False)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    day_table = relationship("DayTable", back_populates="day_timing_tables")


# Notification table
class Notification(Base):
    __tablename__ = "notification"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    recipient_id = Column(Integer, nullable=False)
    sender_id = Column(Integer, nullable=False)
    order_id = Column(Integer, nullable=False, default=0)
    message = Column(String)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    status = Column(Boolean)
    isread = Column(Boolean, nullable=False, default=False)
    image_url = Column(String)
    role_type = Column(Integer)


# Weather cache table
class WeatherCache(Base):
    __tablename__ = "weather_cache"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    latitude = Column(Numeric, nullable=False)
    longitude = Column(Numeric, nullable=False)
    temp_max = Column(Numeric)
    temp_min = Column(Numeric)
    precipitation = Column(Numeric)
    weather_code = Column(Integer)
    api_call_time = Column(DateTime, default=func.now())