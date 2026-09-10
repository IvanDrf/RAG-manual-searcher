from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Final

from bcrypt import checkpw, hashpw
from jwt import InvalidTokenError, decode, encode

from src.core.config import CONFIG
from src.core.exc import ExternalError

MIN_USERNAME_LENGTH: Final[int] = 4
MAX_USERNAME_LENGTH: Final[int] = 20


MIN_PASSWORD_LENGTH: Final[int] = 5
MAX_PASSWORD_LENGTH: Final[int] = 30


_PASSWORD_SALT: Final[bytes] = CONFIG.app_password_salt.encode()

_JWT_SECRET: Final[str] = CONFIG.jwt_secret
_JWT_ACCESS_EXP: Final[timedelta] = timedelta(minutes=CONFIG.jwt_access_exp)
_JWT_REFRESH_EXP: Final[timedelta] = timedelta(minutes=CONFIG.jwt_refresh_exp)


class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"


def hash_password(password: str) -> str:
    return hashpw(password.encode(), _PASSWORD_SALT).decode()


def is_passwords_are_same(password: str, hashed_password: str) -> bool:
    return checkpw(password.encode(), hashed_password.encode())


class TokenType(Enum):
    ACCESS = "access"
    REFRESH = "refresh"


def create_jwt(payload: dict, *, token_type: TokenType) -> tuple[str, datetime]:
    payload["exp"] = datetime.now(UTC) + (_JWT_ACCESS_EXP if token_type == TokenType.ACCESS else _JWT_REFRESH_EXP)

    return encode(payload=payload, key=_JWT_SECRET, algorithm="HS256"), payload["exp"]


def decode_jwt(token: str) -> dict:
    try:
        return decode(jwt=token, key=_JWT_SECRET, algorithms=["HS256"])
    except InvalidTokenError:
        raise ExternalError("невалидный jwt токен")
