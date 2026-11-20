"""Подключения к внешним сервисам для маршрутов FastAPI."""

from asyncio import gather
from collections.abc import AsyncGenerator
from typing import Protocol

from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy import text

from src.core.config import CONFIG, LLMConfig
from src.infrastructure.repository.postgresql.connection import connect_to_postgresql
from src.infrastructure.repository.redis.connection import connect_to_redis

engine, session_maker = connect_to_postgresql(CONFIG)
redis = connect_to_redis(CONFIG)


class ISession(Protocol):
    """Минимальные операции асинхронной транзакции."""

    async def commit(self) -> None:
        """Подтвердить транзакцию."""

    async def rollback(self) -> None:
        """Отменить транзакцию."""


async def get_session() -> AsyncGenerator[ISession, None]:
    """Выдать сессию PostgreSQL на время запроса."""
    async with session_maker() as session:
        yield session


async def ping_database() -> None:
    """Проверить доступ к PostgreSQL."""
    async with session_maker() as session:
        await session.execute(text("SELECT 1"))


async def close_dependencies() -> None:
    """Закрыть пул PostgreSQL и подключение Redis."""
    await engine.dispose()
    await redis.aclose()


async def get_http_client() -> AsyncGenerator[AsyncClient, None]:
    """Выдать HTTP-клиент с таймаутом модели."""
    async with AsyncClient(timeout=CONFIG.llm_timeout) as client:
        yield client


async def get_llm_settings() -> LLMConfig:
    """Передать конфигурацию модели обработчикам чата."""
    return CONFIG


async def get_redis() -> Redis:
    """Вернуть клиент Redis для проверки доступа."""
    return redis


async def check_health() -> None:
    """Проверить PostgreSQL и Redis параллельно."""

    async def ping_postgresql() -> None:
        async with session_maker() as session:
            await session.execute(text("SELECT 1"))

    async def ping_redis() -> None:
        await redis.ping()

    await gather(*[ping_postgresql(), ping_redis()])
