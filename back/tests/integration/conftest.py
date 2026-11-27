from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.domain.models.postgresql import BaseORM


@pytest.fixture
async def pg_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("postgresql+asyncpg://rag_test:rag_test@127.0.0.1:25432/rag_test")
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                await connection.run_sync(BaseORM.metadata.create_all)
                async with AsyncSession(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False) as session:
                    yield session
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
