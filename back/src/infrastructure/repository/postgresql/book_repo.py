from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import BookORM


async def find_books(session: AsyncSession, *, limit: int, offset: int) -> list[BookORM]:
    query = select(BookORM).order_by(BookORM.book_title, BookORM.book_id).limit(limit).offset(offset)

    res = await session.execute(query)
    return list(res.scalars().all())
