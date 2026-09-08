from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Final

from bcrypt import hashpw
from jwt import encode

from src.core.config import CONFIG

MIN_USERNAME_LENGTH: Final[int] = 4
MAX_USERNAME_LENGTH: Final[int] = 20


MIN_PASSWORD_LENGTH: Final[int] = 5
MAX_PASSWORD_LENGTH: Final[int] = 30


_PASSWORD_SALT: Final[bytes] = CONFIG.app_password_salt.encode()

_JWT_SECRET: Final[str] = CONFIG.jwt_secret
_JWT_ACCESS_EXP: Final[timedelta] = timedelta(minutes=CONFIG.jwt_access_exp)
_JWT_REFRESH_EXP: Final[timedelta] = timedelta(minutes=CONFIG.jwt_refresh_exp)


def hash_password(password: str) -> str:
    return hashpw(password.encode(), _PASSWORD_SALT).decode()


class TokenType(Enum):
    ACCESS = "access"
    REFRESH = "refresh"


def create_jwt(payload: dict, *, token_type: TokenType) -> str:
    payload["exp"] = datetime.now(UTC) + (_JWT_ACCESS_EXP if token_type == TokenType.ACCESS else _JWT_REFRESH_EXP)

    return encode(payload=payload, key=_JWT_SECRET, algorithm="HS256")
