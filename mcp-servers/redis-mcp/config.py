"""
Redis MCP Server Configuration
Load Redis credentials from environment variables.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class RedisSettings(BaseSettings):
    """Redis connection settings."""

    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")
    redis_db: int = Field(default=0, alias="REDIS_DB")

    @property
    def dsn(self) -> str:
        """Redis connection string."""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    class Config:
        env_file = "/home/philip/nexus/.env"
        env_file_encoding = "utf-8"
        extra = "ignore"


def get_settings() -> RedisSettings:
    """Get Redis settings."""
    return RedisSettings()


settings = get_settings()