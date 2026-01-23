"""
NEXUS Database Service
Async PostgreSQL connection pool using asyncpg.
"""

import asyncpg
import json
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
import logging

from .config import settings

logger = logging.getLogger(__name__)


async def init_connection(conn):
    """
    Initialize a database connection with custom type codecs.
    This ensures JSONB columns are properly decoded to Python dict/list.
    """
    # Register JSONB codec
    await conn.set_type_codec(
        'jsonb',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog'
    )
    # Also register 'json' type if needed
    await conn.set_type_codec(
        'json',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog'
    )


class Database:
    """Async database connection pool manager."""

    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Initialize the connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                dsn=settings.database_url,
                min_size=2,
                max_size=10,
                command_timeout=60,
                init=init_connection,
            )
            logger.info("Database connection pool created")

    async def disconnect(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Database connection pool closed")

    @asynccontextmanager
    async def connection(self):
        """Get a connection from the pool."""
        if not self._pool:
            raise RuntimeError("Database not connected. Call connect() first.")
        async with self._pool.acquire() as conn:
            yield conn

    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Execute query and return first row as dict."""
        async with self.connection() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute query and return all rows as list of dicts."""
        async with self.connection() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def execute(self, query: str, *args) -> str:
        """Execute query and return status."""
        async with self.connection() as conn:
            return await conn.execute(query, *args)

    async def fetch_val(self, query: str, *args) -> Any:
        """Execute query and return single value."""
        async with self.connection() as conn:
            return await conn.fetchval(query, *args)


# Global database instance
db = Database()


async def get_db() -> Database:
    """Dependency for FastAPI routes."""
    return db
