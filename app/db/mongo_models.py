"""
models.py
----------
Pydantic models and helper for inserting docs into MongoDB.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field
from app.db.session import get_collection, ping


class BaseDoc(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_mongo(self) -> Dict[str, Any]:
        data = self.model_dump()
        for k, v in list(data.items()):
            if isinstance(v, datetime) and v.tzinfo is None:
                data[k] = v.replace(tzinfo=timezone.utc)
        return data


class OrderDraft(BaseDoc):
    """Schema for the Order Drafts collection."""
    customer_id: str
    phone_number: Optional[str] = None
    items: Dict[str, int] = Field(default_factory=dict)
    notes: Optional[str] = None
    status: str = Field(default="draft")  # draft | confirmed | rejected


class CallLog(BaseDoc):
    """Schema for the Call-Logs collection."""
    phone_number: str
    customer_id: Optional[str] = None
    transcript: Optional[str] = None
    duration_sec: Optional[int] = None


def post_doc(collection_name: str, doc: Union[BaseModel, Dict[str, Any]]) -> str:
    """
    Insert a document into the given collection.
    Returns the inserted_id as a string.
    """
    ping()

    if isinstance(doc, BaseModel):
        payload = doc.to_mongo() if hasattr(doc, "to_mongo") else doc.model_dump()
        payload["updated_at"] = payload.get("created_at", datetime.now(timezone.utc))
    elif isinstance(doc, dict):
        payload = doc.copy()
        now = datetime.now(timezone.utc)
        payload.setdefault("created_at", now)
        payload.setdefault("updated_at", now)
    else:
        raise TypeError("doc must be a dict or a Pydantic BaseModel")

    col = get_collection(collection_name)
    result = col.insert_one(payload)
    return str(result.inserted_id)