from collections.abc import AsyncIterator
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, Request, Response
from limits.storage import MemoryStorage
from limits.strategies import FixedWindowRateLimiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.auth import auth_router
from src.api.limiter import limiter
from src.domain.rules import TokenType, create_jwt


def handle_rate_limit(request: Request, error: Exception) -> Response:
    assert isinstance(error, RateLimitExceeded)
    return _rate_limit_exceeded_handler(request, error)


@pytest.fixture
async def auth_client(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[httpx.AsyncClient]:
    storage = MemoryStorage()
    monkeypatch.setattr(limiter, "_storage", storage)
    monkeypatch.setattr(limiter, "_limiter", FixedWindowRateLimiter(storage))

    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, handle_rate_limit)
    app.include_router(auth_router)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test.invalid") as client:
        yield client


async def test_me_serializes_identity_and_injects_rate_limit_headers(auth_client: httpx.AsyncClient) -> None:
    user_id = str(uuid4())
    token, _ = create_jwt({"user_id": user_id, "user_role": "user"}, token_type=TokenType.ACCESS)
    auth_client.cookies.set("access-token", token)

    response = await auth_client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json() == {"user_id": user_id, "user_role": "user"}
    assert response.headers["x-ratelimit-limit"] == "60"
    assert response.headers["x-ratelimit-remaining"] == "59"


async def test_me_enforces_rate_limit(auth_client: httpx.AsyncClient) -> None:
    token, _ = create_jwt({"user_id": str(uuid4()), "user_role": "user"}, token_type=TokenType.ACCESS)
    auth_client.cookies.set("access-token", token)

    for _ in range(60):
        assert (await auth_client.get("/api/v1/auth/me")).status_code == 200

    response = await auth_client.get("/api/v1/auth/me")

    assert response.status_code == 429
    assert int(response.headers["retry-after"]) >= 0


async def test_registration_invalid_input_does_not_reach_database(auth_client: httpx.AsyncClient) -> None:
    response = await auth_client.post("/api/v1/auth/register", json={"username": "ab", "password": "123"})

    assert response.status_code == 422
