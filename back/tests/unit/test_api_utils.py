from datetime import UTC, datetime, timedelta
from http.cookies import SimpleCookie

import pytest
from fastapi import HTTPException, Response
from httpx import ConnectError, ReadTimeout
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from src.api.utils import create_jwt_tokens, handle_errors, set_jwt_in_cookies
from src.core.exc import ExternalError
from src.domain.rules import decode_jwt


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (SQLAlchemyError("private db details"), 500),
        (RedisError("private redis details"), 500),
        (ConnectionRefusedError("private connection details"), 500),
        (ExternalError("invalid input"), 400),
        (TimeoutError("timeout"), 408),
        (ReadTimeout("timeout"), 408),
        (ConnectError("connection"), 408),
    ],
)
async def test_error_mapping_hides_internal_details(error: Exception, status_code: int) -> None:
    @handle_errors
    async def endpoint() -> None:
        raise error

    with pytest.raises(HTTPException) as caught:
        await endpoint()

    assert caught.value.status_code == status_code
    assert "private" not in caught.value.detail

    if status_code == 400:
        assert caught.value.detail == "invalid input"


async def test_http_errors_pass_through_unchanged() -> None:
    original = HTTPException(status_code=403, detail="forbidden")

    @handle_errors
    async def endpoint() -> None:
        raise original

    with pytest.raises(HTTPException) as caught:
        await endpoint()

    assert caught.value is original


async def test_decorator_preserves_result_arguments_and_name() -> None:
    @handle_errors
    async def endpoint(value: int, *, increment: int) -> int:
        return value + increment

    assert await endpoint(2, increment=3) == 5
    assert endpoint.__name__ == "endpoint"


def test_token_pair_has_distinct_expirations() -> None:
    access, refresh = create_jwt_tokens({"user_id": "alice", "user_role": "user"})

    assert access[0] != refresh[0] and access[1] < refresh[1]
    assert decode_jwt(access[0])["user_id"] == decode_jwt(refresh[0])["user_id"] == "alice"


def test_session_cookies_have_security_flags_and_expiration() -> None:
    response = Response()
    expires = datetime.now(UTC) + timedelta(minutes=5)

    set_jwt_in_cookies(response, "access", expires, "refresh", expires)

    cookies = SimpleCookie()
    for header in response.headers.getlist("set-cookie"):
        cookies.load(header)

    assert set(cookies) == {"access-token", "refresh-token"}

    for name, value in [("access-token", "access"), ("refresh-token", "refresh")]:
        cookie = cookies[name]

        assert cookie.value == value
        assert cookie["httponly"] and cookie["secure"]
        assert cookie["samesite"] == "lax" and cookie["path"] == "/"
        assert cookie["expires"]
