from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_URL: str

    JWT_ALGORITHM: str
    JWT_SECRET: str

    REDIS_HOST: str
    REDIS_PORT: int

    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file=".env.local", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_config():
    return Config()  # type: ignore
