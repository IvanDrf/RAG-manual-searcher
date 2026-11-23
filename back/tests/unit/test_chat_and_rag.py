import json
from importlib import import_module
from inspect import unwrap
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, Response
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy.ext.asyncio import AsyncSession

from src.api import chat
from src.core.exc import ExternalError
from src.domain.models.postgresql import ChatORM, HistoryORM
from src.domain.schemas import LLMPromtSchema

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


def test_prompt_contains_question_numbered_context_and_no_data_rule(monkeypatch: pytest.MonkeyPatch) -> None:
    search = MagicMock(return_value=["Первый фрагмент", "Второй фрагмент"])
    monkeypatch.setattr(rag_module, "start_bm25", search)

    prompt = rag_module.rag("Что такое интеграл?", k=2)

    search.assert_called_once_with("Что такое интеграл?", 2)
    assert "QUESTION:\nЧто такое интеграл?" in prompt
    assert "[CHUNK 1]\nПервый фрагмент" in prompt
    assert "[CHUNK 2]\nВторой фрагмент" in prompt
    assert "Недостаточно данных в конспекте" in prompt


@pytest.mark.parametrize(("text", "k"), [(None, 3), (42, 3), ("q", "3")])
def test_rag_rejects_wrong_argument_types(text: object, k: object) -> None:
    with pytest.raises(TypeError):
        rag_module.rag(text, k)


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
    search = MagicMock(return_value="question with context")
    send = AsyncMock(return_value=("answer", "model"))
    monkeypatch.setattr(chat, "rag", search)
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
    assert send.await_args.kwargs["promt"] == "question with context"
    search.assert_called_once_with("question", k=3)
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
