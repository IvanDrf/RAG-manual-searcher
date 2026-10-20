from collections.abc import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.postgresql import BookORM, ChunkORM


async def add_books(session: AsyncSession, books: list[BookORM]) -> None:
    session.add_all(books)


async def get_all_chunks(session: AsyncSession) -> AsyncGenerator[ChunkORM, None]:
    query = select(ChunkORM).order_by(ChunkORM.chunk_id)

    result = await session.stream_scalars(query)
    try:
        async for row in result:
            yield row
    finally:
        await result.close()
