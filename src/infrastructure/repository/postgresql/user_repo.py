from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import UserORM


async def register_user(session: AsyncSession, user: UserORM) -> None:
    pass
