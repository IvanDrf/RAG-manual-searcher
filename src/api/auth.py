from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_session
from src.api.utils import create_jwt_tokens, handle_errors, set_jwt_in_cookies
from src.domain.models import UserORM
from src.domain.rules import UserRole, decode_jwt, hash_password, is_passwords_are_same
from src.domain.schemas import LoginUserSchema, RegisterUserSchema, UserInfoSchema
from src.infrastructure.repository.postgresql.user_repo import add_user, find_user_by_user_id, find_user_by_username

auth_router = APIRouter(prefix="/api/v1/auth", tags=["authorization"])


@auth_router.post(
    "/register",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Метод для регистрации пользователя со стандартной ролью - пользователь",
)
@handle_errors
async def register_user(user: RegisterUserSchema, response: Response, session: Annotated[AsyncSession, Depends(get_session)]) -> None:
    u = await find_user_by_username(session, user.username)
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
    u = await find_user_by_username(session, user.username)
    if u is None or not is_passwords_are_same(password=user.password, hashed_password=u.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="неправильный логин или пароль")

    payload = {"user_id": str(u.user_id), "user_role": u.user_role.value}
    access, refresh = create_jwt_tokens(payload)
    set_jwt_in_cookies(response, *access, *refresh)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, description="Выйти из аккаунта")
async def logout_user(response: Response) -> None:
    response.delete_cookie(key="access-token", httponly=True, secure=True, samesite="lax")
    response.delete_cookie(key="refresh-token", httponly=True, secure=True, samesite="lax")


@auth_router.get("/me", status_code=status.HTTP_200_OK, description="Информация о пользователе")
@handle_errors
async def get_user_info(access_token: Annotated[str, Cookie(alias="access-token")]) -> UserInfoSchema:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="отсутствует access токен")

    payload = decode_jwt(access_token)
    user_id, user_role = payload.get("user_id"), payload.get("user_role")
    if not user_id or not user_role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="невалидный access токен")

    try:
        user_id = UUID(user_id)
        user_role = UserRole(user_role)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="невалидный данные в access токене")

    return UserInfoSchema(user_id=user_id, user_role=user_role)


@auth_router.post("/refresh", status_code=status.HTTP_204_NO_CONTENT, description="Обнволение токенов по refresh токену")
@handle_errors
async def refresh_tokens(
    refresh_token: Annotated[str, Cookie(alias="refresh-token")], session: Annotated[AsyncSession, Depends(get_session)], response: Response
) -> None:
    """Сессия нужна, чтобы проверять не поменялась ли роль пользователя за время access токена"""

    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="невалидный refresh токен")

    payload = decode_jwt(refresh_token)
    user_id, user_role = payload.get("user_id"), payload.get("user_role")
    if not user_id or not user_role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="невалидный refresh токен")

    u = await find_user_by_user_id(session, user_id)
    if u is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="не удалось идентифицировать пользователя, обратитесь к администратору"
        )

    payload["user_role"] = u.user_role.value

    try:
        UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="невалидный данные в access токене")

    access, refresh = create_jwt_tokens(payload)
    set_jwt_in_cookies(response, *access, *refresh)
