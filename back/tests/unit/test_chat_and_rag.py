import json
from importlib import import_module
from inspect import unwrap
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, Response
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api import chat
from src.core.exc import ExternalError
from src.domain.models.postgresql import ChatORM, HistoryORM
from src.domain.rules import get_current_time
from src.domain.schemas import LLMPromtSchema
from src.infrastructure.repository.postgresql.bm25_repo import SearchHit

rag_module = import_module("src.infrastructure.rag.rag")


@given(text=st.text(), limit=st.integers(min_value=1, max_value=100))
def test_chat_name_is_bounded_prefix(text: str, limit: int) -> None:
    result = chat.create_chat_name(text, max_name_length=limit)

    assert result == text[:limit]
    assert len(result) <= limit


@pytest.mark.parametrize("failures", [0, 1, 2])
async def test_model_fallback_stops_on_first_success(monkeypatch: pytest.MonkeyPatch, failures: int) -> None:
    send = AsyncMock(side_effect=[ExternalError("failed")] * failures + ["answer"])
    monkeypatch.setattr(chat, "send_request_to_llm", send)
    client, scraper = MagicMock(), MagicMock()
    models = ("first", "second", "third")

    result = await chat.send_request_to_llm_fallback(
        client, llm_url="https://llm.invalid", api_key="test", promt="question", models=models, scraper=scraper
    )

    assert result == ("answer", models[failures])
    assert [call.kwargs["model"] for call in send.await_args_list] == list(models[: failures + 1])
    assert all(call.kwargs["scraper"] is scraper for call in send.await_args_list)


@pytest.mark.parametrize("models", [(), ("first", "second")])
async def test_fallback_reports_exhaustion(monkeypatch: pytest.MonkeyPatch, models: tuple[str, ...]) -> None:
    send = AsyncMock(side_effect=ExternalError("failed"))
    monkeypatch.setattr(chat, "send_request_to_llm", send)

    with pytest.raises(ExternalError, match="Ни одна"):
        await chat.send_request_to_llm_fallback(
            MagicMock(), llm_url="https://llm.invalid", api_key="test", promt="q", models=models, scraper=MagicMock()
        )

    assert send.await_count == len(models)


def test_prompt_contains_question_numbered_context_and_no_data_rule() -> None:
    hits = [SearchHit(uuid4(), "Учебник", "Первый фрагмент", 1.0), SearchHit(uuid4(), "Конспект", "Второй фрагмент", 0.5)]
    prompt = rag_module.build_prompt("Что такое интеграл?", hits)

    assert "ВОПРОС\nЧто такое интеграл?" in prompt
    assert "[CHUNK 1] Учебник\nПервый фрагмент" in prompt
    assert "[CHUNK 2] Конспект\nВторой фрагмент" in prompt
    assert rag_module.REFUSAL in prompt


async def test_retrieval_normalizes_question_and_queries_index(monkeypatch: pytest.MonkeyPatch) -> None:
    normalize = MagicMock(return_value="интеграл функция")
    rank = AsyncMock(return_value=[])
    monkeypatch.setattr(rag_module, "normalize_text", normalize)
    monkeypatch.setattr(rag_module, "rank_chunks", rank)
    session = MagicMock()

    assert await rag_module.retrieve_context(session, "Об интегралах функций") == []
    normalize.assert_called_once_with("Об интегралах функций")
    rank.assert_awaited_once_with(session, ["интеграл", "функция"], 3)


@pytest.mark.parametrize("found", [False, True])
async def test_delete_chat_checks_owner_before_mutation(session: AsyncSession, monkeypatch: pytest.MonkeyPatch, found: bool) -> None:
    user_id, chat_id = uuid4(), uuid4()
    record = ChatORM(chat_id=chat_id, user_id=user_id)
    find = AsyncMock(return_value=record if found else None)
    delete = AsyncMock()
    monkeypatch.setattr(chat, "find_chat_for_user", find)
    monkeypatch.setattr(chat, "delete_chat", delete)

    if found:
        await unwrap(chat.delete_chat_with_llm)(None, Response(), chat_id, session, user_id)

        delete.assert_awaited_once_with(session, record, commit=True)
    else:
        with pytest.raises(HTTPException) as caught:
            await unwrap(chat.delete_chat_with_llm)(None, Response(), chat_id, session, user_id)

        assert caught.value.status_code == 404
        delete.assert_not_awaited()

    find.assert_awaited_once_with(session, user_id=user_id, chat_id=chat_id, block=True)


@pytest.mark.parametrize("existing_chat", [False, True])
async def test_send_prompt_saves_chat_and_history_and_returns_json(
    session: AsyncSession, session_mock: MagicMock, monkeypatch: pytest.MonkeyPatch, existing_chat: bool
) -> None:
    user_id = uuid4()
    stored_chat = ChatORM(chat_id=uuid4(), user_id=user_id, name="old name")
    monkeypatch.setattr(chat, "find_chat_for_user", AsyncMock(return_value=stored_chat))
    hits = [SearchHit(uuid4(), "Учебник", "Исходный текст", 1.0)]
    search = AsyncMock(return_value=hits)
    send = AsyncMock(return_value=("answer", "model"))
    monkeypatch.setattr(chat, "retrieve_context", search)
    monkeypatch.setattr(chat, "send_request_to_llm_fallback", send)

    response = await unwrap(chat.send_promt_to_llm)(
        request=None,
        promt=LLMPromtSchema(message="question"),
        client=MagicMock(),
        llm_url="https://llm.invalid",
        llm_api_key="test-key",
        session=session,
        user_id=user_id,
        scraper=MagicMock(),
        chat_id=stored_chat.chat_id if existing_chat else None,
    )

    records = [call.args[0] for call in session_mock.add.call_args_list]
    history = next(record for record in records if isinstance(record, HistoryORM))
    if existing_chat:
        assert len(records) == 1
    else:
        new_chat = next(record for record in records if isinstance(record, ChatORM))

        assert new_chat.user_id == user_id and new_chat.name == "question"
        assert new_chat.chat_id == history.chat_id

    assert history.user_request == "question" and history.llm_response == "answer" and history.llm_model == "model"
    assert response.status_code == 200
    assert json.loads(response.body) == {"chat_id": str(history.chat_id), "model": "model", "response": "answer"}
    assert send.await_args is not None
    assert send.await_args.kwargs["promt"] == rag_module.build_prompt("question", hits)
    search.assert_awaited_once_with(session, "question")
    session_mock.commit.assert_awaited_once()


async def test_prompt_to_unknown_or_foreign_chat_never_calls_llm(
    session: AsyncSession, session_mock: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    find = AsyncMock(return_value=None)
    send = AsyncMock()
    monkeypatch.setattr(chat, "find_chat_for_user", find)
    monkeypatch.setattr(chat, "send_request_to_llm_fallback", send)
    user_id, chat_id = uuid4(), uuid4()

    with pytest.raises(HTTPException) as caught:
        await unwrap(chat.send_promt_to_llm)(
            request=None,
            promt=LLMPromtSchema(message="question"),
            client=MagicMock(),
            llm_url="https://llm.invalid",
            llm_api_key="test-key",
            session=session,
            user_id=user_id,
            scraper=MagicMock(),
            chat_id=chat_id,
        )

    assert caught.value.status_code == 404
    find.assert_awaited_once_with(session, user_id=user_id, chat_id=chat_id)
    send.assert_not_awaited()
    session_mock.add.assert_not_called()
    session_mock.commit.assert_not_awaited()


async def test_empty_context_saves_refusal_without_llm(
    session: AsyncSession, session_mock: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(chat, "retrieve_context", AsyncMock(return_value=[]))
    send = AsyncMock()
    monkeypatch.setattr(chat, "send_request_to_llm_fallback", send)

    response = await unwrap(chat.send_promt_to_llm)(
        request=None,
        promt=LLMPromtSchema(message="question"),
        client=MagicMock(),
        llm_url="https://llm.invalid",
        llm_api_key="test-key",
        session=session,
        user_id=uuid4(),
        scraper=MagicMock(),
    )

    assert json.loads(response.body)["response"] == rag_module.REFUSAL
    send.assert_not_awaited()
    history = next(call.args[0] for call in session_mock.add.call_args_list if isinstance(call.args[0], HistoryORM))
    assert history.llm_response == rag_module.REFUSAL
    session_mock.commit.assert_awaited_once()


async def test_history_response_exposes_stored_timestamp(session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    user_id, chat_id = uuid4(), uuid4()
    timestamp = get_current_time()
    record = HistoryORM(
        record_id=uuid4(), chat_id=chat_id, user_request="question", llm_response="answer", llm_model="model", dialog_at=timestamp
    )
    find = AsyncMock(return_value=[record])
    monkeypatch.setattr(chat, "find_history_for_user", find)

    result = await unwrap(chat.get_user_history)(None, Response(), chat_id, (3, 1), session, user_id)

    find.assert_awaited_once_with(session, user_id=user_id, chat_id=chat_id, limit=3, offset=1)
    assert len(result) == 1
    assert result[0].dialog_time == timestamp
    payload = result[0].model_dump(mode="json")
    assert payload["dialog_time"] == timestamp.isoformat()
    assert "dialog_at" not in payload
    assert payload["user_request"] == "question"
    assert payload["llm_response"] == "answer"
    assert payload["llm_model"] == "model"


@pytest.mark.parametrize("histories", [None, []])
async def test_missing_history_returns_404(session: AsyncSession, monkeypatch: pytest.MonkeyPatch, histories: list | None) -> None:
    monkeypatch.setattr(chat, "find_history_for_user", AsyncMock(return_value=histories))

    with pytest.raises(HTTPException) as caught:
        await unwrap(chat.get_user_history)(None, Response(), uuid4(), (10, 0), session, uuid4())

    assert caught.value.status_code == 404


@pytest.mark.parametrize("failure_stage", ["retrieval", "generation"])
async def test_failed_prompt_does_not_save_history_or_commit(
    session: AsyncSession, session_mock: MagicMock, monkeypatch: pytest.MonkeyPatch, failure_stage: str
) -> None:
    failure = SQLAlchemyError("search unavailable") if failure_stage == "retrieval" else ExternalError("LLM unavailable")
    search = AsyncMock(return_value=[SearchHit(uuid4(), "Учебник", "Контекст", 1.0)])
    send = AsyncMock(return_value=("answer", "model"))
    if failure_stage == "retrieval":
        search.side_effect = failure
    else:
        send.side_effect = failure

    monkeypatch.setattr(chat, "retrieve_context", search)
    monkeypatch.setattr(chat, "send_request_to_llm_fallback", send)

    with pytest.raises(type(failure)) as caught:
        await unwrap(chat.send_promt_to_llm)(
            request=None,
            promt=LLMPromtSchema(message="question"),
            client=MagicMock(),
            llm_url="https://llm.invalid",
            llm_api_key="test-key",
            session=session,
            user_id=uuid4(),
            scraper=MagicMock(),
        )

    assert caught.value is failure
    assert not any(isinstance(call.args[0], HistoryORM) for call in session_mock.add.call_args_list)
    session_mock.commit.assert_not_awaited()
    if failure_stage == "retrieval":
        send.assert_not_awaited()
