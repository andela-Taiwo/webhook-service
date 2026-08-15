from typing import AsyncGenerator
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.database import async_session


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session."""
    async with async_session() as session:
        yield session