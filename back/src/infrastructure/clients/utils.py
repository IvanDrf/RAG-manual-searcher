from asyncio import sleep
from functools import wraps

from loguru import logger

type Seconds = float


def circuit_breaker(exc: tuple[type[Exception]] | type[Exception], attempts: int, base_delay: Seconds):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            delay = base_delay

            for attempt in range(1, attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exc as e:
                    logger.error("circuit_breaker", func=func.__name__, attempt=attempt, error=e)
                    await sleep(delay)

                    last_exc = e
                    delay = 0.5 + delay

            if last_exc:
                raise last_exc

        return wrapper

    return decorator
