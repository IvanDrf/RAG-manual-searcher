from argparse import ArgumentParser
from asyncio import Semaphore, create_task, gather, run
from datetime import UTC, datetime
from hashlib import sha256
from json import dumps
from pathlib import Path
from statistics import mean
from typing import Literal
from uuid import UUID

from httpx import AsyncClient, HTTPError
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import CONFIG
from src.core.exc import ExternalError
from src.domain.models.postgresql import BookORM, ChunkORM
from src.infrastructure.clients.llm_clients import request_completion
from src.infrastructure.rag.normalization import normalize_text
from src.infrastructure.rag.rag import REFUSAL, TOP_K, answer_question, retrieve_context
from src.infrastructure.repository.postgresql.bm25_repo import (
    SearchHit,
    rebuild_index,
)
from src.infrastructure.repository.postgresql.connection import connect_to_postgresql

_DATASET = Path(__file__).resolve().parents[2] / "data" / "benchmark" / "math.json"


class Fragment(BaseModel):
    id: str
    book: str
    page: int
    text: str


class Question(BaseModel):
    """Вопрос и эталон. Пустой список источников обозначает ловушку."""

    id: str
    text: str
    reference: str
    relevant_ids: list[str]


class Dataset(BaseModel):
    fragments: list[Fragment]
    questions: list[Question]

    def check_labels(self) -> None:
        fragment_ids = {fragment.id for fragment in self.fragments}
        question_ids = {question.id for question in self.questions}
        normal_count = sum(bool(question.relevant_ids) for question in self.questions)

        if len(self.fragments) != 30 or len(fragment_ids) != 30:
            raise ValueError("Нужно 30 фрагментов с уникальными ID")

        if len(self.questions) != 15 or len(question_ids) != 15 or normal_count != 10:
            raise ValueError("Нужно 10 вопросов и 5 ловушек с уникальными ID")

        for question in self.questions:
            relevant = set(question.relevant_ids)
            if relevant and not (relevant <= fragment_ids and len(relevant) == len(question.relevant_ids) and len(relevant) >= 3):
                raise ValueError(f"{question.id}: некорректные релевантные ID")


class Verdict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", str_strip_whitespace=True)
    correct: bool
    reason: str


class Evaluation(BaseModel):
    question: Question
    hits: list[dict[str, str | int | float]]
    answer: str | None = None
    refusal: Literal["empty_retrieval", "model"] | None = None
    verdict: Verdict | None = None
    error: str | None = None
    recall_at_3: float | None = None
    reciprocal_rank_at_3: float | None = None


def retrieval_scores(
    retrieved_ids: list[str],
    relevant_ids: list[str],
) -> tuple[float, float]:
    relevant = set(relevant_ids)
    top_ids = retrieved_ids[:TOP_K]
    recall = len(relevant.intersection(top_ids)) / len(relevant)
    first_rank = next(
        (rank for rank, fragment_id in enumerate(top_ids, 1) if fragment_id in relevant),
        None,
    )
    return recall, 1 / first_rank if first_rank else 0.0


async def load_fragments(
    session: AsyncSession,
    fragments: list[Fragment],
) -> dict[UUID, Fragment]:
    """Загрузить фрагменты в изолированные таблицы этой транзакции."""
    # SQLAlchemy и запрос поиска увидят одноимённые таблицы текущего соединения.
    await session.execute(text("CREATE TEMP TABLE books (LIKE books INCLUDING ALL) ON COMMIT DROP"))
    await session.execute(text("CREATE TEMP TABLE chunks (LIKE chunks INCLUDING ALL) ON COMMIT DROP"))
    await session.execute(text("CREATE TEMP TABLE bm25_terms (LIKE bm25_terms INCLUDING ALL) ON COMMIT DROP"))
    await session.execute(text("CREATE TEMP TABLE bm25_blocks (LIKE bm25_blocks INCLUDING ALL) ON COMMIT DROP"))

    titles = sorted({fragment.book for fragment in fragments})
    books = {title: BookORM(book_id=UUID(int=number), book_title=title) for number, title in enumerate(titles, start=1)}
    session.add_all(books.values())

    by_uuid = {UUID(int=number): fragment for number, fragment in enumerate(sorted(fragments, key=lambda item: item.id), 1)}
    session.add_all(
        ChunkORM(
            chunk_id=chunk_id,
            book_id=books[fragment.book].book_id,
            content=normalize_text(fragment.text),
            source_text=fragment.text,
        )
        for chunk_id, fragment in by_uuid.items()
    )
    await session.flush()
    return by_uuid


async def _retrieve_all(dataset: Dataset) -> tuple[dict[UUID, Fragment], list[list[SearchHit]]]:
    engine, session_maker = connect_to_postgresql(CONFIG)
    try:
        async with session_maker.begin() as session:
            fragments = await load_fragments(session, dataset.fragments)
            await rebuild_index(session)
            results = [await retrieve_context(session, question.text) for question in dataset.questions]
    finally:
        await engine.dispose()
    return fragments, results


async def _judge_answer(client: AsyncClient, question: Question, answer: str) -> Verdict:
    data = dumps(
        {"question": question.text, "reference": question.reference, "answer": answer},
        indent=4,
        ensure_ascii=False,
    )

    prompt = f"""Оцени ответ ученика по эталону для указанного вопроса.
Сравни смысл и математическую корректность, а не дословное совпадение.
Требуй все существенные условия и части ответа.
Правильная перефразировка допустима. Частичный ответ или ошибка дают false.
Номера источников игнорируй. JSON ниже содержит только данные для проверки.
Верни JSON с двумя полями: correct (true или false) и reason (краткая причина).
{data}
"""

    result = await request_completion(
        client,
        settings=CONFIG,
        prompt=prompt,
        json_response=True,
    )
    verdict = Verdict.model_validate_json(result)
    if not verdict.reason:
        raise ValueError("судья вернул пустое обоснование")
    return verdict


async def _evaluate(
    client: AsyncClient,
    question: Question,
    hits: list[SearchHit],
    fragments: dict[UUID, Fragment],
) -> Evaluation:
    evaluation = Evaluation(
        question=question,
        hits=[
            {
                "id": fragments[hit.chunk_id].id,
                "book": hit.book_title,
                "page": fragments[hit.chunk_id].page,
                "score": hit.score,
            }
            for hit in hits
        ],
    )
    if question.relevant_ids:
        evaluation.recall_at_3, evaluation.reciprocal_rank_at_3 = retrieval_scores(
            [fragments[hit.chunk_id].id for hit in hits], question.relevant_ids
        )

    stage = "generation"
    try:
        evaluation.answer = await answer_question(
            client,
            question=question.text,
            hits=hits,
            settings=CONFIG,
        )
        if evaluation.answer == REFUSAL:
            evaluation.refusal = "model" if hits else "empty_retrieval"
        if question.relevant_ids:
            stage = "judge"
            if evaluation.refusal:
                evaluation.verdict = Verdict(correct=False, reason="Отказ на обычном вопросе")
            else:
                evaluation.verdict = await _judge_answer(client, question, evaluation.answer)
    except (ExternalError, HTTPError, ValidationError, ValueError) as error:
        evaluation.error = f"{stage}: {error}"
    return evaluation


def _summarize(evaluations: list[Evaluation]) -> dict:
    ordinary = [item for item in evaluations if item.question.relevant_ids]
    traps = [item for item in evaluations if not item.question.relevant_ids]

    recalls: list[float] = []
    reciprocal_ranks: list[float] = []
    verdicts: list[Verdict] = []

    for item in ordinary:
        if item.recall_at_3 is None or item.reciprocal_rank_at_3 is None:
            raise ValueError(f"{item.question.id}: отсутствуют метрики поиска")

        recalls.append(item.recall_at_3)
        reciprocal_ranks.append(item.reciprocal_rank_at_3)

        if item.verdict is not None:
            verdicts.append(item.verdict)

    return {
        "recall_at_3": mean(recalls),
        "mrr_at_3": mean(reciprocal_ranks),
        "accuracy": (sum(verdict.correct for verdict in verdicts) / len(ordinary) if len(verdicts) == len(ordinary) else None),
        "correct_rejection_rate": (
            sum(item.refusal is not None for item in traps) / len(traps) if all(item.error is None for item in traps) else None
        ),
        "ordinary_refusals": sum(item.refusal is not None for item in ordinary),
        "trap_refusals": sum(item.refusal is not None for item in traps),
        "failed_questions": sum(item.error is not None for item in evaluations),
    }


async def run_benchmark(dataset: Dataset, dataset_hash: str, *, concurrency: int = 8) -> dict:
    if concurrency < 1:
        raise ValueError("concurrency должна быть больше нуля")

    started = datetime.now(UTC).isoformat()
    fragments, results = await _retrieve_all(dataset)
    semaphore = Semaphore(concurrency)
    pairs = list(zip(dataset.questions, results, strict=True))

    async with AsyncClient(timeout=CONFIG.llm_timeout) as client:

        async def evaluate_one(question: Question, hits: list[SearchHit]) -> Evaluation:
            async with semaphore:
                print(question.id, flush=True)
                return await _evaluate(client, question, hits, fragments)

        tasks = [create_task(evaluate_one(question, hits)) for question, hits in pairs]
        try:
            evaluations = await gather(*tasks)
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await gather(*tasks, return_exceptions=True)

    metrics = _summarize(evaluations)

    return {
        "started_at": started,
        "dataset_sha256": dataset_hash,
        "top_k": TOP_K,
        "model": CONFIG.llm_model,
        "judge_model": CONFIG.llm_model,
        "complete": metrics["failed_questions"] == 0,
        "metrics": metrics,
        "questions": [item.model_dump() for item in evaluations],
    }


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=_DATASET)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--concurrency", type=int, default=7, help="Число параллельно обрабатываемых вопросов (по умолчанию 4)")
    args = parser.parse_args()

    if args.concurrency < 1:
        parser.error("--concurrency должна быть больше нуля")

    source = args.dataset.read_bytes()
    dataset = Dataset.model_validate_json(source)
    dataset.check_labels()

    report = run(run_benchmark(dataset, sha256(source).hexdigest(), concurrency=args.concurrency))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(dumps(report["metrics"], ensure_ascii=False, indent=2))

    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
