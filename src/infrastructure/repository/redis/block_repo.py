from datetime import timedelta

from redis.asyncio import Redis

EXISTS_VALUE = "1"


async def add_user_id(redis: Redis, user_id: str, ttl: timedelta) -> None:
    await redis.set(name=user_id, value=EXISTS_VALUE, ex=ttl)


async def is_user_in_block_list(redis: Redis, user_id: str) -> bool:
    res = await redis.get(user_id)

    return res is not None and res == EXISTS_VALUE


async def delete_user_by_user_id(redis: Redis, user_id: str) -> None:
    await redis.delete(user_id)
