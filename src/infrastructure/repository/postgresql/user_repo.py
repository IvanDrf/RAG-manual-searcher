from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import UserORM
from src.domain.rules import UserRole


async def add_user(session: AsyncSession, user: UserORM, commit: bool = False) -> None:
    session.add(user)

    if commit:
        await session.commit()


async def find_user(session: AsyncSession, username: str, block: bool = False) -> UserORM | None:
    query = select(UserORM).where(UserORM.username == username).limit(1)

    if block:
        query = query.with_for_update()

    res = await session.execute(query)
    return res.scalar_one_or_none()


async def find_users(
    session: AsyncSession, *, limit: int, offset: int, user_role: UserRole | None = None, block: bool = False
) -> list[UserORM]:
    query = select(UserORM).limit(limit).offset(offset)

    if user_role:
        query = query.where(UserORM.user_role == user_role)

    if block:
        query = query.order_by(UserORM.user_id).with_for_update()

    res = await session.execute(query)
    return list(res.scalars().all())
