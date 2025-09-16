# app/core/mongo.py
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None

def get_mongo_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client

def get_mongo_db() -> AsyncIOMotorDatabase:
    global _db
    if _db is None:
        _db = get_mongo_client()[settings.MONGO_DB]
    return _db

async def close_mongo():
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None
