#!/usr/bin/env python3
"""
Check agent_tools table structure and data.
"""
import asyncio
import json
from app.database import db

async def check_table_structure():
    """Check agent_tools table columns."""
    print("=== Checking agent_tools table structure ===")

    # Get column information
    columns = await db.fetch_all("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'agent_tools'
        ORDER BY ordinal_position
    """)

    print(f"Found {len(columns)} columns in agent_tools table:")
    for col in columns:
        print(f"  - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")

    # Check if updated_at column exists
    updated_at_exists = any(col['column_name'] == 'updated_at' for col in columns)
    print(f"\n'updated_at' column exists: {updated_at_exists}")

    return columns

async def check_tool_data():
    """Check actual tool data in database."""
    print("\n=== Checking tool data in database ===")

    tools = await db.fetch_all("""
        SELECT name, tool_type, input_schema, implementation_config,
               implementation_type, is_enabled
        FROM agent_tools
        ORDER BY name
    """)

    print(f"Found {len(tools)} tools in database:")
    for tool in tools:
        print(f"\nTool: {tool['name']} (type: {tool['tool_type']})")
        print(f"  Implementation type: {tool['implementation_type']}")
        print(f"  Is enabled: {tool['is_enabled']}")

        # Check input_schema type
        input_schema = tool['input_schema']
        print(f"  Input schema type: {type(input_schema)}")
        if isinstance(input_schema, str):
            print(f"  Input schema is string, length: {len(input_schema)}")
            try:
                parsed = json.loads(input_schema)
                print(f"  Can be parsed as JSON: Yes")
            except json.JSONDecodeError:
                print(f"  Can be parsed as JSON: No (invalid JSON)")
        elif isinstance(input_schema, dict):
            print(f"  Input schema is dict, keys: {list(input_schema.keys())}")
        elif input_schema is None:
            print(f"  Input schema is None")
        else:
            print(f"  Input schema is unknown type: {type(input_schema)}")

        # Check implementation_config type
        impl_config = tool['implementation_config']
        print(f"  Implementation config type: {type(impl_config)}")
        if isinstance(impl_config, str):
            print(f"  Implementation config is string, length: {len(impl_config)}")
            try:
                parsed = json.loads(impl_config)
                print(f"  Can be parsed as JSON: Yes")
            except json.JSONDecodeError:
                print(f"  Can be parsed as JSON: No (invalid JSON)")
        elif isinstance(impl_config, dict):
            print(f"  Implementation config is dict, keys: {list(impl_config.keys())}")
        elif impl_config is None:
            print(f"  Implementation config is None")
        else:
            print(f"  Implementation config is unknown type: {type(impl_config)}")

async def main():
    """Main function."""
    await db.connect()
    try:
        columns = await check_table_structure()
        await check_tool_data()
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())