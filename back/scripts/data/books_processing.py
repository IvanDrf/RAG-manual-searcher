from asyncio import get_running_loop
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from re import MULTILINE, sub
from typing import overload
from uuid import UUID, uuid4

from fastapi import UploadFile
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from pdfplumber import open as pdf_open
from pdfplumber.pdf import PDF
from pymorphy3 import MorphAnalyzer

from src.domain.models import BookORM, ChunkORM


@overload
async def process_book(book: UploadFile) -> tuple[BookORM, list[ChunkORM]]:
    pass


@overload
async def process_book(book: Path) -> tuple[BookORM, list[ChunkORM]]:
    pass


async def process_book(book: Path | UploadFile) -> tuple[BookORM, list[ChunkORM]]:
    """Обрабатывание книги в модели: BookORM, ChunkORM"""

    if isinstance(book, Path):
        return await process_book_by_filepath(book)

    return await process_book_by_upload_file(book)


_POOL = ProcessPoolExecutor(max_workers=6)


async def process_book_by_upload_file(book: UploadFile) -> tuple[BookORM, list[ChunkORM]]:
    """Обработка книги, которая пришла из вне, FastAPI"""

    title = book.filename
    if not title:
        raise ValueError("book name is empty")

    content = await book.read()
    loop = get_running_loop()
    return await loop.run_in_executor(_POOL, _parse_book, content, title)


async def process_book_by_filepath(book: Path) -> tuple[BookORM, list[ChunkORM]]:
    """Обработка книги как файла, хранится на сервере"""

    if not book.is_file():
        raise ValueError("book is a dir, not a file")

    title = book.name
    loop = get_running_loop()
    return await loop.run_in_executor(_POOL, _parse_book, book, title)


def _parse_book(book: bytes | Path, title: str) -> tuple[BookORM, list[ChunkORM]]:
    """Парсим книгу на чанки"""

    content = book if isinstance(book, Path) else BytesIO(book)

    with pdf_open(content) as pdf_book:
        bookModel = BookORM(book_id=uuid4(), book_title=title)
        chunks = create_chunks_from_book(pdf_book, bookModel.book_id)

    return bookModel, chunks


_STOPWORDS_RUSSIAN = set(stopwords.words("russian"))


def create_chunks_from_book(book: PDF, book_id: UUID) -> list[ChunkORM]:
    """Создаем чанки из книги, с токенезацией и нормализацией"""

    book_text = (clean_text(page.extract_text()) for page in book.pages)

    chunks: list[ChunkORM] = []

    for text in book_text:
        if not text:
            continue

        text = text.casefold()

        tokens = word_tokenize(text, language="russian")
        cleaned_chunk = [word for word in tokens if word.isalpha() and word not in _STOPWORDS_RUSSIAN]

        for i, word in enumerate(cleaned_chunk):
            cleaned_chunk[i] = normalize_word(word)

        chunks.append(ChunkORM(chunk_id=uuid4(), book_id=book_id, content=" ".join(cleaned_chunk)))

    return chunks


_MORPH = MorphAnalyzer()


@lru_cache(maxsize=20_000)
def normalize_word(word: str) -> str:
    return _MORPH.parse(word)[0].normal_form


def clean_text(text: str) -> str:
    """Очистка текста от мусора"""

    text = sub(r"^.*[À-ÿ].*$\n?", "", text, flags=MULTILINE)
    text = sub(r"\(cid:\d+\)", "", text)

    return text
