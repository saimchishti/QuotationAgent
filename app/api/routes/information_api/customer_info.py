# RESTAURANT-AGENT-MAIN/app/api/routes/information_api/customer_info.py

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict

from app.db.session import get_restaurant_db
from app.services.dataprovider_customer import ( # Changed import path here
    get_order_volume_by_owner,
    get_order_frequency_by_customer
)

router = APIRouter()



# ------------------ 1. Order Volume Tracker ------------------
@router.get("/customer/order-volume", tags=["Information - Customer Orders"])
async def order_volume_tracker(
    business_owner_id: int = Query(..., description="Business Owner ID to filter orders"),
    db: AsyncSession = Depends(get_restaurant_db)
):
    """
    Tracks the number of orders placed over a specified period, providing a
    daily total and a cumulative breakdown of all order statuses.
    """
    try:
        # Call the service function to get the raw data (no changes needed here)
        order_data = await get_order_volume_by_owner(db, business_owner_id)

        if not order_data:
            return {"data": {}, "message": "No order volume data found for the specified period."}

        # Restructure the data to include a daily total and a status breakdown.
        # The format will be: { "date": { "total_orders": X, "status_breakdown": { ... } } }
        response_data = defaultdict(lambda: {"total_orders": 0, "status_breakdown": {}})

        for row in order_data:
            date_str = row.order_date.isoformat()
            status_name = row.status_name
            order_count = row.order_count

            # Add the specific status count to the breakdown
            response_data[date_str]["status_breakdown"][status_name] = order_count
            
            # Add to the cumulative daily total
            response_data[date_str]["total_orders"] += order_count

        return {"success": True, "data": response_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ... (keep the order_frequency_by_customer function as is) ...
# ------------------ 2. Order Frequency by Customer ------------------
@router.get("/customer/order-frequency", tags=["Information - Customer Orders"])
async def order_frequency_by_customer(
    business_owner_id: int = Query(..., description="Business Owner ID to filter customers"),
    db: AsyncSession = Depends(get_restaurant_db)
):
    """
    Calculates how many orders each customer has placed.
    This helps identify the most frequent and loyal customers.
    """
    try:
        # Call the service function to get data
        frequency_data = await get_order_frequency_by_customer(db, business_owner_id)

        if not frequency_data:
            return {"data": [], "message": "No customer order frequency data found."}

        # Format the response
        response = [
            {
                "customer_id": row.customer_id,
                "customer_name": row.customer_name,
                "customer_email": row.customer_email,
                "total_orders": row.order_count
            }
            for row in frequency_data
        ]

        return {"success": True, "data": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
