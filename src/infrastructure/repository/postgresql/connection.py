from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import PostgreSQLConfig
from src.infrastructure.repository.postgresql.utils import execute_once


@execute_once
async def connect_to_postgresql(config: PostgreSQLConfig) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(url=config.postgres_dsn)

    session_maker: async_sessionmaker[AsyncSession] = async_sessionmaker(engine)
    await ping_database(session_maker)
    return engine, session_maker


async def ping_database(session_maker: async_sessionmaker[AsyncSession]) -> None:
    async with session_maker() as session:
        await session.execute(text("SELECT 1"))
