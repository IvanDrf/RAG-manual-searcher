from collections.abc import AsyncGenerator
from typing import Protocol

from sqlalchemy import text

from src.core.config import CONFIG
from src.infrastructure.repository.postgresql.connection import connect_to_postgresql

engine, session_maker = connect_to_postgresql(CONFIG)


class ISession(Protocol):
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


async def get_session() -> AsyncGenerator[ISession, None]:
    async with session_maker() as session:
        yield session


async def ping_database() -> None:
    async with session_maker() as session:
        await session.execute(text("SELECT 1"))
