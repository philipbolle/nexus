"""
Agent Framework MCP Server Configuration
Load NEXUS API URL from environment.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class AgentFrameworkSettings(BaseSettings):
    """Agent framework connection settings."""

    nexus_api_url: str = Field(default="http://localhost:8080", alias="NEXUS_API_URL")
    request_timeout: int = Field(default=30, alias="REQUEST_TIMEOUT")

    class Config:
        env_file = "/home/philip/nexus/.env"
        env_file_encoding = "utf-8"
        extra = "ignore"


def get_settings() -> AgentFrameworkSettings:
    """Get agent framework settings."""
    return AgentFrameworkSettings()


settings = get_settings()