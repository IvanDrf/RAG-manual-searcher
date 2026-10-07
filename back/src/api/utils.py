from asyncio import sleep
from datetime import datetime
from functools import wraps

from fastapi import HTTPException, Response, status
from httpx import ConnectError, NetworkError, TimeoutException
from loguru import logger
from redis import ConnectionError, RedisError
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from src.core.exc import ExternalError
from src.domain.rules import TokenType, create_jwt


def handle_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except (SQLAlchemyError, ConnectionRefusedError, DBAPIError, RedisError, ConnectionError) as e:
            logger.exception("Internal error", error=e)

            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ошибка на стороне сервера")

        except ExternalError as e:
            logger.exception("External error", error=e)

            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        except (TimeoutError, NetworkError, TimeoutException, ConnectError) as e:
            logger.exception("Network error", error=e)

            raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail="не удалось получить ответ от модели")

    return wrapper


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


def create_jwt_tokens(payload: dict) -> tuple[tuple[str, datetime], tuple[str, datetime]]:
    access_token, access_exp = create_jwt(payload=payload, token_type=TokenType.ACCESS)
    refresh_token, refresh_exp = create_jwt(payload=payload, token_type=TokenType.REFRESH)

    return (access_token, access_exp), (refresh_token, refresh_exp)


def set_jwt_in_cookies(response: Response, access_token: str, access_exp: datetime, refresh_token: str, refresh_exp: datetime) -> None:
    response.set_cookie("access-token", value=access_token, expires=access_exp, httponly=True, secure=True, samesite="lax")
    response.set_cookie("refresh-token", value=refresh_token, expires=refresh_exp, httponly=True, secure=True, samesite="lax")
