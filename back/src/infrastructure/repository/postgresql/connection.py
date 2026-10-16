from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import PostgreSQLConfig


def connect_to_postgresql(config: PostgreSQLConfig) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(url=config.postgres_dsn)

    session_maker: async_sessionmaker[AsyncSession] = async_sessionmaker(engine)
    return engine, session_maker
