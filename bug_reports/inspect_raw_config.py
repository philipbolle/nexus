#!/usr/bin/env python3
"""
Inspect raw config values in agents table.
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

async def inspect_config():
    """Inspect raw config values."""
    load_dotenv('/home/philip/nexus/.env')

    db_host = os.getenv('POSTGRES_HOST', 'localhost')
    db_port = os.getenv('POSTGRES_PORT', '5432')
    db_name = os.getenv('POSTGRES_DB', 'nexus_db')
    db_user = os.getenv('POSTGRES_USER', 'nexus')
    db_password = os.getenv('POSTGRES_PASSWORD', '')

    print("Inspecting raw config values...")

    try:
        conn = await asyncpg.connect(
            host=db_host,
            port=int(db_port),
            database=db_name,
            user=db_user,
            password=db_password
        )

        # Get raw bytes using encode
        raw_data = await conn.fetch("""
            SELECT id, name,
                   config::text as config_text,
                   pg_typeof(config) as pg_type,
                   octet_length(config::text) as byte_length,
                   config is null as is_null,
                   config::text = '{}' as equals_empty_string,
                   config::text = '' as equals_empty
            FROM agents
            LIMIT 10
        """)

        print("\nFirst 10 rows:")
        for row in raw_data:
            print(f"ID: {row['id']}, Name: {row['name']}")
            print(f"  config_text: '{row['config_text']}'")
            print(f"  pg_type: {row['pg_type']}")
            print(f"  byte_length: {row['byte_length']}")
            print(f"  is_null: {row['is_null']}")
            print(f"  equals_empty_string: {row['equals_empty_string']}")
            print(f"  equals_empty: {row['equals_empty']}")
            print()

        # Try to see if we can cast to jsonb
        try:
            jsonb_test = await conn.fetchval("""
                SELECT config::jsonb FROM agents LIMIT 1
            """)
            print(f"Direct cast to jsonb: {jsonb_test}, type: {type(jsonb_test)}")
        except Exception as e:
            print(f"Casting to jsonb failed: {e}")

        # Check default value from schema
        default_check = await conn.fetchrow("""
            SELECT column_default
            FROM information_schema.columns
            WHERE table_name = 'agents' AND column_name = 'config'
        """)
        if default_check:
            print(f"\nColumn default: {default_check['column_default']}")

        await conn.close()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    await inspect_config()

if __name__ == "__main__":
    asyncio.run(main())