"""Проверки весов, нормализации и общего RAG-промпта."""

from asyncio import run
from math import log1p
from uuid import UUID

import pytest
from httpx import AsyncClient, MockTransport, Request, Response
from pydantic import ValidationError

from scripts.benchmark_rag import Verdict, retrieval_scores
from src.core.config import LLMConfig
from src.infrastructure.rag.bm25 import BM25
from src.infrastructure.rag.normalization import normalize_text
from src.infrastructure.rag.rag import REFUSAL, answer_question, build_prompt
from src.infrastructure.repository.postgresql.bm25_repo import SearchHit


def test_known_bm25_weights() -> None:
    """На равных длинах и частоте 1 вклад термина равен IDF."""
    documents = [
        (UUID(int=1), "возврат оплата на карта"),
        (UUID(int=2), "статус оплата в приложение"),
        (UUID(int=3), "возврат билет через касса"),
    ]
    index = BM25(documents)
    vectors = {(chunk_id, block): weights for chunk_id, block, weights in index.weighted_blocks()}
    first_doc = vectors[(UUID(int=1), 0)]
    _, refund = index.coordinates["возврат"]
    _, payment = index.coordinates["оплата"]
    assert first_doc[refund] + first_doc[payment] == pytest.approx(2 * log1p(1.5 / 2.5))


def test_tf_saturation_and_document_length() -> None:
    """Повторение даёт прибавку, а добавление посторонних слов снижает вес."""
    documents = [
        (UUID(int=1), "вектор вектор дополнительный"),
        (UUID(int=2), "вектор дополнительный дополнительный"),
        (UUID(int=3), "вектор дополнительный дополнительный дополнительный"),
    ]
    index = BM25(documents)
    block, coordinate = index.coordinates["вектор"]
    first, second, third = [weights[coordinate] for _, vector_block, weights in index.weighted_blocks() if vector_block == block]
    assert third < second < first < 2 * second
    assert not list(BM25([]).weighted_blocks())


def test_russian_normalization() -> None:
    """Вопрос и импортированный текст используют одну форму слова."""
    try:
        normalized = normalize_text("О ВЕКТОРАМИ и матрицами!")
    except LookupError:
        pytest.skip("NLTK data required: stopwords, punkt_tab")
    assert normalized == "вектор матрица"


def test_retrieval_metrics() -> None:
    """Учитывать выдачу до третьей позиции и первый релевантный результат."""
    expected = ["D01", "D02", "D03"]
    assert retrieval_scores(["D04", "D02", "D03", "D01"], expected) == (2 / 3, 0.5)
    assert retrieval_scores([], expected) == (0.0, 0.0)


def test_prompt_uses_original_text() -> None:
    """В контекст попадает первоначальный текст с формулой и источником."""
    hit = SearchHit(UUID(int=1), "LA-04.pdf", "Ax = λx", 1.0)
    prompt = build_prompt("Какое равенство выполняется?", [hit])
    assert "[CHUNK 1] LA-04.pdf\nAx = λx" in prompt
    assert REFUSAL in prompt


def test_empty_retrieval_skips_generation() -> None:
    """Пустая выдача даёт согласованный отказ без обращения к Ollama."""

    def fail_on_http(request: Request) -> Response:
        raise AssertionError(request.url)

    async def answer_without_hits() -> str:
        async with AsyncClient(transport=MockTransport(fail_on_http)) as client:
            return await answer_question(
                client,
                question="Вопрос",
                hits=[],
                settings=LLMConfig(),
            )

    assert run(answer_without_hits()) == REFUSAL


def test_judge_requires_boolean() -> None:
    """Строку со словом true нельзя засчитать как корректный вердикт."""
    with pytest.raises(ValidationError):
        Verdict.model_validate_json('{"correct":"true","reason":"yes"}')
