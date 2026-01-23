#!/usr/bin/env python3
"""
Check all tables in the database and their row counts.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

from app.database import db

async def check_all_tables():
    """Check all tables in the database."""
    await db.connect()

    # Get all table names
    tables = await db.fetch_all("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)

    print("="*80)
    print("ALL DATABASE TABLES")
    print("="*80)

    table_data = []
    for table in tables:
        table_name = table['table_name']
        try:
            count_result = await db.fetch_one(f"SELECT COUNT(*) as count FROM {table_name}")
            table_data.append((table_name, count_result['count']))
        except Exception as e:
            table_data.append((table_name, f"ERROR: {e}"))

    # Sort by row count descending
    table_data.sort(key=lambda x: (0 if isinstance(x[1], int) else 1, -x[1] if isinstance(x[1], int) else 0))

    for table_name, count in table_data:
        if isinstance(count, int):
            print(f"{table_name:40} : {count:6} rows")
        else:
            print(f"{table_name:40} : {count}")

    # Show tables with data
    print("\n" + "="*80)
    print("TABLES WITH DATA (more than 0 rows)")
    print("="*80)

    for table_name, count in table_data:
        if isinstance(count, int) and count > 0:
            print(f"{table_name:40} : {count:6} rows")

    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(check_all_tables())