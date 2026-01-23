#!/usr/bin/env python3
"""
Debug database data retrieval.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import db
from app.services.intelligent_context import retrieve_database_data, QueryIntent

async def test_retrieve_database_data():
    """Test retrieve_database_data directly."""
    # Connect to database
    await db.connect()
    print("✅ Database connected")

    try:
        # Create a simple intent
        intent = QueryIntent(
            domains=['database'],
            entities=[],
            requires_data=True,
            is_personal=False,
            is_operational=True,
            time_frame=None
        )

        queries = [
            "What is in my database?",
            "database tables",
        ]

        for query in queries:
            print(f"\n🔍 Testing query: '{query}'")
            print("-" * 40)

            try:
                results = await retrieve_database_data(query, intent)
                print(f"✅ Retrieved {len(results)} results")
                for i, result in enumerate(results):
                    print(f"  {i+1}. {result.get('type')}: {result.get('summary', 'No summary')}")
                    if 'data' in result:
                        print(f"     Data: {result['data']}")
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()

    finally:
        await db.disconnect()
        print("\n✅ Database disconnected")

async def main():
    print("🧠 Debug Database Data Retrieval")
    await test_retrieve_database_data()

if __name__ == "__main__":
    asyncio.run(main())