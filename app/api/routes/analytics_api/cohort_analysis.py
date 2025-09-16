from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, text, cast, DateTime
from db.models import CustomerOrder, CustomerOrderMenuMapping, Menu, OrderCase1
from collections import defaultdict

# ------------------ 1. Retention Curve ------------------
async def get_retention_curve(business_owner_id: int, db: AsyncSession):
    query = (
        select(
            func.date_trunc(text("'day'"), cast(CustomerOrder.delivery_datetime, DateTime)).label('order_date'),
            func.min(
                func.date_trunc(text("'day'"), cast(CustomerOrder.delivery_datetime, DateTime))
            ).over(partition_by=CustomerOrder.customer_id).label('cohort_date'),
            CustomerOrder.customer_id
        )
        .select_from(CustomerOrder)
        .join(CustomerOrderMenuMapping, CustomerOrder.id == CustomerOrderMenuMapping.customer_order_id)
        .join(Menu, Menu.id == CustomerOrderMenuMapping.menu_id)
        .join(OrderCase1, OrderCase1.id == CustomerOrder.id)
        .where(OrderCase1.business_owner_id == business_owner_id)
    )

    result = await db.execute(query)
    rows = result.fetchall()

    if not rows:
        return {"data": [], "message": "No data found for retention curve."}

    retention = {}
    for order_date, cohort_date, customer_id in rows:
        if not order_date or not cohort_date:
            continue
        cohort_key = cohort_date.date()
        week_diff = (order_date.date() - cohort_key).days // 7
        retention.setdefault(cohort_key, {}).setdefault(week_diff, set()).add(customer_id)

    response = []
    for cohort, weeks in retention.items():
        cohort_size = len(weeks.get(0, set()))
        for week, users in weeks.items():
            response.append({
                "cohort": cohort.isoformat(),
                "week": week,
                "retention": round(len(users) / cohort_size * 100, 2) if cohort_size else 0
            })

    return {"data": response}


# ------------------ 2. Cohort Revenue Contribution ------------------
async def get_cohort_revenue_contribution(business_owner_id: int, db: AsyncSession):
    subquery = (
        select(
            CustomerOrder.id.label("order_id"),
            func.min(func.date_trunc(text("'day'"), cast(CustomerOrder.delivery_datetime, DateTime)))
                .over(partition_by=CustomerOrder.customer_id).label('cohort_date'),
            CustomerOrder.price.label("price")
        )
        .select_from(CustomerOrder)
        .join(CustomerOrderMenuMapping, CustomerOrder.id == CustomerOrderMenuMapping.customer_order_id)
        .join(Menu, Menu.id == CustomerOrderMenuMapping.menu_id)
        .join(OrderCase1, OrderCase1.id == CustomerOrder.id)
        .where(OrderCase1.business_owner_id == business_owner_id)
        .subquery()
    )

    query = (
        select(
            subquery.c.cohort_date,
            func.sum(subquery.c.price).label("total_revenue")
        )
        .group_by(subquery.c.cohort_date)
        .order_by(subquery.c.cohort_date)
    )

    result = await db.execute(query)
    rows = result.fetchall()

    if not rows:
        return {"data": [], "message": "No data found for cohort revenue."}

    response = [
        {"cohort": row.cohort_date.date().isoformat(), "revenue": float(row.total_revenue)}
        for row in rows
    ]
    return {"data": response}


# ------------------ 3. Repeat Purchase Rate by Cohort ------------------
async def get_repeat_purchase_rate_by_cohort(business_owner_id: int, db: AsyncSession):
    query = (
        select(
            CustomerOrder.customer_id,
            func.min(func.date_trunc(text("'week'"), cast(CustomerOrder.delivery_datetime, DateTime)))
                .label('cohort_date'),
            func.count(CustomerOrder.id).label("order_count")
        )
        .select_from(CustomerOrder)
        .join(CustomerOrderMenuMapping, CustomerOrder.id == CustomerOrderMenuMapping.customer_order_id)
        .join(Menu, Menu.id == CustomerOrderMenuMapping.menu_id)
        .join(OrderCase1, OrderCase1.id == CustomerOrder.id)
        .where(OrderCase1.business_owner_id == business_owner_id)
        .group_by(CustomerOrder.customer_id)
    )

    result = await db.execute(query)
    rows = result.fetchall()

    cohorts = defaultdict(lambda: {"repeat": 0, "total": 0})
    for customer_id, cohort_date, order_count in rows:
        cohort_key = cohort_date.date()
        cohorts[cohort_key]["total"] += 1
        if order_count > 1:
            cohorts[cohort_key]["repeat"] += 1

    response = [
        {
            "cohort": cohort.isoformat(),
            "repeat_rate": round((data["repeat"] / data["total"]) * 100, 2) if data["total"] else 0
        }
        for cohort, data in sorted(cohorts.items())
    ]
    return {"data": response}


# ------------------ 4. Average Spend per Order by Cohort ------------------
async def get_avg_spend_by_cohort(business_owner_id: int, db: AsyncSession):
    subquery = (
        select(
            CustomerOrder.id.label("order_id"),
            func.date_trunc(text("'week'"), cast(CustomerOrder.delivery_datetime, DateTime)).label("order_week"),
            func.min(func.date_trunc(text("'week'"), cast(CustomerOrder.delivery_datetime, DateTime)))
                .over(partition_by=CustomerOrder.customer_id).label("cohort_date"),
            CustomerOrder.price.label("price")
        )
        .select_from(CustomerOrder)
        .join(CustomerOrderMenuMapping, CustomerOrder.id == CustomerOrderMenuMapping.customer_order_id)
        .join(Menu, Menu.id == CustomerOrderMenuMapping.menu_id)
        .join(OrderCase1, OrderCase1.id == CustomerOrder.id)
        .where(OrderCase1.business_owner_id == business_owner_id)
        .subquery()
    )

    query = (
        select(
            subquery.c.cohort_date,
            subquery.c.order_week,
            func.avg(subquery.c.price).label("avg_spend")
        )
        .group_by(subquery.c.cohort_date, subquery.c.order_week)
        .order_by(subquery.c.cohort_date, subquery.c.order_week)
    )

    result = await db.execute(query)
    rows = result.fetchall()

    response = [
        {
            "cohort": row.cohort_date.date().isoformat(),
            "date": row.order_week.date().isoformat(),
            "avg_order_value": round(row.avg_spend, 2)
        }
        for row in rows
    ]
    return {"data": response}


# ------------------ 5. Drop-Off Funnel Analysis ------------------
async def get_dropoff_funnel(business_owner_id: int, db: AsyncSession):
    query = (
        select(
            CustomerOrder.customer_id,
            func.count(CustomerOrder.id).label("order_count")
        )
        .select_from(CustomerOrder)
        .join(CustomerOrderMenuMapping, CustomerOrder.id == CustomerOrderMenuMapping.customer_order_id)
        .join(Menu, Menu.id == CustomerOrderMenuMapping.menu_id)
        .join(OrderCase1, OrderCase1.id == CustomerOrder.id)
        .where(OrderCase1.business_owner_id == business_owner_id)
        .group_by(CustomerOrder.customer_id)
    )

    result = await db.execute(query)
    rows = result.fetchall()

    signup_count = len(rows)
    first_order = sum(1 for _, count in rows if count >= 1)
    second_order = sum(1 for _, count in rows if count >= 2)
    third_plus_order = sum(1 for _, count in rows if count >= 3)

    return {
        "data": {
            "signup": signup_count,
            "first_order": first_order,
            "second_order": second_order,
            "third_plus_order": third_plus_order
        }
    }


# ------------------ 6. Top Categories by Frequent Buyers ------------------
async def get_top_categories_by_frequent_buyers(business_owner_id: int, min_orders: int, db: AsyncSession):
    subquery = (
        select(
            CustomerOrder.customer_id,
            func.count(CustomerOrder.id).label("order_count")
        )
        .join(OrderCase1, OrderCase1.id == CustomerOrder.id)
        .where(OrderCase1.business_owner_id == business_owner_id)
        .group_by(CustomerOrder.customer_id)
        .having(func.count(CustomerOrder.id) >= min_orders)
        .subquery()
    )

    query = (
        select(
            Menu.menu_category_id,
            func.count(Menu.id).label("total_orders")
        )
        .join(CustomerOrderMenuMapping, Menu.id == CustomerOrderMenuMapping.menu_id)
        .join(CustomerOrder, CustomerOrder.id == CustomerOrderMenuMapping.customer_order_id)
        .join(OrderCase1, OrderCase1.id == CustomerOrder.id)
        .join(subquery, subquery.c.customer_id == CustomerOrder.customer_id)
        .where(OrderCase1.business_owner_id == business_owner_id)
        .group_by(Menu.menu_category_id)
    )

    result = await db.execute(query)
    rows = result.fetchall()

    return {
        "data": [
            {"menu_category_id": row.menu_category_id, "order_count": row.total_orders}
            for row in rows
        ]
    }


