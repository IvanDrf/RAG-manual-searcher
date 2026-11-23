import socket
from collections.abc import AsyncIterator
from typing import cast
from unittest.mock import MagicMock, create_autospec

import pytest
from fakeredis import FakeAsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*args: object, **kwargs: object) -> None:
        raise AssertionError("Unit-тест не должен открывать сетевое соединение")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


@pytest.fixture
def session_mock() -> MagicMock:
    session_mock = create_autospec(AsyncSession, instance=True)

    session_mock.execute.return_value = MagicMock()

    return session_mock


@pytest.fixture
def session(session_mock: MagicMock) -> AsyncSession:
    return cast(AsyncSession, session_mock)


@pytest.fixture
async def redis_client() -> AsyncIterator[FakeAsyncRedis]:
    async with FakeAsyncRedis() as client:
        yield client
