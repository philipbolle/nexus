#!/usr/bin/env python3
"""
Check column types for swarm tables.
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import db

async def check_table_columns():
    await db.connect()
    try:
        # Check swarm_memberships columns
        columns = await db.fetch_all("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'swarm_memberships'
            ORDER BY ordinal_position
        """)
        print("swarm_memberships columns:")
        for col in columns:
            print(f"  {col['column_name']:25} {col['data_type']:20} {col['udt_name']}")

        # Check swarms metadata column
        columns2 = await db.fetch_all("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'swarms'
            AND column_name = 'metadata'
        """)
        print("\nswarms metadata column:")
        for col in columns2:
            print(f"  {col['column_name']:25} {col['data_type']:20} {col['udt_name']}")

    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(check_table_columns())