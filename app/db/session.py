# app/db/session.py

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# --- Synchronous engine/session (for background scripts like pipelines) ---
from sqlalchemy import create_engine

# Make sure we use psycopg2 (sync driver) instead of asyncpg
if settings.DATABASE_URL.startswith("postgresql+asyncpg"):
    sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")
else:
    sync_url = settings.DATABASE_URL

sync_engine = create_engine(sync_url, echo=False, future=True)
SessionLocal = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)


# -----------------------------
# Engine for Main DB (Vendor / AI / Inventory)
# -----------------------------
main_engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
MainSessionLocal = sessionmaker(
    bind=main_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# -----------------------------
# Engine for Restaurant DB (Business Owner / Restaurant)
# -----------------------------
restaurant_engine = create_async_engine(settings.RESTAURANT_DATABASE_URL, echo=False, future=True)
RestaurantSessionLocal = sessionmaker(
    bind=restaurant_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# -----------------------------
# Engine for Vendors DB (NEW)
# -----------------------------
vendor_engine = create_async_engine(settings.VENDOR_DATABASE_URL, echo=False, future=True)
VendorSessionLocal = sessionmaker(
    bind=vendor_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# -----------------------------
# Dependency utilities (for FastAPI if needed)
# -----------------------------
async def get_main_db():
    async with MainSessionLocal() as session:
        yield session

async def get_restaurant_db():
    async with RestaurantSessionLocal() as session:
        yield session

async def get_vendor_db():  # NEW: vendors database dependency
    async with VendorSessionLocal() as session:
        yield session


# -----------------------------
# MongoDB connection
# -----------------------------
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB_NAME", "Vendor-Database")

_client = MongoClient(MONGO_URI)
_db = _client[MONGO_DB]


def get_collection(name: str):
    """Return a MongoDB collection handle by name."""
    return _db[name]


def ping():
    """Simple ping to test connection."""
    try:
        _client.admin.command("ping")
        print("✅ MongoDB connection successful")
    except Exception as e:
        print("❌ MongoDB connection failed:", e)
