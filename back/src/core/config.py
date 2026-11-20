"""Настройки backend и его зависимостей."""

from pathlib import Path
from typing import Final, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LoggerLevel = Literal["debug", "info", "warning", "error", "critical"]


class BaseConfig(BaseSettings):
    """Прочитать окружение и общий файл .env."""

    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")


class AppConfig(BaseConfig):
    """Параметры HTTP-приложения и модели данных."""

    app_host: str = Field(default="localhost", validation_alias="APP_HOST")
    app_port: int = Field(default=8080, gt=1000, lt=50000, validation_alias="APP_PORT")

    app_loger_level: LoggerLevel = Field(default="info", validation_alias="APP_LOGGER_LEVEL")
    app_password_salt: str = Field(default="", min_length=1, validation_alias="APP_PASSWORD_SALT")
    app_embedding_size: int = Field(default=0, gt=0, validation_alias="APP_EMBEDDING_SIZE")


class BooksConfig(BaseConfig):
    """Параметры импорта учебных материалов."""

    books_dir: Path = Field(default=Path("./student_book_pdf"), validation_alias="BOOKS_DIR")
    books_ext: str = Field(default=".pdf", validation_alias="BOOKS_EXT")


class JWTConfig(BaseConfig):
    """Подпись и сроки жизни токенов."""

    jwt_secret: str = Field(default="", min_length=1, validation_alias="JWT_SECRET")
    jwt_access_exp: int = Field(default=5, gt=0, lt=60, validation_alias="JWT_ACCESS_EXP")
    jwt_refresh_exp: int = Field(default=15, gt=0, le=1440, validation_alias="JWT_REFRESH_EXP")


class PostgreSQLConfig(BaseConfig):
    """Подключение к PostgreSQL."""

    postgres_host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, gt=0, validation_alias="POSTGRES_PORT")

    postgres_user: str = Field(default="user", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(default="password", validation_alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="rag_search", validation_alias="POSTGRES_DB")

    @property
    def postgres_dsn(self) -> str:
        """Сформировать строку подключения асинхронного драйвера."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


class RedisConfig(BaseConfig):
    """Подключение к Redis."""

    redis_host: str = Field(default="localhost", validation_alias="REDIS_HOST")
    redis_port: int = Field(default=6379, validation_alias="REDIS_PORT")
    redis_db: int = Field(default=0, ge=0, validation_alias="REDIS_DB")


class LLMConfig(BaseConfig):
    """Адрес, модель и время ожидания Ollama."""

    llm_url: str = Field(
        default="http://127.0.0.1:11434/v1/chat/completions",
        min_length=1,
        validation_alias="LLM_URL",
    )
    llm_model: str = Field(default="qwen2.5:3b", min_length=1, validation_alias="LLM_MODEL")
    llm_timeout: int = Field(default=120, gt=0, validation_alias="LLM_REQUEST_TIMEOUT")
    llm_api_key: str = Field(default="", validation_alias="LLM_API_KEY")


class Config(  # pylint: disable=too-many-ancestors
    AppConfig, BooksConfig, PostgreSQLConfig, RedisConfig, JWTConfig, LLMConfig
):
    """Объединённые настройки backend."""


CONFIG: Final[Config] = Config()
