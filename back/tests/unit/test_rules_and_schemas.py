from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from src.core.config import CONFIG
from src.core.exc import ExternalError
from src.domain.rules import TokenType, create_jwt, decode_jwt, get_current_time
from src.domain.schemas import ChatSchema, HistorySchema, LLMPromtSchema, RegisterUserSchema


@pytest.mark.parametrize(
    "payload",
    [
        {"exp": datetime.now(UTC) - timedelta(days=1)},
        {"exp": datetime.now(UTC) + timedelta(days=1)},
    ],
)
def test_rejects_expired_or_wrong_signature(payload: dict) -> None:
    token = jwt.encode(payload, "wrong-signing-key-that-is-long-enough", algorithm="HS256")

    with pytest.raises(ExternalError, match="невалидный jwt"):
        decode_jwt(token)


def test_rejects_expired_token_signed_with_correct_key() -> None:
    token = jwt.encode({"exp": datetime.now(UTC) - timedelta(seconds=1)}, CONFIG.jwt_secret, algorithm="HS256")

    with pytest.raises(ExternalError):
        decode_jwt(token)


@given(token=st.text(max_size=200).filter(lambda value: value.count(".") != 2))
def test_malformed_jwt_is_domain_error(token: str) -> None:
    with pytest.raises(ExternalError):
        decode_jwt(token)


@pytest.mark.parametrize(("token_type", "minutes"), [(TokenType.ACCESS, 5), (TokenType.REFRESH, 15)])
def test_token_expiration_window(token_type: TokenType, minutes: int) -> None:
    before = datetime.now(UTC)

    token, expires = create_jwt({"user_id": "alice"}, token_type=token_type)

    after = datetime.now(UTC)

    assert before + timedelta(minutes=minutes) <= expires <= after + timedelta(minutes=minutes)
    assert decode_jwt(token)["exp"] == int(expires.timestamp())


def test_current_time_is_aware_moscow_time() -> None:
    before = datetime.now(UTC)

    current = get_current_time()

    assert current.utcoffset() == timedelta(hours=3)
    assert before <= current.astimezone(UTC) <= datetime.now(UTC)


@settings(max_examples=30)
@given(username=st.text(min_size=4, max_size=20), password=st.text(min_size=5, max_size=30))
def test_registration_preserves_valid_credentials(username: str, password: str) -> None:
    user = RegisterUserSchema(username=username, password=password)

    assert user.username == username and user.password == password


@pytest.mark.parametrize(("field", "size"), [("username", 3), ("username", 21), ("password", 4), ("password", 31)])
def test_registration_rejects_outside_length_bounds(field: str, size: int) -> None:
    credentials = {"username": "alice", "password": "password"}
    credentials[field] = "a" * size

    with pytest.raises(ValidationError):
        RegisterUserSchema(**credentials)


@pytest.mark.parametrize("size", [0, 101])
def test_prompt_rejects_outside_length_bounds(size: int) -> None:
    with pytest.raises(ValidationError):
        LLMPromtSchema(message="x" * size)


@given(message=st.text(min_size=1, max_size=100))
def test_valid_prompt_is_not_modified(message: str) -> None:
    assert LLMPromtSchema(message=message).message == message


def test_chat_schema_rejects_long_name() -> None:
    with pytest.raises(ValidationError):
        ChatSchema(chat_id=uuid4(), name="x" * 31)


def test_history_serializes_timestamp_in_moscow_timezone() -> None:
    history = HistorySchema(user_request="question", llm_response="answer", llm_model="model", dialog_time=datetime(2026, 1, 1, tzinfo=UTC))

    assert history.model_dump(mode="json")["dialog_time"] == "2026-01-01T03:00:00+03:00"
