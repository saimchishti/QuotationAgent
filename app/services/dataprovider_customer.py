# RESTAURANT-AGENT-MAIN/app/services/dataprovider_customer.py

from sqlalchemy.future import select
from sqlalchemy import func, case
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from sqlalchemy import cast, Date
from app.core.constants import order_limit as limit
from app.core.constants import days as days
from app.db.models import CustomerOrder, Customer, OrderStatusType

"""
async def get_order_volume_by_owner(db: AsyncSession, business_owner_id: int, days: int):
    """
  #  Fetches the daily order volume for a specific business owner over a given period.
"""
    start_date = datetime.utcnow() - timedelta(days=days)

    query = (
        select(
            func.date(CustomerOrder.delivery_datetime).label('order_date'),
            func.count(CustomerOrder.id).label('total_orders'),
            func.sum(
                case(
                    (OrderStatusType.value == 'Completed', 1),
                    else_=0
                )
            ).label('completed_orders'),
            func.sum(
                case(
                    (OrderStatusType.value == 'Cancelled', 1),
                    else_=0
                )
            ).label('cancelled_orders')
        )
        .join(OrderStatusType, CustomerOrder.status_type_id == OrderStatusType.id)
        .where(CustomerOrder.business_owner_id == business_owner_id)
        .where(CustomerOrder.created_at >= start_date)
        .group_by(func.date(CustomerOrder.delivery_datetime))
        .order_by(func.date(CustomerOrder.delivery_datetime))
    )

    result = await db.execute(query)
    return result.fetchall()
"""

# RESTAURANT-AGENT-MAIN/app/services/dataprovider_customer.py

# Add this import at the top of the file if it's not there

async def get_order_volume_by_owner(db: AsyncSession, business_owner_id: int):
    """
    Fetches the daily order volume grouped by each status type for a specific 
    business owner over a given period.
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    query = (
        select(
            cast(CustomerOrder.delivery_datetime, Date).label('order_date'),
            # --- CHANGE #1: Use .name instead of .value ---
            OrderStatusType.value.label('status_name'),
            func.count(CustomerOrder.id).label('order_count')
        )
        .join(OrderStatusType, CustomerOrder.status_type_id == OrderStatusType.id)
        .where(CustomerOrder.business_owner_id == business_owner_id)
        .where(cast(CustomerOrder.created_at, Date) >= start_date.date())
        .group_by(
            cast(CustomerOrder.delivery_datetime, Date),
            # --- CHANGE #2: Group by .name as well ---
            OrderStatusType.value
        )
        .order_by(cast(CustomerOrder.delivery_datetime, Date))
    )

    result = await db.execute(query)
    return result.fetchall()


async def get_order_frequency_by_customer(db: AsyncSession, business_owner_id: int):
    limit = 20
    """
    Fetches the order frequency for each customer for a specific business owner.
    """
    query = (
        select(
            Customer.id.label("customer_id"),
            Customer.name.label("customer_name"),
            Customer.email.label("customer_email"),
            func.count(CustomerOrder.id).label("order_count")
        )
        .join(Customer, CustomerOrder.customer_id == Customer.id)
        .where(CustomerOrder.business_owner_id == business_owner_id)
        .group_by(Customer.id, Customer.name, Customer.email)
        .order_by(func.count(CustomerOrder.id).desc())
        .limit(limit)
    )

    result = await db.execute(query)
    return result.fetchall()
