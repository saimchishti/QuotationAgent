from fastapi import APIRouter, Query, HTTPException
from app.services.employee_provider import (
get_employee_roster,
get_employee_shift_schedule,
get_attendance_tracker,
get_payroll_summary
)

router = APIRouter()

@router.get("/employees/roster")
async def employee_roster_viewer(
    business_owner_id: int = Query(..., description="Business Owner ID")
):
    try:
        data = await get_employee_roster(business_owner_id)  # ✅ No session passed
        return {"success": True, "data": [dict(row) for row in data]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/employees/shifts")
async def employee_shift_dashboard(
    business_owner_id: int = Query(..., description="Business Owner ID")
):
    try:
        data = await get_employee_shift_schedule(business_owner_id)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


@router.get("/employees/attendance")
async def attendance_tracker(
    business_owner_id: int = Query(..., description="Business Owner ID")
):
    try:
        data = await get_attendance_tracker(business_owner_id)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/employees/payroll-summary")
async def payroll_summary(
    business_owner_id: int = Query(..., description="Business Owner ID")
):
    try:
        data = await get_payroll_summary(business_owner_id)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))