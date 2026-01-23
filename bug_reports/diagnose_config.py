#!/usr/bin/env python3
"""
Diagnose config column issues.
"""

import asyncio
import asyncpg
import json
import os
from dotenv import load_dotenv

async def diagnose_config():
    """Diagnose config column problems."""
    load_dotenv('/home/philip/nexus/.env')

    db_host = os.getenv('POSTGRES_HOST', 'localhost')
    db_port = os.getenv('POSTGRES_PORT', '5432')
    db_name = os.getenv('POSTGRES_DB', 'nexus_db')
    db_user = os.getenv('POSTGRES_USER', 'nexus')
    db_password = os.getenv('POSTGRES_PASSWORD', '')

    print("Diagnosing config column issues...")

    try:
        conn = await asyncpg.connect(
            host=db_host,
            port=int(db_port),
            database=db_name,
            user=db_user,
            password=db_password
        )

        # First, let's see the distribution of config values
        print("\n1. Config value analysis:")

        # Count by config pattern
        patterns = await conn.fetch("""
            SELECT
                CASE
                    WHEN config IS NULL THEN 'NULL'
                    WHEN config::text = 'null' THEN 'JSON null'
                    WHEN config::text = '' THEN 'Empty string'
                    WHEN config::text = '{}' THEN 'Empty object string'
                    WHEN jsonb_typeof(config) = 'object' THEN 'Valid JSON object'
                    WHEN jsonb_typeof(config) = 'array' THEN 'Valid JSON array'
                    ELSE 'Other'
                END as config_type,
                COUNT(*) as count
            FROM agents
            GROUP BY 1
            ORDER BY count DESC
        """)

        for row in patterns:
            print(f"  {row['config_type']}: {row['count']}")

        # Try to get raw text values (bypass JSON parsing)
        print("\n2. Raw config text values (sample):")
        raw_samples = await conn.fetch("""
            SELECT id, name, config::text as raw_config,
                   LENGTH(config::text) as length,
                   LEFT(config::text, 50) as preview
            FROM agents
            WHERE config IS NOT NULL
            LIMIT 10
        """)

        for sample in raw_samples:
            print(f"  ID: {sample['id']}, Name: {sample['name']}")
            print(f"    Length: {sample['length']}, Preview: '{sample['preview']}'")

        # Check which agents have problematic config
        print("\n3. Agents with potentially invalid config:")
        problematic = await conn.fetch("""
            SELECT id, name, config::text as raw_config
            FROM agents
            WHERE config IS NOT NULL
            AND (
                config::text = ''
                OR config::text = 'null'
                OR NOT (config::text ~ '^\{.*\}$' OR config::text ~ '^\[.*\]$')
                OR jsonb_typeof(config) IS NULL
            )
            LIMIT 20
        """)

        if problematic:
            print(f"  Found {len(problematic)} potentially problematic rows:")
            for row in problematic:
                print(f"    {row['name']}: '{row['raw_config']}'")
        else:
            print("  No obviously problematic rows found.")

        # Test parsing some config values
        print("\n4. Testing JSON parsing:")
        test_samples = await conn.fetch("""
            SELECT id, name, config::text as raw_config
            FROM agents
            WHERE config IS NOT NULL AND config::text != ''
            LIMIT 5
        """)

        for sample in test_samples:
            raw = sample['raw_config']
            print(f"  {sample['name']}: '{raw}'")
            try:
                parsed = json.loads(raw)
                print(f"    ✅ Parsed as: {type(parsed).__name__}")
            except json.JSONDecodeError as e:
                print(f"    ❌ JSON decode error: {e}")

        await conn.close()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    await diagnose_config()

if __name__ == "__main__":
    asyncio.run(main())