import asyncio
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.core.config import settings

# Create async engine for SQLModel
engine = create_async_engine(
    settings.database_url,
    echo=True,
    future=True
)

# Create async session maker
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def create_db_tables() -> None:
    """
    Create all database tables defined in SQLModel models.

    WARNING: This is primarily for testing and development.
    In production, use Alembic migrations instead.

    Usage:
        import asyncio
        asyncio.run(create_db_tables())
    """
    # Import all models to ensure they're registered with SQLModel metadata
    import src.db.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def drop_db_tables() -> None:
    """
    Drop all database tables.

    WARNING: This will delete all data. Use with extreme caution.
    Only for testing/development.
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


def init_db() -> None:
    """
    Synchronous wrapper for creating database tables.

    WARNING: For development only. Use Alembic migrations in production.

    Usage:
        python -m src.db.database
    """
    asyncio.run(create_db_tables())


if __name__ == "__main__":
    print("Creating database tables...")
    init_db()
    print("Database tables created successfully!")