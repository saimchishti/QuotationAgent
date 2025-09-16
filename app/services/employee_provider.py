from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Numeric
from app.db.models import ( SmEmployee,                          
SmEmployeeRoleType,                          
BusinessOwnerCase1,                            
EmployeeShift,
EmployeeBenefits, 
)
from app.db.session import RestaurantSessionLocal


async def get_employee_roster(business_owner_id: int):
    async with RestaurantSessionLocal() as session:
        stmt = (
            select(
                SmEmployee.id,
                SmEmployee.name,
                SmEmployee.active,
                SmEmployee.on_leave,
                SmEmployee.terminated,
                SmEmployeeRoleType.value.label("role"),
            )
            .join(SmEmployeeRoleType, SmEmployee.role_type == SmEmployeeRoleType.id)
            .join(BusinessOwnerCase1, SmEmployee.business_owner_id == BusinessOwnerCase1.id)
            .where(SmEmployee.business_owner_id == business_owner_id)
            .order_by(SmEmployeeRoleType.value, SmEmployee.name)
        )

        result = await session.execute(stmt)
        return result.mappings().all()  # ✅ this returns list[dict]


async def get_employee_shift_schedule(business_owner_id: int):
    async with RestaurantSessionLocal() as session:
        stmt = (
            select(
                SmEmployee.id.label("employee_id"),
                SmEmployee.name.label("employee_name"),
                SmEmployeeRoleType.value.label("role"),
                EmployeeShift.day,
                EmployeeShift.start_time,
                EmployeeShift.end_time,
                EmployeeShift.duration,
            )
            .join(EmployeeShift, SmEmployee.id == EmployeeShift.employee_id)
            .join(SmEmployeeRoleType, SmEmployee.role_type == SmEmployeeRoleType.id)
            .where(SmEmployee.business_owner_id == business_owner_id)
            .order_by(EmployeeShift.day, SmEmployeeRoleType.value, SmEmployee.name)
        )

        result = await session.execute(stmt)
        return result.mappings().all()  # returns list of dicts
    


    # In dataprovider/attendance.py
from sqlalchemy import select, and_
from app.db.models import SmEmployee, EmployeeShift, SmEmployeeRoleType
from app.db.session import RestaurantSessionLocal

async def get_attendance_tracker(business_owner_id: int):
    async with RestaurantSessionLocal() as session:
        stmt = (
            select(
                SmEmployee.id.label("employee_id"),
                SmEmployee.name.label("employee_name"),
                SmEmployeeRoleType.value.label("role"),
                EmployeeShift.day,
                EmployeeShift.start_time,
                EmployeeShift.end_time,
                SmEmployee.on_leave,
                SmEmployee.terminated,
                SmEmployee.active
            )
            .join(EmployeeShift, SmEmployee.id == EmployeeShift.employee_id)
            .join(SmEmployeeRoleType, SmEmployee.role_type == SmEmployeeRoleType.id)
            .where(SmEmployee.business_owner_id == business_owner_id)
            .order_by(EmployeeShift.day, SmEmployeeRoleType.value)
        )

        result = await session.execute(stmt)
        rows = result.mappings().all()

        attendance_data = []

        for row in rows:
            status = "Present"
            if row["terminated"]:
                status = "Terminated"
            elif row["on_leave"]:
                status = "On Leave"
            elif not row["active"]:
                status = "Absent"

            attendance_data.append({
                "employee_id": row["employee_id"],
                "employee_name": row["employee_name"],
                "role": row["role"],
                "day": row["day"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "status": status,
            })

        return attendance_data


async def get_payroll_summary(business_owner_id: int):
    async with RestaurantSessionLocal() as session:
        stmt = (
            select(
                SmEmployee.id.label("employee_id"),
                SmEmployee.name.label("employee_name"),
                SmEmployeeRoleType.value.label("role"),
                SmEmployee.salary.label("base_salary"),
                func.coalesce(func.sum(cast(EmployeeBenefits.amount, Numeric)), 0).label("total_benefits"),
            )
            .join(SmEmployeeRoleType, SmEmployee.role_type == SmEmployeeRoleType.id)
            .outerjoin(EmployeeBenefits, EmployeeBenefits.employee_id == SmEmployee.id)
            .where(SmEmployee.business_owner_id == business_owner_id)
            .group_by(
                SmEmployee.id,
                SmEmployee.name,
                SmEmployeeRoleType.value,
                SmEmployee.salary
            )
            .order_by(SmEmployee.name)
        )

        result = await session.execute(stmt)
        return [dict(row._mapping) for row in result.fetchall()]