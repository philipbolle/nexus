"""
NEXUS Configuration
Load settings from environment using pydantic-settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


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

    # Cost limits
    daily_budget_usd: float = Field(default=1.0)
    monthly_budget_usd: float = Field(default=3.0)

    @property
    def database_url(self) -> str:
        """PostgreSQL connection string."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def redis_url(self) -> str:
        """Redis connection string."""
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
