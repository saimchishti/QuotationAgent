import httpx
from langchain.tools import tool
from core.constants import business_owner_id
BASE_URL = "http://localhost:8000"

# =====================
# CUSTOMER TOOLS
# =====================

@tool
async def order_volume_tracker_tool(business_owner_id):
    """Tracks daily order volume and status breakdown for a business owner."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/customer_orders/customer/order-volume", params={"business_owner_id": business_owner_id})
        return resp.json()

@tool
async def order_frequency_tool(business_owner_id):
    """Gets top customers ranked by order frequency."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/customer_orders/customer/order-frequency", params={"business_owner_id": business_owner_id})
        return resp.json()


# =====================
# EMPLOYEE TOOLS
# =====================

@tool
async def employee_roster_tool(business_owner_id):
    """Returns the employee roster for a business owner."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/employees/employees/roster", params={"business_owner_id": business_owner_id})
        return resp.json()

@tool
async def employee_shift_tool(business_owner_id):
    """Returns the shift schedule of employees."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/employees/employees/shifts", params={"business_owner_id": business_owner_id})
        return resp.json()

@tool
async def attendance_tracker_tool(business_owner_id):
    """Tracks employee attendance for a business owner."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/employees/employees/attendance", params={"business_owner_id": business_owner_id})
        return resp.json()

@tool
async def payroll_summary_tool(business_owner_id):
    """Returns payroll summary data."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/employees/employees/payroll-summary", params={"business_owner_id": business_owner_id})
        return resp.json()


# =====================
# INVENTORY ORDER TOOLS
# =====================

@tool
async def purchase_orders_tool(business_owner_id):
    """Lists all purchase orders for the business owner."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/inventory_orders/purchase-orders/{business_owner_id}")
        return resp.json()

@tool
async def supplier_orders_tool(business_owner_id):
    """Shows supplier-wise order history."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/inventory_orders/supplier-orders/{business_owner_id}")
        return resp.json()

@tool
async def order_cost_breakdown_tool(business_owner_id):
    """Shows cost breakdown per order."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/inventory_orders/cost-breakdown/{business_owner_id}")
        return resp.json()

@tool
async def pending_deliveries_tool(business_owner_id):
    """Lists all pending deliveries."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/inventory_orders/pending-deliveries/{business_owner_id}")
        return resp.json()

@tool
async def received_inventory_log_tool(business_owner_id):
    """Returns log of received inventory."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/inventory_orders/received-log/{business_owner_id}")
        return resp.json()

@tool
async def rejected_orders_log_tool(business_owner_id):
    """Returns log of rejected orders."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/inventory_orders/rejected-orders-log", params={"business_owner_id": business_owner_id})
        return resp.json()


# =====================
# MENU TOOLS
# =====================

@tool
async def menu_items_tool(business_owner_id):
    """Returns all menu items with ingredients."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/information/menu/items", params={"business_owner_id": business_owner_id})
        return resp.json()

@tool
async def menu_categories_tool(business_owner_id):
    """Returns categorized menu information."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/information/menu/categories", params={"business_owner_id": business_owner_id})
        return resp.json()

@tool
async def item_availability_tool(business_owner_id):
    """Checks menu item availability based on ingredients."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/information/menu/availability", params={"business_owner_id": business_owner_id})
        return resp.json()

@tool
async def price_history_tool(business_owner_id):
    """Returns price change history of menu items."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/information/menu/price-history", params={"business_owner_id": business_owner_id})
        return resp.json()


# =====================
# INVENTORY TOOLS
# =====================

@tool
async def inventory_overview_tool(business_owner_id: int):
    """Provides current inventory snapshot for the given business owner."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "http://localhost:8000/api/inventory/overview",
            params={"business_owner_id": business_owner_id}
        )
        return resp.json()


@tool
async def inventory_expiry_tool(business_owner_id: int):
    """Shows items from the inventory nearing expiry for the given business owner."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "http://localhost:8000/api/inventory/expiry", 
            params={"business_owner_id": business_owner_id}
        )
        return resp.json()


@tool
async def inventory_cost_breakdown_tool(business_owner_id: int):
    """Breaks down inventory cost by item/category for the given business owner."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "http://localhost:8000/api/inventory/cost-breakdown",
            params={"business_owner_id": business_owner_id}
        )
        return resp.json()


@tool
async def inventory_by_supplier_or_brand_tool(business_owner_id: int):
    """Groups inventory by supplier or brand for the given business owner."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "http://127.0.0.1:8000/api/inventory/by-supplier-or-brand",
            params={"business_owner_id": business_owner_id}
        )
        return resp.json()

# =====================
# WASTAGE TOOLS
# =====================

@tool
async def daily_wastage_log_tool(business_owner_id):
    """Returns daily ingredient wastage grouped by date."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/wastage/daily-wastage-log", params={"business_owner_id": business_owner_id})
        return resp.json()

@tool
async def order_to_waste_correlation_tool(business_owner_id):
    """Returns correlation of order volume with wastage."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/wastage/order-to-waste-correlation", params={"business_owner_id": business_owner_id})
        return resp.json()



# =====================
# VENDOR TOOLS
# =====================

@tool
async def vendor_directory_tool(business_owner_id):
    """Lists vendors with contact info, ingredients, and linked branches. Optional filter by Business Owner ID."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/information/vendor/directory", params={"business_owner_id": business_owner_id})
        return resp.json()

@tool
async def ingredient_vendor_mapper_tool(business_owner_id):
    """Shows which vendor supplies each ingredient."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/information/vendor/ingredient-mapper", params={"business_owner_id": business_owner_id})
        return resp.json()

@tool
async def vendor_performance_tracker_tool(business_owner_id):
    """Tracks vendor performance (cost, delivery time, status) for a business owner."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/information/vendor/performance", params={"business_owner_id": business_owner_id})
        return resp.json()

@tool
async def ingredient_sourcing_optimizer_tool(business_owner_id, ingredient_name: str):
    """Finds vendors for a specific ingredient, comparing price and delivery time."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/information/vendor/sourcing-optimizer", 
            params={"business_owner_id": business_owner_id, "ingredient_name": ingredient_name}
        )
        return resp.json()

@tool
async def vendor_branch_linkage_tool(business_owner_id: int):
    """Shows which vendors a business owner (branch) uses and how often."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/information/vendor/branch-linkage", 
            params={"business_owner_id": business_owner_id}
        )
        return resp.json()