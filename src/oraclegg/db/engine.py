from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from oraclegg.config import settings

engine = create_async_engine(settings.db_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Create all tables. Uses SQLAlchemy metadata for simplicity (no Alembic for MVP)."""
    from oraclegg.db.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    """FastAPI dependency for DB sessions."""
    async with async_session() as session:
        yield session
