from fastapi import APIRouter
from sqlalchemy import text
from app.core.logger import get_logger
from app.core.db.connection import engine
from app.core.errors.custom_errors import InternalServerError

router = APIRouter()
logger = get_logger()


@router.get("")
async def health_check():
    return {"status": "healthy"}


@router.get("/db")
async def db_health_check():
    if engine is None:
        return {"status": "not_configured", "message": "Database not configured - using in-memory storage"}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception:
        raise InternalServerError
