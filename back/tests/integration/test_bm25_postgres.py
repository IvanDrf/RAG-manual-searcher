from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from scripts import benchmark_rag
from scripts.benchmark_rag import Fragment, load_fragments
from scripts.data.data_migration import import_book
from src.domain.models.postgresql import BookORM, ChunkORM
from src.infrastructure.repository.postgresql.bm25_repo import rank_chunks, rebuild_index

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def normalize_benchmark_fragments(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(benchmark_rag, "normalize_text", str.casefold)


async def test_persisted_rankings_and_temporary_tables(pg_session: AsyncSession) -> None:
    session = pg_session
    before = await session.scalar(text("SELECT count(*) FROM public.chunks"))
    temporary_tables = await session.begin_nested()
    try:
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
    finally:
        await temporary_tables.rollback()

    assert await session.scalar(text("SELECT to_regclass('pg_temp.chunks')")) is None
    assert await session.scalar(text("SELECT count(*) FROM public.chunks")) == before


async def test_import_preserves_legacy_chunk_ids(pg_session: AsyncSession) -> None:
    session = pg_session
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
    assert found is not None
    assert ambiguous is not None
    assert found.source_text == "Текст один"
    assert ambiguous.source_text is None
    assert await session.scalar(text("SELECT count(*) FROM chunks")) == 2
