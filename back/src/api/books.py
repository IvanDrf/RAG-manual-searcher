from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.common_params import get_limit_and_offset
from src.api.dependencies import get_session
from src.api.limiter import limiter
from src.api.middleware import auth_middleware
from src.api.utils import handle_errors
from src.domain.schemas import BookSchema
from src.infrastructure.repository.postgresql.book_repo import find_books

books_router = APIRouter(prefix="/api/v1/books", tags=["books"], dependencies=[Depends(auth_middleware)])


@books_router.get("", status_code=status.HTTP_200_OK, description="Получить список книг, используемых для контекста")
@limiter.limit("60/minute")
@handle_errors
async def get_books(
    request: Request,
    limit_offset: Annotated[tuple[int, int], Depends(get_limit_and_offset)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[BookSchema]:
    limit, offset = limit_offset

    books = await find_books(session, limit=limit, offset=offset)
    if not books:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"не удалось найти книги с параметрами поиска {limit=}, {offset=}"
        )

    return [BookSchema(title=book.book_title) for book in books]
