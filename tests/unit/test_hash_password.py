from hypothesis import given, settings
from hypothesis import strategies as st

from src.domain.rules import hash_password, is_passwords_are_same


@settings(max_examples=5, deadline=None)
@given(password=st.text())
def test_hash_password(password: str) -> None:
    hashed_password = hash_password(password)

    assert len(hashed_password) > 0 and hashed_password != password

    assert is_passwords_are_same(password, hashed_password) is True
    assert is_passwords_are_same(password[::-1] + "1", hashed_password) is False
