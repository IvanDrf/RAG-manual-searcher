from uuid import UUID

from hypothesis import given, settings
from hypothesis import strategies as st

from src.domain.rules import TokenType, UserRole, create_jwt, decode_jwt


@settings(max_examples=10, deadline=None)
@given(user_id=st.uuids(version=4), role=st.sampled_from(UserRole))
def test_create_jwt(user_id: UUID, role: UserRole) -> None:
    id_str = str(user_id)
    payload = {"user_id": id_str, "user_role": role.value}

    access_token, access_exp = create_jwt(payload, token_type=TokenType.ACCESS)
    refresh_token, refresh_exp = create_jwt(payload, token_type=TokenType.REFRESH)

    assert access_token and refresh_token
    assert access_token != refresh_token
    assert refresh_exp > access_exp

    validate_jwt_payload(access_token, payload)
    validate_jwt_payload(refresh_token, payload)


def validate_jwt_payload(token: str, payload: dict) -> None:
    decoded_payload = decode_jwt(token)

    assert decoded_payload["user_id"] == payload["user_id"]
    assert decoded_payload["user_role"] == payload["user_role"]
