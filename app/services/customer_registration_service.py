# app/services/customer_registration_service.py
import re
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.db.session import VendorSessionLocal
from app.db.vendors_models import VdCustomer, VdTemporaryCustomer

def _normalize_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    return re.sub(r"\D+", "", phone) or None

def _phone_filter(column, phone_digits: str):
    return func.regexp_replace(column, r"[^0-9]", "", "g") == phone_digits

def _split_full_name(full_name: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if not full_name or not full_name.strip():
        return None, None
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0], None
    return " ".join(parts[:-1]), parts[-1]

async def register_customer_for_order(
    phone: str,
    *,
    business_name: str | None = None,
    full_name: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    service_required: str | None = None,
    notes: str | None = None,
    source_channel: str | None = "phone-call",
) -> dict:
    # — validation
    missing = []
    phone_digits = _normalize_phone(phone)
    if not phone_digits:
        missing.append("phone")
    if not business_name or not business_name.strip():
        missing.append("business_name")
    if (not full_name or not full_name.strip()) and (not first_name or not first_name.strip()):
        missing.append("full_name_or_first_name")
    if missing:
        return {"ready": False, "missing": missing}

    # derive names if only full_name provided
    if (first_name is None or not first_name.strip()) and full_name:
        f, l = _split_full_name(full_name)
        first_name = first_name or f
        last_name = last_name or l

    # stash business_name into notes (schema doesn’t have column)
    composed_notes = (notes or "").strip()
    composed_notes = f"[business_name={business_name.strip()}] {composed_notes}".strip()

    async with VendorSessionLocal() as session:
        # 1) permanent customers
        stmt = select(VdCustomer).where(_phone_filter(VdCustomer.phone, phone_digits)).limit(1)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            return {
                "ready": True,
                "created": False,
                "source": "vendors.customers",
                "customer": {
                    "customer_id": existing.customer_id,
                    "first_name": existing.first_name,
                    "last_name": existing.last_name,
                    "email": existing.email,
                    "phone": existing.phone,
                    "business_name": business_name,
                },
            }

        # 2) temporary customers
        stmt = select(VdTemporaryCustomer).where(_phone_filter(VdTemporaryCustomer.phone, phone_digits)).limit(1)
        tmp = (await session.execute(stmt)).scalar_one_or_none()
        if tmp:
            return {
                "ready": True,
                "created": False,
                "source": "vendors.temporary_customers",
                "customer": {
                    "customer_id": tmp.temp_customer_id,
                    "first_name": tmp.first_name,
                    "last_name": tmp.last_name,
                    "email": tmp.email,
                    "phone": tmp.phone,
                    "service_required": tmp.service_required,
                    "notes": tmp.notes,
                    "business_name": business_name,
                },
            }

        # 3) insert new temp customer
        rec = VdTemporaryCustomer(
            first_name=(first_name.strip() if first_name else None),
            last_name=(last_name.strip() if last_name else None),
            email=(email.strip().lower() if email else None),
            phone=phone,
            service_required=(service_required.strip() if service_required else None),
            source_channel=(source_channel.strip() if source_channel else None),
            notes=composed_notes,
        )
        session.add(rec)
        try:
            await session.commit()
            await session.refresh(rec)
        except IntegrityError as e:
            await session.rollback()
            return {"error": "Failed to insert customer", "detail": str(e)}

        return {
            "ready": True,
            "created": True,
            "source": "vendors.temporary_customers",
            "customer": {
                "customer_id": rec.temp_customer_id,
                "first_name": rec.first_name,
                "last_name": rec.last_name,
                "email": rec.email,
                "phone": rec.phone,
                "service_required": rec.service_required,
                "notes": rec.notes,
                "business_name": business_name,
            },
        }
