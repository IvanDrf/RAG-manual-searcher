from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.rules import MAX_PASSWORD_LENGTH, MAX_USERNAME_LENGTH, MIN_PASSWORD_LENGTH, MIN_USERNAME_LENGTH, UserRole


class RegisterUserSchema(BaseModel):
    username: str = Field(min_length=MIN_USERNAME_LENGTH, max_length=MAX_USERNAME_LENGTH)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)


class LoginUserSchema(RegisterUserSchema):
    pass


class UserInfoSchema(BaseModel):
    user_id: UUID
    user_role: UserRole
