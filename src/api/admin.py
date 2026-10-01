from typing import Annotated, Final

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_redis, get_session
from src.api.middleware import admin_middleware
from src.api.utils import handle_errors
from src.domain.rules import JWT_ACCESS_EXP, UserRole
from src.domain.schemas import BlockUserSchema, ChangeUserRoleSchema, UserForAdminSchema
from src.infrastructure.repository.postgresql.user_repo import find_user_by_username, find_users
from src.infrastructure.repository.redis.block_repo import add_user_in_block_list, remove_user_from_block_list

admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin"], dependencies=[Depends(admin_middleware)])


MIN_LIMIT: Final[int] = 1
MAX_LIMIT: Final[int] = 40

MIN_OFFSET: Final[int] = 0


def limit_and_offset(
    limit: Annotated[int, Query(ge=MIN_LIMIT, le=MAX_LIMIT)], offset: Annotated[int, Query(ge=MIN_OFFSET)]
) -> tuple[int, int]:
    return limit, offset


@admin_router.get("/users", status_code=status.HTTP_200_OK, description="Получение списка пользователей для админа")
@handle_errors
async def get_users(
    limit_offset: Annotated[tuple[int, int], Depends(limit_and_offset)],
    session: Annotated[AsyncSession, Depends(get_session)],
    user_role: Annotated[UserRole | None, Query()] = None,
) -> list[UserForAdminSchema]:
    limit, offset = limit_offset

    users = await find_users(session, limit=limit, offset=offset, user_role=user_role)
    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"не удалось найти пользователей с параметарми {limit=}, {offset=}"
        )

    return [UserForAdminSchema(user_id=user.user_id, username=user.username, user_role=user.user_role) for user in users]


@admin_router.patch("/users/role", status_code=status.HTTP_204_NO_CONTENT, description="Изменить роль пользователю")
@handle_errors
async def change_user_role(
    user: ChangeUserRoleSchema,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    u = await find_user_by_username(session, user.username, block=True)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"не удалось найти пользователля с username{user.username}")

    u.user_role = user.user_role
    await session.commit()


@admin_router.post("/users/block", status_code=status.HTTP_204_NO_CONTENT, description="Заблокировать пользователя")
@handle_errors
async def block_user(
    user: BlockUserSchema, session: Annotated[AsyncSession, Depends(get_session)], redis: Annotated[Redis, Depends(get_redis)]
) -> None:
    u = await find_user_by_username(session, user.username)
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"не удалось найти пользователля с username{user.username}")

    if u.user_role == UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="невозможно заблокировать администратора")

    u.is_blocked = True
    await add_user_in_block_list(redis, str(u.user_id), ttl=JWT_ACCESS_EXP)
    await session.commit()


@admin_router.delete("/users/block", status_code=status.HTTP_204_NO_CONTENT, description="Разблокировать пользователя")
@handle_errors
async def unblock_user(
    user: BlockUserSchema, session: Annotated[AsyncSession, Depends(get_session)], redis: Annotated[Redis, Depends(get_redis)]
) -> None:
    u = await find_user_by_username(session, user.username)
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"не удалось найти пользователля с username{user.username}")

    u.is_blocked = False
    await remove_user_from_block_list(redis, str(u.user_id))
    await session.commit()
