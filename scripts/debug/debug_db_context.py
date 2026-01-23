#!/usr/bin/env python3
"""
Debug database context retrieval.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import db
from app.services.intelligent_context import retrieve_intelligent_context

async def test_database_query():
    """Test database query context retrieval."""
    queries = [
        "What is in my database?",
        "database tables",
        "show me my database schema",
        "what tables are in my database",
        "How many tables in my database?",
    ]

    for query in queries:
        print(f"\n🔍 Query: '{query}'")
        print("-" * 40)

        try:
            context = await retrieve_intelligent_context(query, timeout_seconds=2.0)

            print(f"Domains detected: {context.domains if hasattr(context, 'domains') else 'N/A'}")
            print(f"Finance data: {len(context.finance_data) if context.finance_data else 0}")
            print(f"Email data: {len(context.email_data) if context.email_data else 0}")
            print(f"Agent data: {len(context.agent_data) if context.agent_data else 0}")
            print(f"System data: {len(context.system_data) if context.system_data else 0}")
            print(f"Database data: {len(context.database_data) if context.database_data else 0}")
            print(f"Conversation history: {len(context.conversation_history) if context.conversation_history else 0}")
            print(f"Errors: {context.errors}")

            formatted = context.format_for_ai()
            if formatted and formatted != "No relevant data found.":
                print(f"\nFormatted context (first 500 chars):")
                print(formatted[:500] + "..." if len(formatted) > 500 else formatted)
            else:
                print("\nNo formatted context returned")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

async def main():
    print("🧠 Debug Database Context Retrieval")

    # Connect to database
    try:
        await db.connect()
        print("✅ Database connected")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return

    try:
        await test_database_query()
    finally:
        await db.disconnect()
        print("\n✅ Database disconnected")

if __name__ == "__main__":
    asyncio.run(main())