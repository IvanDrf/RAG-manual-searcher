from typing import Final, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LoggerLevel = Literal["debug", "info", "warning", "error", "critical"]


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class AppConfig(BaseConfig):
    app_host: str = Field(default="localhost", validation_alias="APP_HOST")
    app_port: int = Field(default=8080, gt=1000, lt=50000, validation_alias="APP_PORT")

    app_loger_level: LoggerLevel = Field(default="info", validation_alias="APP_LOGGER_LEVEL")
    app_password_salt: str = Field(default="", min_length=1, validation_alias="APP_PASSWORD_SALT")


class JWTConfig(BaseConfig):
    jwt_secret: str = Field(default="", min_length=1, validation_alias="JWT_SECRET")
    jwt_access_exp: int = Field(default=5, gt=0, lt=60, validation_alias="JWT_ACCESS_EXP")
    jwt_refresh_exp: int = Field(default=15, gt=0, le=1440, validation_alias="JWT_REFRESH_EXP")


class PostgreSQLConfig(BaseConfig):
    postgres_host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, gt=0, validation_alias="POSTGRES_PORT")

    postgres_user: str = Field(default="user", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(default="password", validation_alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="rag_search", validation_alias="POSTGRES_DB")

    @property
    def postgres_dsn(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


class LLMConfig(BaseConfig):
    llm_url: str = Field(default="", min_length=1, validation_alias="LLM_URL")
    llm_timeout: int = Field(default=10, gt=0, validation_alias="LLM_REQUEST_TIMEOUT")
    llm_api_key: str = Field(default="", validation_alias="LLM_API_KEY")


class Config(AppConfig, PostgreSQLConfig, JWTConfig, LLMConfig):
    pass


CONFIG: Final[Config] = Config()
