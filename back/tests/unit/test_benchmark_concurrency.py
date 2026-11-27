from asyncio import Event, sleep, wait_for
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from httpx import AsyncClient

from scripts import benchmark_rag as benchmark
from src.core.exc import ExternalError
from src.infrastructure.repository.postgresql.bm25_repo import SearchHit


def benchmark_dataset() -> benchmark.Dataset:
    return benchmark.Dataset(
        fragments=[benchmark.Fragment(id="D01", book="book", page=1, text="context")],
        questions=[benchmark.Question(id=f"Q{number}", text=f"Q{number}", reference="answer", relevant_ids=["D01"]) for number in range(5)]
        + [benchmark.Question(id="T01", text="T01", reference="", relevant_ids=[])],
    )


@pytest.mark.parametrize("concurrency", [1, 2, 4])
async def test_parallel_evaluation_limits_requests_and_preserves_report_order(monkeypatch: pytest.MonkeyPatch, concurrency: int) -> None:
    dataset = benchmark_dataset()
    chunk_id = UUID(int=1)
    hit = SearchHit(chunk_id, "book", "context", 1.0)
    monkeypatch.setattr(benchmark, "_retrieve_all", AsyncMock(return_value=({chunk_id: dataset.fragments[0]}, [[hit]] * 6)))
    active = 0
    peak = 0
    finished: list[str] = []
    second_finished = Event()

    async def answer(client: AsyncClient, *, question: str, **kwargs: object) -> str:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        try:
            if question == "Q0" and concurrency > 1:
                await second_finished.wait()
            await sleep(0)
            if question == "Q2":
                raise ExternalError("provider unavailable")
            return benchmark.REFUSAL if question == "T01" else "answer"
        finally:
            active -= 1

    async def judge(client: AsyncClient, question: benchmark.Question, answer: str) -> benchmark.Verdict:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        try:
            await sleep(0)
            finished.append(question.id)
            if question.id == "Q1":
                second_finished.set()
            return benchmark.Verdict(correct=True, reason="correct")
        finally:
            active -= 1

    monkeypatch.setattr(benchmark, "answer_question", answer)
    monkeypatch.setattr(benchmark, "_judge_answer", judge)

    report = await wait_for(benchmark.run_benchmark(dataset, "hash", concurrency=concurrency), timeout=5)

    assert peak == concurrency
    assert active == 0
    assert [item["question"]["id"] for item in report["questions"]] == [question.id for question in dataset.questions]
    if concurrency > 1:
        assert finished.index("Q1") < finished.index("Q0")
    assert report["questions"][2]["error"] == "generation: provider unavailable"
    assert report["questions"][-1]["refusal"] == "model"
    assert report["metrics"]["failed_questions"] == 1
    assert report["complete"] is False


@pytest.mark.parametrize("concurrency", [0, -1])
async def test_invalid_concurrency_does_not_start_retrieval(monkeypatch: pytest.MonkeyPatch, concurrency: int) -> None:
    retrieve = AsyncMock()
    monkeypatch.setattr(benchmark, "_retrieve_all", retrieve)

    with pytest.raises(ValueError, match="concurrency"):
        await benchmark.run_benchmark(benchmark_dataset(), "hash", concurrency=concurrency)

    retrieve.assert_not_awaited()


async def test_unexpected_failure_cancels_other_evaluations(monkeypatch: pytest.MonkeyPatch) -> None:
    dataset = benchmark_dataset()
    monkeypatch.setattr(benchmark, "_retrieve_all", AsyncMock(return_value=({}, [[] for _ in dataset.questions])))
    second_started = Event()
    second_stopped = Event()
    never_finish = Event()

    async def evaluate(
        client: AsyncClient, question: benchmark.Question, hits: list[SearchHit], fragments: dict[UUID, benchmark.Fragment]
    ) -> benchmark.Evaluation:
        if question.id == "Q0":
            await second_started.wait()
            raise RuntimeError("unexpected failure")
        try:
            second_started.set()
            await never_finish.wait()
            raise AssertionError("unreachable")
        finally:
            second_stopped.set()

    monkeypatch.setattr(benchmark, "_evaluate", evaluate)

    with pytest.raises(RuntimeError, match="unexpected failure"):
        await wait_for(benchmark.run_benchmark(dataset, "hash", concurrency=2), timeout=5)

    assert second_stopped.is_set()
