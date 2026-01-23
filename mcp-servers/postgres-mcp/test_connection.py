#!/usr/bin/env python3
"""
Test PostgreSQL connection for MCP server.
"""
import asyncio
import asyncpg
from config import settings


async def test_connection():
    """Test database connection and list tables."""
    try:
        print(f"Connecting to {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db} as {settings.postgres_user}")
        conn = await asyncpg.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            user=settings.postgres_user,
            password=settings.postgres_password,
            database=settings.postgres_db
        )
        print("✅ Connected successfully")

        # List tables
        tables = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        print(f"✅ Found {len(tables)} tables")

        # Show first 5 tables
        for i, row in enumerate(tables[:5]):
            print(f"  {i+1}. {row['table_name']}")
        if len(tables) > 5:
            print(f"  ... and {len(tables) - 5} more")

        await conn.close()
        return True

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)