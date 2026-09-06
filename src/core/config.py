from typing import Final

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class PostgreSQLConfig(BaseConfig):
    postgres_host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, gt=0, validation_alias="POSTGRES_PORT")

    postgres_user: str = Field(default="user", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(default="password", validation_alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="rag_search", validation_alias="POSTGRES_DB")

    @property
    def postgres_dsn(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


class Config(PostgreSQLConfig):
    pass


CONFIG: Final[Config] = Config()
