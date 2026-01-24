#!/usr/bin/env python3
"""
Test asyncpg JSONB decoding.
"""

import asyncio
import asyncpg
import os
import json
from dotenv import load_dotenv

async def test_jsonb():
    load_dotenv('/home/philip/nexus/.env')

    db_host = os.getenv('POSTGRES_HOST', 'localhost')
    db_port = os.getenv('POSTGRES_PORT', '5432')
    db_name = os.getenv('POSTGRES_DB', 'nexus_db')
    db_user = os.getenv('POSTGRES_USER', 'nexus')
    db_password = os.getenv('POSTGRES_PASSWORD', '')

    print("Testing asyncpg JSONB decoding...")

    # Connect without any special codec
    conn = await asyncpg.connect(
        host=db_host,
        port=int(db_port),
        database=db_name,
        user=db_user,
        password=db_password
    )

    # Fetch a row
    row = await conn.fetchrow("SELECT config FROM agents LIMIT 1")
    print(f"Row: {row}")
    print(f"Row type: {type(row)}")
    if row:
        config = row['config']
        print(f"Config value: {config}")
        print(f"Config type: {type(config)}")
        print(f"Config repr: {repr(config)}")

        # Try to check if it's a string or dict
        if isinstance(config, str):
            print("Config is a string")
            # Try to parse it as JSON
            try:
                parsed = json.loads(config)
                print(f"Parsed JSON: {parsed}, type: {type(parsed)}")
            except json.JSONDecodeError as e:
                print(f"Failed to parse as JSON: {e}")
        elif isinstance(config, dict):
            print("Config is a dict")
        else:
            print(f"Config is unexpected type: {type(config)}")

    # Test with explicit type codec
    print("\n--- Testing with explicit JSON codec ---")
    # Register json codec for 'jsonb' type
    await conn.set_type_codec(
        'jsonb',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog'
    )

    # Fetch again
    row2 = await conn.fetchrow("SELECT config FROM agents LIMIT 1")
    if row2:
        config2 = row2['config']
        print(f"With codec - Config value: {config2}")
        print(f"With codec - Config type: {type(config2)}")
        print(f"With codec - Config repr: {repr(config2)}")

    await conn.close()

async def main():
    await test_jsonb()

if __name__ == "__main__":
    asyncio.run(main())