"""
n8n MCP Server Configuration
Load n8n API credentials from environment.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class N8nSettings(BaseSettings):
    """n8n connection settings."""

    n8n_api_url: str = Field(default="http://localhost:5678", alias="N8N_API_URL")
    n8n_api_key: Optional[str] = Field(default=None, alias="N8N_API_KEY")
    request_timeout: int = Field(default=30, alias="REQUEST_TIMEOUT")

    class Config:
        env_file = "/home/philip/nexus/.env"
        env_file_encoding = "utf-8"
        extra = "ignore"


def get_settings() -> N8nSettings:
    """Get n8n settings."""
    return N8nSettings()


settings = get_settings()