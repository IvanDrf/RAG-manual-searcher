from typing import Annotated

from fastapi import Cookie, HTTPException, status

from src.api.utils import handle_errors
from src.domain.rules import UserRole, decode_jwt


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
async def auth_middleware(access_token: Annotated[str, Cookie(alias="access-token")]) -> None:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="access токен отсутствует")

    decode_jwt(access_token)
