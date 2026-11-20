"""Извлечение исходных страниц и подготовка поискового текста."""

from asyncio import get_running_loop
from concurrent.futures import ProcessPoolExecutor
from io import BytesIO
from pathlib import Path
from re import MULTILINE, sub
from uuid import UUID, uuid4

from fastapi import UploadFile
from pdfplumber import open as pdf_open
from pdfplumber.pdf import PDF

from src.domain.models import BookORM, ChunkORM
from src.infrastructure.rag.normalization import normalize_text

_POOL = ProcessPoolExecutor(max_workers=6)


async def process_book(book: Path | UploadFile) -> tuple[BookORM, list[ChunkORM]]:
    """Извлечь страницы локального или загруженного PDF."""
    if isinstance(book, Path):
        return await process_book_by_filepath(book)

    return await process_book_by_upload_file(book)


async def process_book_by_upload_file(book: UploadFile) -> tuple[BookORM, list[ChunkORM]]:
    """Извлечь страницы загруженной книги."""
    title = book.filename
    if not title:
        raise ValueError("book name is empty")

    content = await book.read()
    loop = get_running_loop()
    return await loop.run_in_executor(_POOL, _parse_book, content, title)


async def process_book_by_filepath(book: Path) -> tuple[BookORM, list[ChunkORM]]:
    """Извлечь страницы из локального PDF."""
    if not book.is_file():
        raise ValueError("book is not a file")

    loop = get_running_loop()
    return await loop.run_in_executor(_POOL, _parse_book, book, book.name)


def _parse_book(book: bytes | Path, title: str) -> tuple[BookORM, list[ChunkORM]]:
    content = book if isinstance(book, Path) else BytesIO(book)
    book_record = BookORM(book_id=uuid4(), book_title=title)

    with pdf_open(content) as pdf_book:
        chunks = create_chunks_from_book(pdf_book, book_record.book_id)

    return book_record, chunks


def create_chunks_from_book(book: PDF, book_id: UUID) -> list[ChunkORM]:
    """Сохранить извлечённую страницу и поисковый текст отдельно."""
    chunks: list[ChunkORM] = []
    for page in book.pages:
        source_text = page.extract_text() or ""
        searchable_text = clean_text(source_text)
        if not searchable_text.strip():
            continue

        chunks.append(
            ChunkORM(
                chunk_id=uuid4(),
                book_id=book_id,
                content=normalize_text(searchable_text),
                source_text=source_text.strip(),
            )
        )

    return chunks


def clean_text(text: str) -> str:
    """Убрать артефакты PDF так же, как при старом импорте лемм."""
    text = sub(r"^.*[À-ÿ].*$\n?", "", text, flags=MULTILINE)
    return sub(r"\(cid:\d+\)", "", text)
