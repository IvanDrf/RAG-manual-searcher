from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models import UserORM
from src.api.dependencies import get_session
from src.domain.rules import hash_password
from src.domain.schemas import RegisterUserSchema
from src.infrastructure.repository.postgresql.user_repo import add_user, find_user

auth_router = APIRouter(prefix="/api/v1/auth", tags=["authorization"])


@auth_router.post("/register", status_code=status.HTTP_204_NO_CONTENT)
async def register_user(user: RegisterUserSchema, session: Annotated[AsyncSession, Depends(get_session)]) -> None:
    u = await find_user(session, user.username)
    if u is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="пользователь с таким именем уже существует")

    hashed_password = hash_password(user.password)
    u = UserORM(user_id=uuid4(), username=user.username, hashed_password=hashed_password)

    await add_user(session, user=u)
    await session.commit()
