from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import UserORM


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
