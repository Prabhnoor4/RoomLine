from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app import config

engine = create_async_engine(f"sqlite+aiosqlite:///{config.DB_PATH}")


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session():
    async with AsyncSession(engine) as session:
        yield session
