"""Интеграция BM25 с PostgreSQL и проверка изоляции бенчмарка."""

from asyncio import run
from os import getenv
from uuid import UUID

import pytest
from sqlalchemy import text

from scripts.benchmark_rag import Fragment, load_fragments
from scripts.data.data_migration import import_book
from src.core.config import CONFIG
from src.domain.models import BookORM, ChunkORM
from src.infrastructure.repository.postgresql.bm25_repo import rank_chunks, rebuild_index
from src.infrastructure.repository.postgresql.connection import connect_to_postgresql

pytestmark = pytest.mark.skipif(
    getenv("RUN_POSTGRES_TESTS") != "1",
    reason="requires PostgreSQL with the BM25 migration applied",
)


def test_persisted_rankings_and_temporary_tables() -> None:
    """Скоринг суммирует разные блоки и сохраняет порядок при равных баллах."""
    run(_check_rankings())


async def _check_rankings() -> None:
    engine, sessions = connect_to_postgresql(CONFIG)
    try:
        async with sessions.begin() as session:
            before = await session.scalar(text("SELECT count(*) FROM public.chunks"))
            fragments = [Fragment(id=f"D0{number}", book="test", page=number, text="Текст") for number in range(1, 4)]
            await load_fragments(session, fragments)
            corpus = " ".join(f"term{number:04d}" for number in range(1001))
            await session.execute(
                text("UPDATE chunks SET content = :corpus WHERE chunk_id <> :other"),
                {"corpus": corpus, "other": UUID(int=3)},
            )
            await session.execute(text("UPDATE chunks SET source_text = NULL WHERE chunk_id = :id"), {"id": UUID(int=3)})

            assert await rebuild_index(session) == 2
            assert await rebuild_index(session) == 2
            for term in ["term0000", "term1000"]:
                assert await rank_chunks(session, [term], 1)
            hits = await rank_chunks(session, ["term0000", "term1000"], 3)
            assert [hit.chunk_id.int for hit in hits] == [1, 2]
            single = await rank_chunks(session, ["term0000", "term0000"], 1)
            assert hits[0].score == pytest.approx(2 * single[0].score)
            assert not await rank_chunks(session, ["unknown"], 3)
        async with sessions.begin() as session:
            assert await session.scalar(text("SELECT to_regclass('pg_temp.chunks')")) is None
            assert await session.scalar(text("SELECT count(*) FROM public.chunks")) == before
    finally:
        await engine.dispose()


def test_import_preserves_legacy_chunk_ids() -> None:
    """Точное совпадение дополняется исходником, повторяющиеся страницы остаются без него."""
    run(_check_legacy_import())


async def _check_legacy_import() -> None:
    engine, sessions = connect_to_postgresql(CONFIG)
    try:
        async with sessions.begin() as session:
            fragment = Fragment(id="D01", book="legacy", page=1, text="Текст")
            await load_fragments(session, [fragment])
            await session.execute(text("UPDATE chunks SET source_text = NULL, content = 'лемма'"))
            session.add(ChunkORM(chunk_id=UUID(int=3), book_id=UUID(int=1), content="повтор"))
            await session.flush()

            incoming_book = BookORM(book_id=UUID(int=10), book_title="legacy")
            incoming_chunks = [
                ChunkORM(chunk_id=UUID(int=11), content="лемма", source_text="Текст один"),
                ChunkORM(chunk_id=UUID(int=12), content="повтор", source_text="Текст два"),
                ChunkORM(chunk_id=UUID(int=13), content="повтор", source_text="Текст три"),
            ]
            await import_book(session, incoming_book, incoming_chunks)
            await import_book(session, incoming_book, incoming_chunks)

            found = await session.get(ChunkORM, UUID(int=1))
            ambiguous = await session.get(ChunkORM, UUID(int=3))
            assert found.source_text == "Текст один"
            assert ambiguous.source_text is None
            assert await session.scalar(text("SELECT count(*) FROM chunks")) == 2
    finally:
        await engine.dispose()
