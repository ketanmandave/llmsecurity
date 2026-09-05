"""Database engine and transaction-scoped session helpers."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings


settings = get_settings()
# Psycopg is retained for synchronous Alembic migrations. asyncpg is used by
# FastAPI because it supports Windows' default Proactor event loop.
async_database_url = settings.database_url.replace(
    "postgresql+psycopg://", "postgresql+asyncpg://", 1
)

engine = create_async_engine(
    async_database_url,
    pool_pre_ping=True,
)
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Provide an API request with a session and atomic transaction."""

    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
