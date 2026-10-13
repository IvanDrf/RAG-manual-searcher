from datetime import datetime
from uuid import UUID

import numpy as np
from pgvector.sqlalchemy import Vector
from sqlalchemy import TIMESTAMP, VARCHAR, Boolean, ForeignKey, Text
from sqlalchemy import UUID as SqlUUID
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.core.config import CONFIG
from src.domain.rules import MAX_PASSWORD_LENGTH, MAX_USERNAME_LENGTH, UserRole, get_current_time

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
    embedding: Mapped[np.ndarray] = mapped_column(Vector(dim=CONFIG.app_embedding_size))


class UserORM(BaseORM):
    __tablename__ = "users"

    user_id: Mapped[UUID] = mapped_column(SqlUUID, primary_key=True)

    username: Mapped[str] = mapped_column(VARCHAR(length=MAX_USERNAME_LENGTH), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(VARCHAR(length=2 * MAX_PASSWORD_LENGTH), nullable=False)
    user_role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole, name="UserRoles"), default=UserRole.USER, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False, server_default="false")


class ChatORM(BaseORM):
    __tablename__ = "chats"

    chat_id: Mapped[UUID] = mapped_column(SqlUUID, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    edited_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=get_current_time, nullable=False)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))


class HistoryORM(BaseORM):
    __tablename__ = "histories"

    record_id: Mapped[UUID] = mapped_column(SqlUUID, primary_key=True)
    chat_id: Mapped[UUID] = mapped_column(ForeignKey("chats.chat_id", ondelete="CASCADE"), nullable=False, index=True)

    user_request: Mapped[str] = mapped_column(Text, nullable=False)
    llm_response: Mapped[str] = mapped_column(Text, nullable=False)
    llm_model: Mapped[str] = mapped_column(Text, nullable=False)

    dialog_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=get_current_time)
