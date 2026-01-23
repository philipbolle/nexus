#!/usr/bin/env python3
"""
Debug script for intelligent context retrieval.
Shows exactly what context is being retrieved for queries.
"""

import asyncio
import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

from app.services.intelligent_context import retrieve_intelligent_context, QueryIntent, RetrievedContext
from app.database import db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def check_database_tables():
    """Check if required database tables exist and have data."""
    print("\n" + "="*80)
    print("DATABASE TABLE CHECK")
    print("="*80)

    # Connect to database first
    await db.connect()

    tables = [
        'fin_categories', 'fin_transactions', 'agents', 'sessions',
        'system_health', 'error_logs', 'api_usage', 'emails', 'messages'
    ]

    for table in tables:
        try:
            # Check if table exists
            exists_result = await db.fetch_one(
                f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}') as exists"
            )

            if exists_result['exists']:
                # Count rows
                count_result = await db.fetch_one(f"SELECT COUNT(*) as count FROM {table}")
                print(f"✓ {table}: EXISTS with {count_result['count']} rows")

                # Show sample data for key tables
                if table in ['fin_categories', 'agents', 'error_logs'] and count_result['count'] > 0:
                    sample = await db.fetch_all(f"SELECT * FROM {table} LIMIT 2")
                    print(f"  Sample: {sample}")
            else:
                print(f"✗ {table}: MISSING")

        except Exception as e:
            print(f"✗ {table}: ERROR - {e}")

    await db.disconnect()

async def test_context_retrieval(query: str):
    """Test context retrieval for a specific query."""
    print("\n" + "="*80)
    print(f"TESTING CONTEXT RETRIEVAL FOR QUERY: '{query}'")
    print("="*80)

    try:
        # Connect to database
        await db.connect()

        # Test the context retrieval
        context = await retrieve_intelligent_context(query, timeout_seconds=2.0)

        print("\n1. RAW RetrievedContext OBJECT:")
        print("-" * 40)
        print(f"finance_data: {len(context.finance_data) if context.finance_data else 0} items")
        print(f"email_data: {len(context.email_data) if context.email_data else 0} items")
        print(f"agent_data: {len(context.agent_data) if context.agent_data else 0} items")
        print(f"system_data: {len(context.system_data) if context.system_data else 0} items")
        print(f"conversation_history: {len(context.conversation_history) if context.conversation_history else 0} items")
        print(f"usage_data: {len(context.usage_data) if context.usage_data else 0} items")
        print(f"errors: {context.errors}")

        print("\n2. FORMATTED CONTEXT (format_for_ai()):")
        print("-" * 40)
        formatted = context.format_for_ai()
        print(formatted if formatted else "(Empty)")

        print("\n3. DETECTED DOMAINS AND INTENT ANALYSIS:")
        print("-" * 40)
        # Manually analyze the query like the function does
        query_lower = query.lower()
        domains = []

        if any(word in query_lower for word in ['spent', 'budget', 'debt', 'money', 'expense', 'finance']):
            domains.append('finance')

        if any(word in query_lower for word in ['email', 'inbox', 'gmail', 'message', 'sender']):
            domains.append('email')

        if any(word in query_lower for word in ['agent', 'session', 'task', 'tool', 'memory']):
            domains.append('agents')

        if any(word in query_lower for word in ['system', 'status', 'health', 'error', 'docker', 'api']):
            domains.append('system')

        # If no specific domain detected, check a few key ones
        if not domains:
            domains = ['finance', 'system', 'agents']  # Default domains to check

        print(f"Query: '{query}'")
        print(f"Detected domains: {domains}")
        print(f"Is personal query: {any(word in query_lower for word in ['i', 'my', 'me', 'mine'])}")
        print(f"Is operational query: {any(word in query_lower for word in ['status', 'check', 'how', 'what'])}")

        # Check what data should have been retrieved
        print("\n4. EXPECTED DATA RETRIEVAL:")
        print("-" * 40)
        if 'finance' in domains:
            print("✓ Should retrieve finance data")
        if 'email' in domains:
            print("✓ Should retrieve email data")
        if 'agents' in domains:
            print("✓ Should retrieve agent data")
        if 'system' in domains:
            print("✓ Should retrieve system data")

        # Check database connection issues
        print("\n5. DATABASE CONNECTION STATUS:")
        print("-" * 40)
        try:
            # Test a simple query
            test_result = await db.fetch_one("SELECT 1 as test")
            print("✓ Database connection: OK")
        except Exception as e:
            print(f"✗ Database connection error: {e}")

    except Exception as e:
        print(f"\nERROR during context retrieval: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.disconnect()

async def main():
    """Main debug function."""
    print("NEXUS Intelligent Context Debug Script")
    print("="*80)

    # First check database tables
    await check_database_tables()

    # Test with the specific query
    await test_context_retrieval("What is in my database?")

    # Test with other queries for comparison
    print("\n" + "="*80)
    print("ADDITIONAL TEST QUERIES")
    print("="*80)

    test_queries = [
        "How much have I spent this month?",
        "Show me my recent emails",
        "What agents are running?",
        "What is the system status?",
        "Check my database"
    ]

    for query in test_queries:
        print(f"\nTesting: '{query}'")
        try:
            await db.connect()
            context = await retrieve_intelligent_context(query, timeout_seconds=1.0)
            formatted = context.format_for_ai()
            print(f"Retrieved context length: {len(formatted)} chars")
            print(f"Errors: {context.errors}")
            await db.disconnect()
        except Exception as e:
            print(f"Error: {e}")
            await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())