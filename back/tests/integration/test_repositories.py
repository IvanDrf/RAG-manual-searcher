from datetime import timedelta
from uuid import uuid4

import pytest
from clickhouse_connect import get_async_client
from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.postgresql import BookORM, ChatORM, ChunkORM, HistoryORM, UserORM
from src.domain.rules import UserRole, get_current_time
from src.infrastructure.repository.postgresql import book_repo, chat_repo, chunk_repo, history_repo, user_repo
from src.infrastructure.repository.redis.block_repo import add_user_in_block_list, is_user_in_block_list, remove_user_from_block_list

pytestmark = pytest.mark.integration


async def test_postgresql_owner_isolation_and_history_order(pg_session: AsyncSession) -> None:
    alice = UserORM(user_id=uuid4(), username="alice", hashed_password="hash", user_role=UserRole.USER)
    bob = UserORM(user_id=uuid4(), username="bobby", hashed_password="hash", user_role=UserRole.ADMIN)
    pg_session.add_all([alice, bob])

    await pg_session.flush()
    now = get_current_time()

    first = ChatORM(chat_id=uuid4(), name="first", user_id=alice.user_id, edited_at=now - timedelta(hours=1))
    second = ChatORM(chat_id=uuid4(), name="second", user_id=alice.user_id, edited_at=now)
    pg_session.add_all([first, second, ChatORM(chat_id=uuid4(), name="private", user_id=bob.user_id)])

    await pg_session.flush()

    older = HistoryORM(
        record_id=uuid4(),
        chat_id=first.chat_id,
        user_request="old",
        llm_response="old",
        llm_model="model",
        dialog_at=now - timedelta(minutes=1),
    )
    newer = HistoryORM(record_id=uuid4(), chat_id=first.chat_id, user_request="new", llm_response="new", llm_model="model", dialog_at=now)
    pg_session.add_all([older, newer])

    await pg_session.flush()

    assert await chat_repo.find_chat_for_user(pg_session, user_id=bob.user_id, chat_id=first.chat_id) is None
    assert await chat_repo.find_chats_for_user(pg_session, user_id=alice.user_id, limit=1, offset=1) == [first]
    assert await history_repo.find_history_for_user(pg_session, user_id=bob.user_id, chat_id=first.chat_id, limit=10, offset=0) is None
    assert await history_repo.find_history_for_user(pg_session, user_id=alice.user_id, chat_id=first.chat_id, limit=1, offset=0) == [newer]
    assert await user_repo.find_users(pg_session, limit=10, offset=0, user_role=UserRole.ADMIN) == [bob]


async def test_postgresql_unique_username_and_commit(pg_session: AsyncSession) -> None:
    user = UserORM(user_id=uuid4(), username="alice", hashed_password="hash")

    await user_repo.add_user(pg_session, user, commit=True)

    assert await user_repo.find_user_by_username(pg_session, "alice", block=True) is user

    with pytest.raises(IntegrityError):
        async with pg_session.begin_nested():
            await user_repo.add_user(pg_session, UserORM(user_id=uuid4(), username="alice", hashed_password="hash"))
            await pg_session.flush()


async def test_postgresql_book_pagination_vector_stream_and_cascade(pg_session: AsyncSession) -> None:
    first = BookORM(book_id=uuid4(), book_title="Algebra")
    second = BookORM(book_id=uuid4(), book_title="Calculus")

    await chunk_repo.add_books(pg_session, [second, first])
    await pg_session.flush()

    chunk = ChunkORM(chunk_id=uuid4(), book_id=first.book_id, content="integral", embedding=[0.1, 0.2, 0.3])
    pg_session.add(chunk)

    await pg_session.flush()

    assert await book_repo.find_books(pg_session, limit=1, offset=1) == [second]
    assert [row async for row in chunk_repo.get_all_chunks(pg_session)] == [chunk]

    await pg_session.delete(first)
    await pg_session.flush()

    assert [row async for row in chunk_repo.get_all_chunks(pg_session)] == []


async def test_real_redis_block_lifecycle() -> None:
    async with Redis(host="127.0.0.1", port=26379) as client:
        key = str(uuid4())

        try:
            await add_user_in_block_list(client, key, timedelta(seconds=30))

            assert await is_user_in_block_list(client, key)
            assert 0 < await client.ttl(key) <= 30

            await remove_user_from_block_list(client, key)

            assert not await is_user_in_block_list(client, key)
        finally:
            await client.delete(key)


async def test_clickhouse_connection() -> None:
    client = await get_async_client(host="127.0.0.1", port=28123, username="rag_test", password="rag_test", database="rag_test")
    try:
        assert await client.ping()

        result = await client.query("SELECT 1")

        assert result.result_rows == [(1,)]
    finally:
        await client.close()
