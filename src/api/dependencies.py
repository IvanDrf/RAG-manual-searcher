from collections.abc import AsyncGenerator
from typing import Protocol

from httpx import AsyncClient
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


async def close_dependencies() -> None:
    await engine.dispose()


async def get_http_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(timeout=CONFIG.llm_timeout) as client:
        yield client


async def get_llm_api_key() -> str:
    return CONFIG.llm_api_key


async def get_llm_url() -> str:
    return CONFIG.llm_url
