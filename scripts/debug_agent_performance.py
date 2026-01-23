#!/usr/bin/env python3
"""
Debug agent performance endpoint.
"""

import asyncio
import sys
from pathlib import Path
from uuid import UUID

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import db
from app.agents.monitoring import PerformanceMonitor


async def test_query():
    """Test the get_agent_performance_history method directly."""
    monitor = PerformanceMonitor()

    query = {
        "agent_id": UUID("667c97fc-fa58-4644-8b85-9b7d941fd8d5"),
        "start_date": None,
        "end_date": None,
        "metric": None
    }

    print(f"Testing with query: {query}")
    try:
        result = await monitor.get_agent_performance_history(query)
        print(f"Success! Got {len(result)} records")
        for r in result[:2]:
            print(f"  {r}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


async def check_table_columns():
    """Check columns in agent_performance table."""
    print("\nChecking agent_performance columns...")
    try:
        columns = await db.fetch_all("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'agent_performance'
            ORDER BY ordinal_position
        """)
        print(f"Found {len(columns)} columns:")
        for col in columns:
            print(f"  {col['column_name']:25} {col['data_type']:20} nullable={col['is_nullable']}")
    except Exception as e:
        print(f"Error: {e}")


async def test_sql_query():
    """Run the exact SQL query from get_agent_performance_history."""
    print("\nTesting SQL query directly...")
    agent_id = UUID("667c97fc-fa58-4644-8b85-9b7d941fd8d5")
    sql = """
        SELECT ap.*, a.name as agent_name
        FROM agent_performance ap
        JOIN agents a ON ap.agent_id = a.id
        WHERE ap.agent_id = $1
        ORDER BY ap.date DESC
        LIMIT 100
    """
    try:
        rows = await db.fetch_all(sql, agent_id)
        print(f"Query returned {len(rows)} rows")
        for row in rows[:2]:
            print(f"  Date: {row['date']}, Requests: {row['total_requests']}")
    except Exception as e:
        print(f"SQL error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    await db.connect()
    try:
        await test_query()
        await check_table_columns()
        await test_sql_query()
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())