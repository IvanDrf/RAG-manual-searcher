import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.core.exc import ExternalError
from src.infrastructure.clients import llm_clients, utils


async def test_retry_stops_after_success(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep = AsyncMock()
    monkeypatch.setattr(utils, "sleep", sleep)
    operation = AsyncMock(side_effect=[ExternalError("retry"), "ok"])
    wrapped = utils.circuit_breaker(ExternalError, attempts=3, base_delay=0.5)(operation)

    result = await wrapped()

    assert result == "ok"
    assert operation.await_count == 2
    sleep.assert_awaited_once_with(0.5)


async def test_retry_exhaustion_raises_last_error(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep = AsyncMock()
    monkeypatch.setattr(utils, "sleep", sleep)
    original = ExternalError("unavailable")
    operation = AsyncMock(side_effect=original)
    wrapped = utils.circuit_breaker(ExternalError, attempts=3, base_delay=0.5)(operation)

    with pytest.raises(ExternalError) as caught:
        await wrapped()

    assert caught.value is original and operation.await_count == 3
    assert [call.args[0] for call in sleep.await_args_list] == [0.5, 1.0, 1.5]


async def test_unexpected_error_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep = AsyncMock()
    monkeypatch.setattr(utils, "sleep", sleep)
    operation = AsyncMock(side_effect=ValueError("bug"))

    with pytest.raises(ValueError):
        await utils.circuit_breaker(ExternalError, 3, 0.5)(operation)()

    operation.assert_awaited_once()
    sleep.assert_not_awaited()


@pytest.fixture
def scraper() -> MagicMock:
    result = MagicMock()
    result.save = AsyncMock()
    result.is_found_context.return_value = True

    return result


@pytest.fixture
def statistics_tasks(monkeypatch: pytest.MonkeyPatch) -> list[asyncio.Task]:
    tasks = []

    def create_task(coroutine) -> asyncio.Task:
        task = asyncio.create_task(coroutine)
        tasks.append(task)
        return task

    monkeypatch.setattr(llm_clients, "create_task", create_task)
    return tasks


async def test_llm_request_and_success_statistics(scraper: MagicMock, statistics_tasks: list[asyncio.Task]) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-key"
        assert json.loads(request.content) == {"model": "test-model", "messages": [{"role": "user", "content": "question"}]}

        return httpx.Response(200, json={"choices": [{"message": {"content": "answer"}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await llm_clients.send_request_to_llm(
            client, model="test-model", llm_url="https://llm.invalid", api_key="test-key", promt="question", scraper=scraper
        )
    await asyncio.gather(*statistics_tasks)

    assert result == "answer"
    scraper.measure_time.assert_called_once()
    scraper.save.assert_awaited_once_with(model="test-model", promt="question", is_success=True, is_found_context=True)


@pytest.mark.parametrize(
    ("status", "body"),
    [(503, '{"error":"unavailable"}'), (502, "Bad Gateway"), (200, "invalid json"), (200, '{"choices":[]}')],
)
async def test_llm_invalid_responses_retry_and_record_failures(
    status: int, body: str, scraper: MagicMock, statistics_tasks: list[asyncio.Task], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(utils, "sleep", AsyncMock())
    requests = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status, text=body)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(ExternalError):
            await llm_clients.send_request_to_llm(
                client, model="test-model", llm_url="https://llm.invalid", api_key="test-key", promt="question", scraper=scraper
            )
    await asyncio.gather(*statistics_tasks)

    assert len(requests) == scraper.save.await_count == 3
    assert all(call.kwargs["is_success"] is False for call in scraper.save.await_args_list)


async def test_network_error_is_propagated(scraper: MagicMock, statistics_tasks: list[asyncio.Task]) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(httpx.ConnectError):
            await llm_clients.send_request_to_llm(
                client, model="test-model", llm_url="https://llm.invalid", api_key="test-key", promt="question", scraper=scraper
            )

    assert not statistics_tasks
