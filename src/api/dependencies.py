from collections.abc import AsyncGenerator
from typing import Protocol

from infrastructure.repository.postgresql.connection import connect_to_postgresql
from src.core.config import CONFIG

engine, session_maker = connect_to_postgresql(CONFIG)


class ISession(Protocol):
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


async def get_session() -> AsyncGenerator[ISession, None]:
    async with session_maker() as session:
        yield session
