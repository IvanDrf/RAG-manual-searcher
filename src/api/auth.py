from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_session
from src.api.utils import create_jwt_tokens, handle_errors, set_jwt_in_cookies
from src.domain.models import UserORM
from src.domain.rules import UserRole, hash_password, is_passwords_are_same
from src.domain.schemas import LoginUserSchema, RegisterUserSchema
from src.infrastructure.repository.postgresql.user_repo import add_user, find_user

auth_router = APIRouter(prefix="/api/v1/auth", tags=["authorization"])


@auth_router.post(
    "/register",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Метод для регистрации пользователя со стандартной ролью - пользователь",
)
@handle_errors
async def register_user(user: RegisterUserSchema, response: Response, session: Annotated[AsyncSession, Depends(get_session)]) -> None:
    u = await find_user(session, user.username)
    if u is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="пользователь с таким именем уже существует")

    hashed_password = hash_password(user.password)
    user_id = uuid4()
    u = UserORM(user_id=user_id, username=user.username, hashed_password=hashed_password, user_role=UserRole.USER)

    await add_user(session, user=u)
    await session.commit()

    payload = {"user_id": str(user_id), "user_role": UserRole.USER.value}
    access, refresh = create_jwt_tokens(payload)
    set_jwt_in_cookies(response, *access, *refresh)


@auth_router.post("/login", status_code=status.HTTP_204_NO_CONTENT, description="Логин пользователя")
@handle_errors
async def login_user(user: LoginUserSchema, response: Response, session: Annotated[AsyncSession, Depends(get_session)]) -> None:
    u = await find_user(session, user.username)
    if u is None or not is_passwords_are_same(password=user.password, hashed_password=u.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="неправильный логин или пароль")

    payload = {"user_id": str(u.user_id), "user_role": u.user_role.value}
    access, refresh = create_jwt_tokens(payload)
    set_jwt_in_cookies(response, *access, *refresh)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, description="Выйти из аккаунта")
@handle_errors
async def logout_user(response: Response) -> None:
    response.delete_cookie(key="access-token", httponly=True, secure=True, samesite="lax")
    response.delete_cookie(key="refresh-token", httponly=True, secure=True, samesite="lax")
