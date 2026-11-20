"""Хранение индекса и ранжирование чанков в PostgreSQL."""

from dataclasses import dataclass
from itertools import batched
from uuid import UUID

from pgvector import SparseVector
from sqlalchemy import Text, bindparam, delete, insert, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import BM25BlockORM, BM25TermORM
from src.infrastructure.rag.bm25 import BLOCK_SIZE, BM25
from src.infrastructure.repository.postgresql.chunk_repo import get_all_chunks

_RANK_CHUNKS = text(
    """
    WITH query_blocks AS (
        SELECT block,
               CAST('{' || string_agg(format('%s:%s', coordinate + 1, 1), ','
                                       ORDER BY coordinate)
                    || '}/' || :dimensions AS sparsevec) AS weights
        FROM bm25_terms
        WHERE term = ANY(:terms)
        GROUP BY block
    ),
    ranked AS (
        SELECT docs.chunk_id,
               sum(inner_product(docs.weights, query.weights)) AS score
        FROM bm25_blocks AS docs
        JOIN query_blocks AS query USING (block)
        GROUP BY docs.chunk_id
    )
    SELECT chunks.chunk_id, books.book_title, chunks.source_text, ranked.score
    FROM ranked
    JOIN chunks USING (chunk_id)
    JOIN books USING (book_id)
    WHERE ranked.score > 0 AND chunks.source_text IS NOT NULL
    ORDER BY ranked.score DESC, chunks.chunk_id
    LIMIT :limit
    """
).bindparams(
    bindparam("terms", type_=ARRAY(Text())),
    bindparam("dimensions", type_=Text()),
)


@dataclass(frozen=True)
class SearchHit:
    """Оценка, текст и источник найденного фрагмента."""

    chunk_id: UUID
    book_title: str
    source_text: str
    score: float


async def lock_index_for_update(session: AsyncSession) -> None:
    """Сериализовать импорт и перестроение индекса в пределах транзакции."""
    await session.execute(text("LOCK TABLE bm25_terms IN SHARE ROW EXCLUSIVE MODE"))


async def rebuild_index(session: AsyncSession) -> int:
    """Заменить словарь и веса в текущей транзакции, не закрывая сессию."""
    await lock_index_for_update(session)
    documents = [(chunk.chunk_id, chunk.content) async for chunk in get_all_chunks(session, with_source=True)]
    index = BM25(documents)

    await session.execute(delete(BM25BlockORM))
    await session.execute(delete(BM25TermORM))

    terms = ({"term": term, "block": block, "coordinate": coordinate} for term, (block, coordinate) in index.coordinates.items())
    for batch in batched(terms, 1000):
        await session.execute(insert(BM25TermORM), list(batch))

    blocks = (
        {
            "chunk_id": chunk_id,
            "block": block,
            "weights": SparseVector(weights, BLOCK_SIZE),
        }
        for chunk_id, block, weights in index.weighted_blocks()
    )
    for batch in batched(blocks, 1000):
        await session.execute(insert(BM25BlockORM), list(batch))

    return len(documents)


async def rank_chunks(
    session: AsyncSession,
    terms: list[str],
    limit: int,
) -> list[SearchHit]:
    """Найти документы по сохранённым весам за один SQL-запрос."""
    if not terms or limit <= 0:
        return []

    result = await session.execute(_RANK_CHUNKS, {"terms": terms, "dimensions": str(BLOCK_SIZE), "limit": limit})
    return [SearchHit(**row) for row in result.mappings()]
