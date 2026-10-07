from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import HistoryORM


async def add_history(session: AsyncSession, history: HistoryORM, commit: bool = False) -> None:
    session.add(history)

    if commit:
        await session.commit()


async def find_history_for_user(
    session: AsyncSession,
    user_id: UUID,
    *,
    limit: int,
    offset: int,
    order_by: Literal["time"] | None = None,
) -> list[HistoryORM] | None:
    query = select(HistoryORM).where(HistoryORM.user_id == user_id).limit(limit).offset(offset)

    if order_by:
        query = query.order_by(HistoryORM.dialog_time)

    res = await session.execute(query)
    res = res.scalars().all()

    return list(res) if res else None
