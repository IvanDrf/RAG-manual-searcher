from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import UUID as SaUUID
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import Boolean, DateTime, String, Time
from clickhouse_connect.cc_sqlalchemy.ddl.tableengine import MergeTree
from sqlalchemy import Column
from sqlalchemy.orm import DeclarativeBase

# TODO: выбрать движок для таблицы, пока что Merge Tree


class BaseORM(DeclarativeBase):
    pass


class LLMResponseORM(BaseORM):
    __tablename__ = "llm_statistics"
    __table_args__ = (MergeTree(order_by=["response_id", "responsed_at"]),)

    response_id = Column(SaUUID, primary_key=True)
    model = Column(String, nullable=False)
    promt = Column(String, nullable=False)

    is_success = Column(Boolean, nullable=False)
    is_user_liked = Column(Boolean, default=None, nullable=True)
    is_found_context = Column(Boolean, default=None, nullable=True)

    error_type = Column(String, default=None, nullable=True)
    error_message = Column(String, default=None, nullable=None)

    reasoning_time = Column(Time, nullable=False)
    responsed_at = Column(DateTime, nullable=False)
