from uuid import UUID

from sqlalchemy import UUID as SqlUUID
from sqlalchemy import VARCHAR, ForeignKey, Text, UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

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
    content: Mapped[str] = mapped_column(Text, nullable=False)


class ChunkToBookORM(BaseORM):
    __tablename__ = "chunks_to_books"

    record_id: Mapped[UUID] = mapped_column(SqlUUID, primary_key=True)

    chunk_id: Mapped[UUID] = mapped_column(ForeignKey("chunks.chunk_id", ondelete="CASCADE"), nullable=False)
    book_id: Mapped[UUID] = mapped_column(ForeignKey("books.book_id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (UniqueConstraint("chunk_id", "book_id", name="unique_chunk_to_book"),)
