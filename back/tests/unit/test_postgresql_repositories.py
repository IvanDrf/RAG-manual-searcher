from collections.abc import AsyncGenerator, Callable
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from src.domain.models.postgresql import BookORM, ChatORM, ChunkORM, HistoryORM, UserORM
from src.domain.rules import UserRole
from src.infrastructure.repository.postgresql import book_repo, chat_repo, chunk_repo, history_repo, user_repo


def compiled_query(session_mock: MagicMock) -> tuple[str, dict[str, object]]:
    assert session_mock.execute.call_args is not None
    query = cast(Select, session_mock.execute.call_args.args[0])
    compiled = query.compile(dialect=postgresql.dialect())

    return str(compiled), dict(compiled.params or {})


@pytest.mark.parametrize("commit", [False, True])
@pytest.mark.parametrize(
    ("add", "model"),
    [(user_repo.add_user, UserORM), (chat_repo.add_chat, ChatORM), (history_repo.add_history, HistoryORM)],
)
async def test_add_preserves_transaction_boundary(
    session: AsyncSession, session_mock: MagicMock, add: Callable, model: type, commit: bool
) -> None:
    record = model()

    await add(session, record, commit=commit)

    session_mock.add.assert_called_once_with(record)
    assert session_mock.commit.await_count == int(commit)
    session_mock.rollback.assert_not_awaited()


@pytest.mark.parametrize("commit", [False, True])
async def test_delete_chat(session: AsyncSession, session_mock: MagicMock, commit: bool) -> None:
    chat = ChatORM()

    await chat_repo.delete_chat(session, chat, commit=commit)

    session_mock.delete.assert_awaited_once_with(chat)
    assert session_mock.commit.await_count == int(commit)


async def test_add_books_uses_bulk_add_without_commit(session: AsyncSession, session_mock: MagicMock) -> None:
    books = [BookORM(), BookORM()]

    await chunk_repo.add_books(session, books)

    session_mock.add_all.assert_called_once_with(books)
    session_mock.commit.assert_not_awaited()


@pytest.mark.parametrize("block", [False, True])
@pytest.mark.parametrize("found", [False, True])
@pytest.mark.parametrize("lookup", ["username", "user_id"])
async def test_user_lookup(session: AsyncSession, session_mock: MagicMock, block: bool, found: bool, lookup: str) -> None:
    user = UserORM() if found else None
    session_mock.execute.return_value.scalar_one_or_none.return_value = user
    value = "alice" if lookup == "username" else str(uuid4())
    method = user_repo.find_user_by_username if lookup == "username" else user_repo.find_user_by_user_id

    result = await method(session, value, block=block)

    assert result is user
    sql, params = compiled_query(session_mock)
    assert f"users.{lookup} =" in sql
    assert value in params.values()
    assert params["param_1"] == 1
    assert ("FOR UPDATE" in sql) is block


@pytest.mark.parametrize("role", [None, UserRole.USER, UserRole.ADMIN])
@pytest.mark.parametrize("block", [False, True])
async def test_users_filter_pagination_and_lock(session: AsyncSession, session_mock: MagicMock, role: UserRole | None, block: bool) -> None:
    users = [UserORM(), UserORM()]
    session_mock.execute.return_value.scalars.return_value.all.return_value = users

    result = await user_repo.find_users(session, limit=7, offset=3, user_role=role, block=block)

    assert result == users
    sql, params = compiled_query(session_mock)
    assert "ORDER BY users.username" in sql
    assert params["param_1"] == 7 and params["param_2"] == 3
    assert ("users.user_role =" in sql) is (role is not None)

    if role:
        assert role in params.values()

    assert ("FOR UPDATE" in sql) is block


@pytest.mark.parametrize("block", [False, True])
async def test_chat_lookup_requires_both_owner_and_chat(session: AsyncSession, session_mock: MagicMock, block: bool) -> None:
    user_id, chat_id = uuid4(), uuid4()
    chat = ChatORM()
    session_mock.execute.return_value.scalar_one_or_none.return_value = chat

    result = await chat_repo.find_chat_for_user(session, user_id=user_id, chat_id=chat_id, block=block)

    assert result is chat
    sql, params = compiled_query(session_mock)
    assert "chats.chat_id =" in sql and "AND chats.user_id =" in sql
    assert user_id in params.values() and chat_id in params.values()
    assert ("FOR UPDATE" in sql) is block


@pytest.mark.parametrize("empty", [False, True])
async def test_chats_are_scoped_and_sorted(session: AsyncSession, session_mock: MagicMock, empty: bool) -> None:
    user_id = uuid4()
    rows = [] if empty else [ChatORM()]
    session_mock.execute.return_value.scalars.return_value.all.return_value = rows

    result = await chat_repo.find_chats_for_user(session, user_id=user_id, limit=5, offset=2)

    assert result == (rows or None)
    sql, params = compiled_query(session_mock)
    assert "WHERE chats.user_id =" in sql and "ORDER BY chats.edited_at DESC" in sql
    assert user_id in params.values()
    assert params["param_1"] == 5 and params["param_2"] == 2


@pytest.mark.parametrize("empty", [False, True])
async def test_books_have_stable_order_and_pagination(session: AsyncSession, session_mock: MagicMock, empty: bool) -> None:
    rows = [] if empty else [BookORM()]
    session_mock.execute.return_value.scalars.return_value.all.return_value = rows

    result = await book_repo.find_books(session, limit=4, offset=8)

    assert result == rows
    sql, params = compiled_query(session_mock)
    assert "ORDER BY books.book_title, books.book_id" in sql
    assert params["param_1"] == 4 and params["param_2"] == 8


@pytest.mark.parametrize("empty", [False, True])
async def test_history_filters_owner_and_orders_by_existing_timestamp(session: AsyncSession, session_mock: MagicMock, empty: bool) -> None:
    user_id, chat_id = uuid4(), uuid4()
    rows = [] if empty else [HistoryORM()]
    session_mock.execute.return_value.scalars.return_value.all.return_value = rows

    result = await history_repo.find_history_for_user(session, user_id=user_id, chat_id=chat_id, limit=3, offset=1)

    assert result == (rows or None)
    sql, params = compiled_query(session_mock)
    assert "JOIN chats ON chats.chat_id = histories.chat_id" in sql
    assert "chats.user_id =" in sql and "AND histories.chat_id =" in sql
    assert "ORDER BY histories.dialog_at DESC" in sql
    assert user_id in params.values() and chat_id in params.values()
    assert params["param_1"] == 3 and params["param_2"] == 1


@pytest.mark.parametrize("stop_early", [False, True])
async def test_chunk_stream_is_closed(session: AsyncSession, session_mock: MagicMock, stop_early: bool) -> None:
    rows = [ChunkORM(), ChunkORM()]
    stream = MagicMock()
    stream.__aiter__.return_value = rows
    stream.close = AsyncMock()
    session_mock.stream_scalars.return_value = stream
    generator = chunk_repo.get_all_chunks(session)

    if stop_early:
        assert await anext(generator) is rows[0]

        await generator.aclose()
    else:
        assert [row async for row in generator] == rows

    stream.close.assert_awaited_once()
    assert session_mock.stream_scalars.call_args is not None
    sql = str(session_mock.stream_scalars.call_args.args[0])
    assert "ORDER BY chunks.chunk_id" in sql


async def test_chunk_stream_is_closed_on_failure(session: AsyncSession, session_mock: MagicMock) -> None:
    async def broken_stream() -> AsyncGenerator[ChunkORM, None]:
        yield ChunkORM()
        raise SQLAlchemyError("stream failed")

    stream = MagicMock()
    stream.__aiter__.side_effect = broken_stream
    stream.close = AsyncMock()
    session_mock.stream_scalars.return_value = stream

    with pytest.raises(SQLAlchemyError, match="stream failed"):
        _ = [row async for row in chunk_repo.get_all_chunks(session)]

    stream.close.assert_awaited_once()


async def test_repository_propagates_database_failure(session: AsyncSession, session_mock: MagicMock) -> None:
    session_mock.execute.side_effect = SQLAlchemyError("database unavailable")

    with pytest.raises(SQLAlchemyError, match="database unavailable"):
        await user_repo.find_user_by_username(session, "alice")
