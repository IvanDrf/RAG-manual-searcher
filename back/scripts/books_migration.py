from asyncio import run
from uuid import uuid4

from src.core.config import CONFIG
from src.domain.models import BookORM
from src.infrastructure.repository.postgresql.chunk_repo import add_books
from src.infrastructure.repository.postgresql.connection import connect_to_postgresql


async def add_books_to_database() -> None:
    titles = []  # названия учебников

    books = [BookORM(book_id=uuid4(), book_title=title) for title in titles]

    engine, session_maker = connect_to_postgresql(CONFIG)
    async with session_maker() as session:
        await add_books(session, books)
        await session.commit()

    await engine.dispose()


if __name__ == "__main__":
    run(add_books_to_database())
