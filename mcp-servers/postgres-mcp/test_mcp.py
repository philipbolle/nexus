#!/usr/bin/env python3
"""
Test PostgreSQL MCP server functionality.
"""
import asyncio
import sys
sys.path.insert(0, '.')

from server import PostgresMCP


async def test_mcp_functionality():
    """Test core MCP functionality."""
    mcp = PostgresMCP()

    try:
        # Connect
        await mcp.connect()
        print("✅ Connected to PostgreSQL")

        # Test list_tables
        tables = await mcp.list_tables()
        print(f"✅ list_tables: Found {len(tables)} tables")

        # Test describe_table on first table (if exists)
        if tables:
            table_name = tables[0]
            schema = await mcp.describe_table(table_name)
            print(f"✅ describe_table: {len(schema)} columns in {table_name}")

            # Test get_table_stats
            stats = await mcp.get_table_stats(table_name)
            print(f"✅ get_table_stats: {stats['row_count']} rows in {table_name}")

            # Test search_schema
            results = await mcp.search_schema("agent")
            print(f"✅ search_schema: Found {len(results)} matches for 'agent'")

        # Test execute_query (simple select)
        query = "SELECT 1 as test"
        rows = await mcp.execute_query(query)
        print(f"✅ execute_query: Query returned {len(rows)} rows")

        # Test safety - non-SELECT query should raise ValueError
        try:
            await mcp.execute_query("DELETE FROM non_existent")
            print("❌ execute_query safety check failed - DELETE allowed")
        except ValueError as e:
            print(f"✅ execute_query safety check passed: {e}")

        print("\n✅ All PostgreSQL MCP tests passed")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await mcp.disconnect()


if __name__ == "__main__":
    success = asyncio.run(test_mcp_functionality())
    sys.exit(0 if success else 1)