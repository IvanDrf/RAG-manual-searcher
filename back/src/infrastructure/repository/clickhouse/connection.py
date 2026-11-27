from clickhouse_connect import get_async_client
from clickhouse_connect.driver.asyncclient import AsyncClient

from src.core.config import ClickHouseConfig


async def connect_to_clickhouse(config: ClickHouseConfig) -> AsyncClient:
    return await get_async_client(
        host=config.clickhouse_host,
        port=config.clickhouse_port,
        username=config.clickhouse_user,
        password=config.clickhouse_password,
        database=config.clickhouse_db,
    )
