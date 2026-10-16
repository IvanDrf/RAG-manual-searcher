from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import ChatORM, HistoryORM


async def add_history(session: AsyncSession, history: HistoryORM, commit: bool = False) -> None:
    session.add(history)

    if commit:
        await session.commit()


async def find_history_for_user(
    session: AsyncSession,
    *,
    user_id: UUID,
    chat_id: UUID,
    limit: int,
    offset: int,
) -> list[HistoryORM] | None:
    query = (
        select(HistoryORM)
        .join(ChatORM, ChatORM.chat_id == HistoryORM.chat_id)
        .where(and_(ChatORM.user_id == user_id, HistoryORM.chat_id == chat_id))
        .order_by(HistoryORM.dialog_time.desc())
        .limit(limit)
        .offset(offset)
    )

    res = await session.execute(query)
    res = res.scalars().all()

    return list(res) if res else None
