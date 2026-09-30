from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import HistoryORM


async def add_history(session: AsyncSession, history: HistoryORM, commit: bool = False) -> None:
    session.add(history)

    if commit:
        await session.commit()
