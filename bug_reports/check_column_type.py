#!/usr/bin/env python3
"""
Check column types in database.
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

async def check_agents_table():
    """Check agents table schema."""
    load_dotenv('/home/philip/nexus/.env')

    db_host = os.getenv('POSTGRES_HOST', 'localhost')
    db_port = os.getenv('POSTGRES_PORT', '5432')
    db_name = os.getenv('POSTGRES_DB', 'nexus_db')
    db_user = os.getenv('POSTGRES_USER', 'nexus')
    db_password = os.getenv('POSTGRES_PASSWORD', '')

    print("Checking agents table schema...")

    try:
        conn = await asyncpg.connect(
            host=db_host,
            port=int(db_port),
            database=db_name,
            user=db_user,
            password=db_password
        )

        # Get column information
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'agents'
            ORDER BY ordinal_position
        """)

        print("\nAgents table columns:")
        print("-" * 80)
        for col in columns:
            print(f"{col['column_name']:30} {col['data_type']:20} nullable: {col['is_nullable']}")

        # Specifically check config column
        config_col = await conn.fetchrow("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = 'agents' AND column_name = 'config'
        """)

        if config_col:
            print(f"\nConfig column details:")
            print(f"  Data type: {config_col['data_type']}")
            print(f"  UDT name: {config_col['udt_name']}")

            # Check sample data
            samples = await conn.fetch("""
                SELECT config, pg_typeof(config) as type_name
                FROM agents
                WHERE config IS NOT NULL AND config != ''
                LIMIT 5
            """)

            print(f"\nSample config values (first 5 non-empty):")
            for i, sample in enumerate(samples):
                print(f"  {i+1}. Type: {sample['type_name']}, Value: {sample['config'][:100]}")

        # Check for other JSON columns
        json_columns = await conn.fetch("""
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE data_type IN ('json', 'jsonb')
            ORDER BY table_name, column_name
        """)

        print(f"\nAll JSON columns in database:")
        for col in json_columns:
            print(f"  {col['table_name']}.{col['column_name']}: {col['data_type']}")

        await conn.close()

    except Exception as e:
        print(f"Error: {e}")

async def main():
    await check_agents_table()

if __name__ == "__main__":
    asyncio.run(main())