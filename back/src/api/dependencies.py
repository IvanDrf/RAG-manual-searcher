from asyncio import gather
from collections.abc import AsyncGenerator
from typing import Protocol

from async_lru import alru_cache
from clickhouse_connect.driver.asyncclient import AsyncClient as AsyncClickHouse
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy import text

from src.core.config import CONFIG
from src.core.exc import InternalError
from src.infrastructure.analytics.llm_response import IStatisticsRepo, LLMStatisticsScraper
from src.infrastructure.repository.clickhouse.connection import connect_to_clickhouse
from src.infrastructure.repository.clickhouse.llm_statistics import LLMStatisticsRepo
from src.infrastructure.repository.postgresql.connection import connect_to_postgresql
from src.infrastructure.repository.redis.connection import connect_to_redis

engine, session_maker = connect_to_postgresql(CONFIG)
redis = connect_to_redis(CONFIG)


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
    await redis.aclose()

    clickhouse = await get_clickhouse()
    await clickhouse.close()


async def get_http_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(timeout=CONFIG.llm_timeout) as client:
        yield client


def get_llm_api_key() -> str:
    return CONFIG.llm_api_key


def get_llm_url() -> str:
    return CONFIG.llm_url


def get_redis() -> Redis:
    return redis


@alru_cache(maxsize=1)
async def get_clickhouse() -> AsyncClickHouse:
    return await connect_to_clickhouse(CONFIG)


@alru_cache(maxsize=1)
async def get_llm_statistics_repo(client: AsyncClickHouse) -> IStatisticsRepo:
    return LLMStatisticsRepo(client)


@alru_cache(maxsize=1)
async def get_llm_scraper() -> LLMStatisticsScraper:
    statistics_repo = await get_llm_statistics_repo(await get_clickhouse())
    return LLMStatisticsScraper(batch_size=CONFIG.app_statistics_batch_size, statistics_repo=statistics_repo)


async def check_health() -> tuple[BaseException | None, ...]:
    async def ping_postgresql() -> None:
        try:
            async with session_maker() as session:
                await session.execute(text("SELECT 1"))
        except ConnectionRefusedError:
            raise InternalError("postgresql is not available")

    async def ping_redis() -> None:
        if not await redis.ping():
            raise InternalError("redis is not available")

    async def ping_clickhouse() -> None:
        clickhouse = await get_clickhouse()
        if not await clickhouse.ping():
            raise InternalError("statistic database is not available")

    return await gather(*[ping_postgresql(), ping_redis(), ping_clickhouse()], return_exceptions=True)
