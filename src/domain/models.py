from uuid import UUID

from sqlalchemy import UUID as SqlUUID
from sqlalchemy import VARCHAR, Boolean, ForeignKey, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.domain.rules import MAX_PASSWORD_LENGTH, MAX_USERNAME_LENGTH, UserRole

MAX_BOOK_NAME_LENGTH = 100


class BaseORM(DeclarativeBase, AsyncAttrs):
    pass


class BookORM(BaseORM):
    __tablename__ = "books"

    book_id: Mapped[UUID] = mapped_column(SqlUUID, primary_key=True)
    book_title: Mapped[str] = mapped_column(VARCHAR(MAX_BOOK_NAME_LENGTH), nullable=False)


class ChunkORM(BaseORM):
    __tablename__ = "chunks"

    chunk_id: Mapped[UUID] = mapped_column(SqlUUID, primary_key=True, index=True)
    book_id: Mapped[UUID] = mapped_column(ForeignKey("books.book_id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)


class UserORM(BaseORM):
    __tablename__ = "users"

    user_id: Mapped[UUID] = mapped_column(SqlUUID, primary_key=True)

    username: Mapped[str] = mapped_column(VARCHAR(length=MAX_USERNAME_LENGTH), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(VARCHAR(length=2 * MAX_PASSWORD_LENGTH), nullable=False)
    user_role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole, name="UserRoles"), default=UserRole.USER, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False, server_default="false")
