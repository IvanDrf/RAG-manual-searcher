from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from clickhouse_connect.driver.exceptions import DatabaseError, InterfaceError

from src.core.exc import InternalError
from src.domain.models.clickhouse import LLMResponseORM
from src.infrastructure.analytics import llm_response
from src.infrastructure.analytics.llm_response import LLMStatisticsScraper
from src.infrastructure.repository.clickhouse.llm_statistics import LLMStatisticsRepo


async def test_clickhouse_insert_matches_column_order() -> None:
    client = MagicMock()
    client.insert = AsyncMock()
    records = [LLMResponseORM(response_id=uuid4(), model="model", promt="question", is_success=True)]

    await LLMStatisticsRepo(client).add_llm_statistics(records)

    columns = [column.name for column in LLMResponseORM.__table__.columns]
    client.insert.assert_awaited_once_with(
        table="llm_statistics", data=[[getattr(records[0], column) for column in columns]], column_names=columns
    )


async def test_clickhouse_rejects_empty_batch() -> None:
    client = MagicMock()
    client.insert = AsyncMock()

    with pytest.raises(InternalError, match="empty"):
        await LLMStatisticsRepo(client).add_llm_statistics([])

    client.insert.assert_not_awaited()


@pytest.mark.parametrize("error", [DatabaseError("offline"), InterfaceError("offline")])
async def test_clickhouse_failure_becomes_domain_error(error: Exception) -> None:
    client = MagicMock()
    client.insert = AsyncMock(side_effect=error)

    with pytest.raises(InternalError, match="can't insert statistics"):
        await LLMStatisticsRepo(client).add_llm_statistics([LLMResponseORM(response_id=uuid4())])


async def test_statistics_batch_records_identifiers_and_timing(monkeypatch: pytest.MonkeyPatch) -> None:
    repository = MagicMock()
    repository.add_llm_statistics = AsyncMock()
    scraper = LLMStatisticsScraper(batch_size=2, statistics_repo=repository)
    monkeypatch.setattr(llm_response, "perf_counter", MagicMock(side_effect=[10.0, 10.25, 10.5, 10.75]))
    scraper.measure_time()

    await scraper.save(model="first", promt="q1", is_success=True)
    await scraper.save(model="second", promt="q2", is_success=False, error_type="ExternalError", error_message="offline")

    repository.add_llm_statistics.assert_not_awaited()

    await scraper.save(model="third", promt="q3", is_success=True)

    repository.add_llm_statistics.assert_awaited_once()

    records = repository.add_llm_statistics.call_args.args[0]
    assert [record.model for record in records] == ["first", "second"]
    assert [record.reasoning_time for record in records] == [0.25, 0.5]
    assert all(isinstance(record.response_id, UUID) for record in records)
    assert records[0].response_id != records[1].response_id
    assert records[0].responsed_at == records[1].responsed_at
    assert records[1].error_type == "ExternalError" and records[1].error_message == "offline"


async def test_statistics_keeps_failed_batch_for_retry_and_bounds_buffer() -> None:
    repository = MagicMock()
    repository.add_llm_statistics = AsyncMock(side_effect=InternalError("offline"))
    scraper = LLMStatisticsScraper(batch_size=1, statistics_repo=repository)
    scraper.measure_time()

    for index in range(5):
        await scraper.save(model=f"model-{index}", promt="q", is_success=True)

    retained = repository.add_llm_statistics.call_args.args[0]
    assert len(retained) == 3
    assert [record.model for record in retained] == ["model-0", "model-1", "model-2"]

    repository.add_llm_statistics.side_effect = None
    await scraper.save(model="recovered", promt="q", is_success=True)

    assert repository.add_llm_statistics.call_args.args[0] == retained


@pytest.mark.parametrize(("answer", "found"), [("Ответ [CHUNK 1]", True), ("Недостаточно данных в конспекте", False)])
def test_context_presence(answer: str, found: bool) -> None:
    scraper = LLMStatisticsScraper(batch_size=1, statistics_repo=MagicMock())

    assert scraper.is_found_context(answer) is found


def test_incoming_rag_refusal_is_not_found_context() -> None:
    scraper = LLMStatisticsScraper(batch_size=1, statistics_repo=MagicMock())
    assert not scraper.is_found_context("Нет ответа в прикреплённых данных")
