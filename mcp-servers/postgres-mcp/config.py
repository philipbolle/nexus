"""
PostgreSQL MCP Server Configuration
Load PostgreSQL credentials from environment variables or .env file.
"""

import os
from typing import Optional
from pydantic import BaseSettings, Field


class PostgresSettings(BaseSettings):
    """PostgreSQL connection settings."""

    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_user: str = Field(default="nexus", alias="POSTGRES_USER")
    postgres_password: str = Field(alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="nexus_db", alias="POSTGRES_DB")

    @property
    def dsn(self) -> str:
        """PostgreSQL connection string."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


def get_settings() -> PostgresSettings:
    """Get PostgreSQL settings."""
    return PostgresSettings()


settings = get_settings()