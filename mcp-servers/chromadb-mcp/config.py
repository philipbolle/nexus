"""
ChromaDB MCP Server Configuration
Load ChromaDB connection settings from environment.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class ChromaDBSettings(BaseSettings):
    """ChromaDB connection settings."""

    chromadb_host: str = Field(default="localhost", alias="CHROMADB_HOST")
    chromadb_port: int = Field(default=8000, alias="CHROMADB_PORT")
    chromadb_collection: str = Field(default="nexus_memory", alias="CHROMADB_COLLECTION")

    @property
    def client_settings(self):
        """ChromaDB client settings."""
        return {
            "host": self.chromadb_host,
            "port": self.chromadb_port
        }

    class Config:
        env_file = "/home/philip/nexus/.env"
        env_file_encoding = "utf-8"
        extra = "ignore"


def get_settings() -> ChromaDBSettings:
    """Get ChromaDB settings."""
    return ChromaDBSettings()


settings = get_settings()