from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_session
from src.api.utils import handle_errors
from src.domain.models import UserORM
from src.domain.rules import TokenType, UserRole, create_jwt, hash_password
from src.domain.schemas import RegisterUserSchema
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

    user_id = str(user_id)
    payload = {"user_id": user_id, "user_role": UserRole.USER.value}

    access_token, access_exp = create_jwt(payload=payload, token_type=TokenType.ACCESS)
    refresh_token, refresh_exp = create_jwt(payload=payload, token_type=TokenType.REFRESH)

    response.set_cookie("access-token", value=access_token, expires=access_exp, httponly=True, secure=True, samesite="lax")
    response.set_cookie("refresh-token", value=refresh_token, expires=refresh_exp, httponly=True, secure=True, samesite="lax")
