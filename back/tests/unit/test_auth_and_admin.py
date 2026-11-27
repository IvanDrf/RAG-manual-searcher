from datetime import timedelta
from http.cookies import SimpleCookie
from inspect import unwrap
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fakeredis import FakeAsyncRedis
from fastapi import HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api import admin, auth, middleware
from src.domain.models.postgresql import UserORM
from src.domain.rules import TokenType, UserRole, create_jwt, decode_jwt, hash_password
from src.domain.schemas import BlockUserSchema, ChangeUserRoleSchema, LoginUserSchema, RegisterUserSchema
from src.infrastructure.repository.redis.block_repo import add_user_in_block_list, is_user_in_block_list


def token(**payload: str) -> str:
    return create_jwt(payload, token_type=TokenType.ACCESS)[0]


@pytest.mark.parametrize(("role", "expected"), [("admin", None), ("user", 403), ("unknown", 401)])
async def test_admin_requires_admin_role(role: str, expected: int | None) -> None:
    access_token = token(user_role=role)

    if expected is None:
        assert await middleware.admin_middleware(access_token) is None
    else:
        with pytest.raises(HTTPException) as caught:
            await middleware.admin_middleware(access_token)

        assert caught.value.status_code == expected


@pytest.mark.parametrize("guard", [middleware.admin_middleware, middleware.auth_middleware])
async def test_missing_cookie_is_unauthorized(guard, redis_client: FakeAsyncRedis) -> None:
    kwargs = {"redis": redis_client} if guard is middleware.auth_middleware else {}

    with pytest.raises(HTTPException) as caught:
        await guard(**kwargs)

    assert caught.value.status_code == 401


async def test_auth_returns_uuid_and_rejects_blocked_user(redis_client: FakeAsyncRedis) -> None:
    user_id = uuid4()
    access_token = token(user_id=str(user_id), user_role="user")

    assert await middleware.auth_middleware(redis_client, access_token) == user_id

    await add_user_in_block_list(redis_client, str(user_id), timedelta(minutes=5))

    with pytest.raises(HTTPException) as caught:
        await middleware.auth_middleware(redis_client, access_token)

    assert caught.value.status_code == 403


@pytest.mark.parametrize("payload", [{}, {"user_id": "invalid-uuid"}])
async def test_auth_rejects_invalid_identity(redis_client: FakeAsyncRedis, payload: dict) -> None:
    with pytest.raises(HTTPException) as caught:
        await middleware.auth_middleware(redis_client, token(**payload))

    assert caught.value.status_code == 401


async def test_register_hashes_password_and_commits(
    session: AsyncSession, session_mock: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(auth, "find_user_by_username", AsyncMock(return_value=None))
    user = RegisterUserSchema(username="alice", password="secret")
    response = Response()

    await unwrap(auth.register_user)(request=None, user=user, response=response, session=session)

    stored = session_mock.add.call_args.args[0]
    assert stored.username == "alice" and stored.hashed_password != "secret"
    assert stored.user_role is UserRole.USER
    session_mock.commit.assert_awaited_once()
    assert len(response.headers.getlist("set-cookie")) == 2


async def test_duplicate_registration_does_not_write(
    session: AsyncSession, session_mock: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(auth, "find_user_by_username", AsyncMock(return_value=UserORM()))

    with pytest.raises(HTTPException) as caught:
        await unwrap(auth.register_user)(None, RegisterUserSchema(username="alice", password="secret"), Response(), session)

    assert caught.value.status_code == 409
    session_mock.add.assert_not_called()
    session_mock.commit.assert_not_awaited()


@pytest.mark.parametrize(
    ("exists", "password", "blocked", "status"), [(False, "secret", False, 401), (True, "wrong", False, 401), (True, "secret", True, 403)]
)
async def test_login_failure_does_not_commit(
    session: AsyncSession,
    session_mock: MagicMock,
    redis_client: FakeAsyncRedis,
    monkeypatch: pytest.MonkeyPatch,
    exists: bool,
    password: str,
    blocked: bool,
    status: int,
) -> None:
    user = UserORM(user_id=uuid4(), hashed_password=hash_password("secret"), user_role=UserRole.USER, is_blocked=blocked)
    monkeypatch.setattr(auth, "find_user_by_username", AsyncMock(return_value=user if exists else None))

    with pytest.raises(HTTPException) as caught:
        await unwrap(auth.login_user)(None, LoginUserSchema(username="alice", password=password), Response(), session, redis_client)

    assert caught.value.status_code == status
    session_mock.commit.assert_not_awaited()


async def test_login_removes_stale_role_block_and_sets_cookies(
    session: AsyncSession, session_mock: MagicMock, redis_client: FakeAsyncRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = UserORM(user_id=uuid4(), hashed_password=hash_password("secret"), user_role=UserRole.USER, is_blocked=False)
    monkeypatch.setattr(auth, "find_user_by_username", AsyncMock(return_value=user))
    response = Response()
    await add_user_in_block_list(redis_client, str(user.user_id), timedelta(minutes=5))

    await unwrap(auth.login_user)(None, LoginUserSchema(username="alice", password="secret"), response, session, redis_client)

    assert not await is_user_in_block_list(redis_client, str(user.user_id))
    assert len(response.headers.getlist("set-cookie")) == 2


async def test_refresh_uses_current_database_role(session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid4()
    user = UserORM(user_id=user_id, user_role=UserRole.ADMIN, is_blocked=False)
    monkeypatch.setattr(auth, "find_user_by_user_id", AsyncMock(return_value=user))
    response = Response()

    await unwrap(auth.refresh_tokens)(None, token(user_id=str(user_id), user_role="user"), session, response)

    cookies = SimpleCookie()
    for header in response.headers.getlist("set-cookie"):
        cookies.load(header)

    assert decode_jwt(cookies["access-token"].value)["user_role"] == "admin"


@pytest.mark.parametrize(("exists", "blocked", "expected"), [(False, False, 404), (True, True, 403)])
async def test_refresh_rejects_deleted_or_blocked_user(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch, exists: bool, blocked: bool, expected: int
) -> None:
    user_id = uuid4()
    user = UserORM(user_id=user_id, user_role=UserRole.USER, is_blocked=blocked)
    monkeypatch.setattr(auth, "find_user_by_user_id", AsyncMock(return_value=user if exists else None))
    response = Response()

    with pytest.raises(HTTPException) as caught:
        await unwrap(auth.refresh_tokens)(None, token(user_id=str(user_id), user_role="user"), session, response)

    assert caught.value.status_code == expected
    assert not response.headers.getlist("set-cookie")


@pytest.mark.parametrize("payload", [{}, {"user_id": "invalid", "user_role": "user"}, {"user_id": str(uuid4()), "user_role": "invalid"}])
async def test_me_rejects_invalid_claims(payload: dict) -> None:
    with pytest.raises(HTTPException) as caught:
        await unwrap(auth.get_user_info)(None, Response(), token(**payload))

    assert caught.value.status_code == 401


@pytest.mark.parametrize("role", [UserRole.USER, UserRole.ADMIN])
async def test_blocking_user_enforces_admin_protection(
    session: AsyncSession, session_mock: MagicMock, redis_client: FakeAsyncRedis, monkeypatch: pytest.MonkeyPatch, role: UserRole
) -> None:
    user = UserORM(user_id=uuid4(), username="alice", user_role=role, is_blocked=False)
    monkeypatch.setattr(admin, "find_user_by_username", AsyncMock(return_value=user))

    if role is UserRole.ADMIN:
        with pytest.raises(HTTPException) as caught:
            await unwrap(admin.block_user)(None, Response(), BlockUserSchema(username="alice"), session, redis_client)

        assert caught.value.status_code == 403
        session_mock.commit.assert_not_awaited()
        assert not await is_user_in_block_list(redis_client, str(user.user_id))
    else:
        await unwrap(admin.block_user)(None, Response(), BlockUserSchema(username="alice"), session, redis_client)

        assert user.is_blocked and await is_user_in_block_list(redis_client, str(user.user_id))
        session_mock.commit.assert_awaited_once()


async def test_role_change_invalidates_existing_sessions(
    session: AsyncSession, session_mock: MagicMock, redis_client: FakeAsyncRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = UserORM(user_id=uuid4(), username="alice", user_role=UserRole.USER)
    find = AsyncMock(return_value=user)
    monkeypatch.setattr(admin, "find_user_by_username", find)

    await unwrap(admin.change_user_role)(
        None, Response(), ChangeUserRoleSchema(username="alice", user_role=UserRole.ADMIN), redis_client, session
    )

    assert user.user_role is UserRole.ADMIN
    assert await is_user_in_block_list(redis_client, str(user.user_id))
    find.assert_awaited_once_with(session, "alice", block=True)
    session_mock.commit.assert_awaited_once()


async def test_unblock_clears_database_and_redis_flags(
    session: AsyncSession, session_mock: MagicMock, redis_client: FakeAsyncRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = UserORM(user_id=uuid4(), is_blocked=True)
    monkeypatch.setattr(admin, "find_user_by_username", AsyncMock(return_value=user))

    await add_user_in_block_list(redis_client, str(user.user_id), timedelta(minutes=5))

    await unwrap(admin.unblock_user)(None, Response(), BlockUserSchema(username="alice"), session, redis_client)

    assert not user.is_blocked and not await is_user_in_block_list(redis_client, str(user.user_id))
    session_mock.commit.assert_awaited_once()


@pytest.mark.parametrize("action", ["block_user", "unblock_user", "change_user_role"])
async def test_admin_missing_user_does_not_write(
    session: AsyncSession, session_mock: MagicMock, redis_client: FakeAsyncRedis, monkeypatch: pytest.MonkeyPatch, action: str
) -> None:
    monkeypatch.setattr(admin, "find_user_by_username", AsyncMock(return_value=None))
    user = (
        ChangeUserRoleSchema(username="alice", user_role=UserRole.ADMIN)
        if action == "change_user_role"
        else BlockUserSchema(username="alice")
    )

    with pytest.raises(HTTPException) as caught:
        await unwrap(getattr(admin, action))(request=None, response=Response(), user=user, session=session, redis=redis_client)

    assert caught.value.status_code == 404
    session_mock.commit.assert_not_awaited()
    assert await redis_client.dbsize() == 0
