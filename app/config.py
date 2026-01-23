"""
NEXUS Configuration
Load settings from environment using pydantic-settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Database
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_user: str = Field(default="nexus", alias="POSTGRES_USER")
    postgres_password: str = Field(alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="nexus_db", alias="POSTGRES_DB")

    # Redis
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_password: str = Field(alias="REDIS_PASSWORD")

    # Celery
    celery_broker_pool_limit: int = Field(default=10, alias="CELERY_BROKER_POOL_LIMIT")
    celery_result_backend: str = Field(default="redis", alias="CELERY_RESULT_BACKEND")
    celery_task_serializer: str = Field(default="json", alias="CELERY_TASK_SERIALIZER")
    celery_result_serializer: str = Field(default="json", alias="CELERY_RESULT_SERIALIZER")
    celery_accept_content: list = Field(default=["json"], alias="CELERY_ACCEPT_CONTENT")
    celery_timezone: str = Field(default="UTC", alias="CELERY_TIMEZONE")
    celery_enable_utc: bool = Field(default=True, alias="CELERY_ENABLE_UTC")

    # ChromaDB
    chromadb_host: str = Field(default="localhost:8000", alias="CHROMADB_HOST")
    chromadb_token: str = Field(default="", alias="CHROMA_TOKEN")
    chromadb_collection_prefix: str = Field(default="nexus_", alias="CHROMADB_COLLECTION_PREFIX")

    # AI Providers
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    google_ai_api_key: str = Field(default="", alias="GOOGLE_AI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")

    # Ollama
    ollama_host: str = Field(default="http://localhost:11434", alias="OLLAMA_HOST")

    # Email accounts
    gmail_email: str = Field(default="", alias="GMAIL_EMAIL")
    gmail_app_password: str = Field(default="", alias="GMAIL_APP_PASSWORD")
    icloud_email: str = Field(default="", alias="ICLOUD_EMAIL")
    icloud_app_password: str = Field(default="", alias="ICLOUD_APP_PASSWORD")

    # Notifications
    ntfy_topic: str = Field(default="", alias="NTFY_TOPIC")

    # Network
    tailscale_ip: str = Field(default="100.68.201.55")
    api_port: int = Field(default=8080)
    cors_origins: List[str] = Field(default=["http://localhost:8080", "http://100.68.201.55:8080"], alias="CORS_ORIGINS")

    # Cost limits
    daily_budget_usd: float = Field(default=1.0)
    monthly_budget_usd: float = Field(default=3.0)
    environment: str = Field(default="development", alias="ENVIRONMENT")

    @property
    def database_url(self) -> str:
        """PostgreSQL connection string."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def redis_url(self) -> str:
        """Redis connection string."""
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"

    @property
    def celery_broker_url(self) -> str:
        """Celery broker URL using Redis."""
        return self.redis_url

    @property
    def celery_result_backend_url(self) -> str:
        """Celery result backend URL."""
        return self.redis_url.replace('/0', '/1')  # Use different Redis database for results

    @property
    def chromadb_settings(self) -> dict:
        """ChromaDB connection settings."""
        return {
            "host": self.chromadb_host,
            "auth_token": self.chromadb_token if self.chromadb_token else None,
            "collection_prefix": self.chromadb_collection_prefix
        }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
