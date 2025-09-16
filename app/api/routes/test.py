from fastapi import APIRouter
from app.core.mongo import get_mongo_db

router = APIRouter()

@router.get("/test-mongo")
async def test_mongo():
    db = get_mongo_db()
    try:
        await db.command("ping")
        return {"status": "success", "message": "Pinged your MongoDB deployment successfully!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
