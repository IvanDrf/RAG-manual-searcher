from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.rules import MAX_PASSWORD_LENGTH, MAX_PROMT_LENGTH, MAX_USERNAME_LENGTH, MIN_PASSWORD_LENGTH, MIN_USERNAME_LENGTH, UserRole


class Username(BaseModel):
    username: str = Field(min_length=MIN_USERNAME_LENGTH, max_length=MAX_USERNAME_LENGTH)


class Password(BaseModel):
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)


class RegisterUserSchema(Username, Password):
    pass


class LoginUserSchema(RegisterUserSchema):
    pass


class UserInfoSchema(BaseModel):
    user_id: UUID
    user_role: UserRole


class UserForAdminSchema(Username):
    user_id: UUID
    user_role: UserRole


class ChangeUserRoleSchema(Username):
    user_role: UserRole


class BlockUserSchema(Username):
    pass


class LLMPromtSchema(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_PROMT_LENGTH)


class LLMResponseSchema(BaseModel):
    model: str
    response: str
