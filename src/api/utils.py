from functools import wraps

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from src.core.exc import ExternalError


def handle_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except (SQLAlchemyError, ConnectionRefusedError, DBAPIError) as e:
            logger.exception("Internal error", error=e)

            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ошибка на стороне сервера")

        except ExternalError as e:
            logger.exception("External error", error=e)

            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return wrapper
