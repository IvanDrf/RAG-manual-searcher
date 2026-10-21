from clickhouse_connect.driver.asyncclient import AsyncClient

from src.core.exc import InternalError
from src.domain.models.clickhouse import LLMResponseORM


async def add_llm_statistics(client: AsyncClient, llm_responses: list[LLMResponseORM]) -> None:
    if not llm_responses:
        raise InternalError("insert empty values in clickhouse, llm_statistics")

    tablename = llm_responses[0].__tablename__

    columns = [col.name for col in LLMResponseORM.__table__.columns]
    data = [[getattr(r, col) for col in columns] for r in llm_responses]

    await client.insert(table=tablename, data=data, column_names=columns)
