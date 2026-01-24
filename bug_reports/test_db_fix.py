#!/usr/bin/env python3
"""
Test that database JSONB decoding works after fix.
"""

import asyncio
import sys
sys.path.insert(0, '/home/philip/nexus')

from app.database import db

async def test():
    # Connect to database (pool will be created with init_connection)
    await db.connect()

    # Fetch agents
    agents = await db.fetch_all("SELECT id, name, config FROM agents LIMIT 5")

    print(f"Fetched {len(agents)} agents")
    for i, agent in enumerate(agents):
        config = agent['config']
        print(f"\nAgent {i+1}: {agent['name']}")
        print(f"  Config: {config}")
        print(f"  Config type: {type(config)}")
        print(f"  Is dict: {isinstance(config, dict)}")
        print(f"  Is str: {isinstance(config, str)}")

        # If it's a dict, we can check keys
        if isinstance(config, dict):
            print(f"  Keys: {list(config.keys())}")
        # If it's a string, try to parse
        elif isinstance(config, str):
            import json
            try:
                parsed = json.loads(config)
                print(f"  Parsed as: {type(parsed)}")
            except json.JSONDecodeError:
                print(f"  Could not parse as JSON")

    # Also test other JSONB columns
    print("\n--- Testing other JSONB columns ---")
    # Check if system_config table exists and has JSONB column
    try:
        system_configs = await db.fetch_all("SELECT key, value FROM system_config LIMIT 3")
        for row in system_configs:
            value = row['value']
            print(f"Key: {row['key']}, Value type: {type(value)}")
    except Exception as e:
        print(f"Could not query system_config: {e}")

    await db.disconnect()

async def main():
    try:
        await test()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())