from fastapi import FastAPI
from app.api.routes.information_api.owner_inventory import router as inventory_router
from app.api.routes.information_api.empolyess_info import router as employees_router
from app.api.routes.information_api.customer_info import router as customer_order_router
from app.api.routes.information_api.inventory_order_info import router as purchase_order
from app.api.routes.information_api.menu_detail import router as menu_details_router
from app.api.routes.information_api.vendor_details import router as vendor_details_router
from app.api.routes.information_api.wastage_info import router as wastage

from app.api.routes.information_api.customer_info import router as customer_order_router

app = FastAPI()

# Include the inventory router
app.include_router(inventory_router, prefix="/api/inventory", tags=["Inventory"])

# Include the employees router
app.include_router(employees_router, prefix="/api/employees", tags=["Employees"])

# Include the new menu details router
app.include_router(menu_details_router, prefix="/information", tags=["Information - Menu Details"])

# Include the customer order router
app.include_router(customer_order_router, prefix="/api/customer_orders", tags=["Information - Customer Orders"])

# Include the Inventory order router
app.include_router(purchase_order, prefix="/api/inventory_orders", tags=["Inventory Orders"])

# Include the new vendor details router
app.include_router(vendor_details_router, prefix="/information", tags=["Information - Vendor Details"])

# Include the Wastage Router
app.include_router(wastage, prefix="/api/wastage", tags=["Wastage"])


from app.api.routes.test import router as test_router
app.include_router(test_router, prefix="/api/test", tags=["Test"])
