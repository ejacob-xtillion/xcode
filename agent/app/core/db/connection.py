from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
from app.core.db.models import Base
from app.core.settings import get_settings

settings = get_settings()

# Make database optional - only create engine if DATABASE_URL is configured
engine = None
async_session_maker = None

if settings.async_database_url:
    engine = create_async_engine(
        settings.async_database_url,
        pool_size=20,
        max_overflow=20,
        pool_timeout=60,
        pool_recycle=1800,
    )

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


@asynccontextmanager
async def get_session() -> AsyncGenerator[Optional[AsyncSession], None]:
    """Get database session if database is configured, otherwise yield None"""
    if async_session_maker is None:
        # No database configured - yield None
        yield None
    else:
        async with async_session_maker() as db_session:
            try:
                yield db_session
                await db_session.commit()
            except:
                await db_session.rollback()
                raise
