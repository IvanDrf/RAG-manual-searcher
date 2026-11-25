"""Импорт книг и обновление BM25 в одной транзакции."""

from argparse import ArgumentParser
from asyncio import Semaphore, as_completed, run
from collections import Counter
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.data.books_processing import process_book
from src.core.config import CONFIG
from src.domain.models.postgresql import BookORM, ChunkORM
from src.infrastructure.repository.postgresql.bm25_repo import (
    lock_index_for_update,
    rebuild_index,
)
from src.infrastructure.repository.postgresql.connection import connect_to_postgresql


async def import_book(
    session: AsyncSession,
    book: BookORM,
    chunks: list[ChunkORM],
) -> None:
    """Добавить новую книгу или восстановить исходники однозначных страниц."""
    existing_books = (await session.scalars(select(BookORM).where(BookORM.book_title == book.book_title))).all()
    if not existing_books:
        session.add(book)
        await session.flush()
        session.add_all(chunks)
        return

    if len(existing_books) > 1:
        print(f"{book.book_title}: несколько книг с таким названием, пропущено")
        return

    existing_chunks = (await session.scalars(select(ChunkORM).where(ChunkORM.book_id == existing_books[0].book_id))).all()
    incoming_counts = Counter(chunk.content for chunk in chunks)
    existing_counts = Counter(chunk.content for chunk in existing_chunks)
    sources = {chunk.content: chunk.source_text for chunk in chunks}

    restored = 0
    unresolved = 0
    for chunk in existing_chunks:
        if chunk.source_text is not None:
            continue

        if incoming_counts[chunk.content] == existing_counts[chunk.content] == 1:
            chunk.source_text = sources[chunk.content]
            restored += 1
        else:
            unresolved += 1

    print(f"{book.book_title}: восстановлено {restored}, без совпадения {unresolved}")


async def migrate_books(books_path: Path) -> None:
    """Обработать PDF и опубликовать индекс одновременно с импортом."""
    paths = sorted(books_path.glob(f"*{CONFIG.books_ext}"))
    paths = [path for path in paths if path.is_file()]
    if not paths:
        raise ValueError(f"В {books_path} нет файлов {CONFIG.books_ext}")

    semaphore = Semaphore(12)

    async def process_one(path: Path) -> tuple[BookORM, list[ChunkORM]]:
        async with semaphore:
            return await process_book(path)

    engine, session_maker = connect_to_postgresql(CONFIG)
    try:
        async with session_maker.begin() as session:
            await lock_index_for_update(session)
            for book_number, task in enumerate(as_completed(process_one(path) for path in paths), start=1):
                book, chunks = await task
                await import_book(session, book, chunks)
                print(f"[{book_number}/{len(paths)}] {book.book_title}")

            count = await rebuild_index(session)
        print(f"BM25: проиндексировано {count} фрагментов")
    finally:
        await engine.dispose()


async def rebuild_books_index() -> None:
    """Перестроить индекс по существующим чанкам с исходниками."""
    engine, session_maker = connect_to_postgresql(CONFIG)
    try:
        async with session_maker.begin() as session:
            count = await rebuild_index(session)
        print(f"BM25: проиндексировано {count} фрагментов")
    finally:
        await engine.dispose()


def main() -> None:
    """Запустить импорт или перестроение индекса."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--books-dir", type=Path, default=CONFIG.books_dir)
    parser.add_argument("--reindex", action="store_true")
    args = parser.parse_args()

    if args.reindex:
        run(rebuild_books_index())
    else:
        run(migrate_books(args.books_dir))


if __name__ == "__main__":
    main()
