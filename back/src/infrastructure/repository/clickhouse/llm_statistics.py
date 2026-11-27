from clickhouse_connect.driver.asyncclient import AsyncClient
from clickhouse_connect.driver.exceptions import DatabaseError, InterfaceError
from loguru import logger

from src.core.exc import InternalError
from src.domain.models.clickhouse import LLMResponseORM


class LLMStatisticsRepo:
    def __init__(self, client: AsyncClient) -> None:
        self.__client = client

    async def add_llm_statistics(self, llm_statistics: list[LLMResponseORM]) -> None:
        if not llm_statistics:
            raise InternalError("insert empty values in clickhouse, llm_statistics")

        tablename = llm_statistics[0].__tablename__

        columns = [col.name for col in LLMResponseORM.__table__.columns]
        data = [[getattr(r, col) for col in columns] for r in llm_statistics]
        try:
            await self.__client.insert(table=tablename, data=data, column_names=columns)
        except (DatabaseError, InterfaceError) as e:
            logger.critical("can't insert data in clickhouse", error=e)

            raise InternalError("can't insert statistics")
