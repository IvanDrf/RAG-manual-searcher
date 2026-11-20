from asyncio import Semaphore, as_completed, run
from pathlib import Path

from scripts.data.books_processing import process_book
from src.core.config import CONFIG
from src.domain.models import BookORM, ChunkORM
from src.infrastructure.repository.postgresql.connection import connect_to_postgresql


async def migrate_books(books_path: Path) -> None:
    books = (p for p in books_path.iterdir() if p.is_file() and p.suffix.lower() == CONFIG.books_ext)

    sem = Semaphore(12)

    async def process_one(book: Path) -> tuple[BookORM, list[ChunkORM]]:
        async with sem:
            return await process_book(book)

    tasks = [process_one(book) for book in books]
    engine, session_maker = connect_to_postgresql(CONFIG)
    done = 1
    async with session_maker() as session:
        for coro in as_completed(tasks):
            book, chunks = await coro
            session.add(book)
            session.add_all(chunks)

            await session.flush()

            print(f"Done: {(done / len(tasks) * 100):.2f}%")
            done += 1

        await session.commit()

    await engine.dispose()


if __name__ == "__main__":
    run(migrate_books(CONFIG.books_dir))
