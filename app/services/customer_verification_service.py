# app/services/customer_verification_service.py

import re
from typing import Optional
from sqlalchemy import select, func

# Use the VendorSessionLocal from your app/db/session.py (singular)
from app.db.session import VendorSessionLocal
from app.db.vendors_models import VdCustomer, VdTemporaryCustomer


def _normalize_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    digits = re.sub(r"\D+", "", phone)
    return digits or None

def _phone_filter(column, phone_digits: str):
    # Compare digits-only version of the column with the normalized phone
    return func.regexp_replace(column, r"[^0-9]", "", "g") == phone_digits


async def verify_customer_by_phone(phone: str) -> dict:
    """
    Look up a customer by phone number ONLY in the Vendors database.
    Checks vendors.customers first, then vendors.temporary_customers.
    Returns first match; otherwise {"found": False, "message": "no information"}.
    """
    phone_digits = _normalize_phone(phone)
    if not phone_digits:
        return {"error": "Invalid phone number format"}

    async with VendorSessionLocal() as v_sess:
        # 1) vendors.customers
        stmt = select(VdCustomer).where(_phone_filter(VdCustomer.phone, phone_digits)).limit(1)
        match = (await v_sess.execute(stmt)).scalar_one_or_none()
        if match:
            return {
                "found": True,
                "source": "vendors.customers",
                "customer_id": match.customer_id,
                "first_name": match.first_name,
                "last_name": match.last_name,
                "email": match.email,
                "phone": match.phone,
            }

        # 2) vendors.temporary_customers
        stmt = select(VdTemporaryCustomer).where(_phone_filter(VdTemporaryCustomer.phone, phone_digits)).limit(1)
        match = (await v_sess.execute(stmt)).scalar_one_or_none()
        if match:
            return {
                "found": True,
                "source": "vendors.temporary_customers",
                "customer_id": match.temp_customer_id,
                "first_name": match.first_name,
                "last_name": match.last_name,
                "email": match.email,
                "phone": match.phone,
            }

    return {"found": False, "message": "no information"}
