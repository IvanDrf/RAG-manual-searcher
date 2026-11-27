from datetime import timedelta

import pytest
from fakeredis import FakeAsyncRedis, FakeServer
from redis.exceptions import ConnectionError

from src.infrastructure.repository.redis.block_repo import (
    add_user_in_block_list,
    is_user_in_block_list,
    remove_user_from_block_list,
)


@pytest.mark.parametrize("decode_responses", [False, True])
async def test_block_round_trip_and_ttl(decode_responses: bool) -> None:
    async with FakeAsyncRedis(decode_responses=decode_responses) as client:
        assert not await is_user_in_block_list(client, "alice")

        await add_user_in_block_list(client, "alice", timedelta(minutes=5))

        assert await is_user_in_block_list(client, "alice")
        assert not await is_user_in_block_list(client, "bob")
        assert 0 < await client.ttl("alice") <= 300

        await remove_user_from_block_list(client, "alice")
        await remove_user_from_block_list(client, "alice")

        assert not await is_user_in_block_list(client, "alice")


async def test_expired_and_unexpected_values_are_not_blocked(redis_client: FakeAsyncRedis) -> None:
    await add_user_in_block_list(redis_client, "expired", timedelta(minutes=1))
    await redis_client.pexpire("expired", 0)
    await redis_client.set("unexpected", "0")

    assert not await is_user_in_block_list(redis_client, "expired")
    assert not await is_user_in_block_list(redis_client, "unexpected")


async def test_redis_connection_failure_is_not_a_cache_miss() -> None:
    server = FakeServer()
    server.connected = False

    async with FakeAsyncRedis(server=server) as client:
        with pytest.raises(ConnectionError):
            await is_user_in_block_list(client, "alice")
