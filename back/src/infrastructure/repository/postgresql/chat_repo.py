from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import ChatORM


async def find_chats_for_user(session: AsyncSession, *, user_id: UUID, limit: int, offset: int) -> list[ChatORM] | None:
    query = select(ChatORM).where(ChatORM.user_id == user_id).order_by(ChatORM.edited_at.desc()).limit(limit).offset(offset)

    res = await session.execute(query)
    res = res.scalars().all()

    return list(res) if res else None


async def find_chat_for_user(session: AsyncSession, *, user_id: UUID, chat_id: UUID, block: bool = False) -> ChatORM | None:
    query = select(ChatORM).where(and_(ChatORM.chat_id == chat_id, ChatORM.user_id == user_id))

    if block:
        query = query.with_for_update()

    res = await session.execute(query)
    return res.scalar_one_or_none()


async def add_chat(session: AsyncSession, chat: ChatORM, commit: bool = False) -> None:
    session.add(chat)

    if commit:
        await session.commit()


async def delete_chat(session: AsyncSession, chat: ChatORM, commit: bool = False) -> None:
    await session.delete(chat)

    if commit:
        await session.commit()
