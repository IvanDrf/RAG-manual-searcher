from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from redis.asyncio import Redis

from src.api.dependencies import get_redis
from src.api.utils import handle_errors
from src.domain.rules import UserRole, decode_jwt
from src.infrastructure.repository.redis.block_repo import is_user_in_block_list


@handle_errors
async def admin_middleware(access_token: Annotated[str, Cookie(alias="access-token")]) -> None:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="access токен отсутствует")

    payload = decode_jwt(access_token)
    role = payload.get("user_role")
    try:
        role = UserRole(role)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="невалидный access токен")

    if role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="недостаточно прав доступа")


@handle_errors
async def auth_middleware(access_token: Annotated[str, Cookie(alias="access-token")], redis: Annotated[Redis, Depends(get_redis)]) -> None:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="access токен отсутствует")

    payload = decode_jwt(access_token)
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="отсутствует user_id")

    # if user in block list
    if await is_user_in_block_list(redis, user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="вы были заблокированы, обратитесь к администратору")
