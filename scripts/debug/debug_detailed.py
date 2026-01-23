#!/usr/bin/env python3
"""
Detailed debug script for intelligent context retrieval.
"""

import asyncio
import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

from app.services.intelligent_context import (
    retrieve_intelligent_context,
    retrieve_finance_data,
    retrieve_agent_data,
    retrieve_system_data,
    retrieve_email_data,
    QueryIntent
)
from app.database import db

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def debug_finance_retrieval():
    """Debug finance data retrieval specifically."""
    print("\n" + "="*80)
    print("DEBUG FINANCE DATA RETRIEVAL")
    print("="*80)

    await db.connect()

    # Test queries
    test_queries = [
        "What is in my database?",
        "How much have I spent this month?",
        "Check my budget",
        "Show me my transactions"
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        intent = QueryIntent(
            domains=['finance'],
            entities=[],
            requires_data=True,
            is_personal=True,
            is_operational=True,
            time_frame=None
        )

        try:
            result = await retrieve_finance_data(query, intent)
            print(f"  Result: {len(result)} items")
            if result:
                for i, item in enumerate(result[:3]):
                    print(f"    {i+1}. {item.get('summary', 'No summary')}")
        except Exception as e:
            print(f"  ERROR: {e}")

    # Check why month_spending query returns no results
    print("\n" + "-"*80)
    print("DEBUG: Why month_spending query returns no results")
    print("-"*80)

    # Check if categories have monthly_target
    categories = await db.fetch_all(
        "SELECT name, monthly_target FROM fin_categories WHERE is_active = true"
    )
    print(f"Active categories: {len(categories)}")
    for cat in categories:
        print(f"  - {cat['name']}: monthly_target = {cat['monthly_target']}")

    # Check transactions
    transactions = await db.fetch_all(
        "SELECT COUNT(*) as count, SUM(amount) as total FROM fin_transactions WHERE transaction_type = 'expense'"
    )
    print(f"\nExpense transactions: {transactions[0]['count']}, total: ${transactions[0]['total']}")

    # Run the actual month_spending query
    month_spending = await db.fetch_all("""
        SELECT
            c.name as category,
            COALESCE(SUM(t.amount), 0) as spent,
            c.monthly_target as budget
        FROM fin_categories c
        LEFT JOIN fin_transactions t ON t.category_id = c.id
            AND t.transaction_type = 'expense'
            AND DATE_TRUNC('month', t.transaction_date) = DATE_TRUNC('month', CURRENT_DATE)
        WHERE c.is_active = true
        GROUP BY c.id, c.name, c.monthly_target
        ORDER BY spent DESC
        LIMIT 10
    """)
    print(f"\nMonth spending query results: {len(month_spending)} rows")
    for row in month_spending:
        print(f"  - {row['category']}: spent=${row['spent']}, budget={row['budget']}")

    await db.disconnect()

async def debug_agent_retrieval():
    """Debug agent data retrieval specifically."""
    print("\n" + "="*80)
    print("DEBUG AGENT DATA RETRIEVAL")
    print("="*80)

    await db.connect()

    # Test the failing query
    query = "What agents are running?"
    intent = QueryIntent(
        domains=['agents'],
        entities=[],
        requires_data=True,
        is_personal=True,
        is_operational=True,
        time_frame=None
    )

    try:
        result = await retrieve_agent_data(query, intent)
        print(f"Query: '{query}'")
        print(f"Result: {len(result)} items")
        if result:
            for i, item in enumerate(result):
                print(f"  {i+1}. {item.get('summary', 'No summary')}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    # Check sessions table structure
    print("\n" + "-"*80)
    print("DEBUG: Sessions table structure")
    print("-"*80)

    try:
        sessions = await db.fetch_all("SELECT id, status, started_at FROM sessions LIMIT 3")
        print(f"Sessions sample: {len(sessions)} rows")
        for session in sessions:
            print(f"  - ID type: {type(session['id'])}, value: {session['id']}")
            print(f"    Status: {session['status']}, Started: {session['started_at']}")
    except Exception as e:
        print(f"Error checking sessions: {e}")

    await db.disconnect()

async def debug_system_retrieval():
    """Debug system data retrieval specifically."""
    print("\n" + "="*80)
    print("DEBUG SYSTEM DATA RETRIEVAL")
    print("="*80)

    await db.connect()

    # Test query
    query = "What is the system status?"
    intent = QueryIntent(
        domains=['system'],
        entities=[],
        requires_data=True,
        is_personal=True,
        is_operational=True,
        time_frame=None
    )

    try:
        result = await retrieve_system_data(query, intent)
        print(f"Query: '{query}'")
        print(f"Result: {len(result)} items")
        if result:
            for i, item in enumerate(result):
                print(f"  {i+1}. {item.get('summary', 'No summary')}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    # Check system_health table
    print("\n" + "-"*80)
    print("DEBUG: system_health table check")
    print("-"*80)

    try:
        exists = await db.fetch_one(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'system_health') as exists"
        )
        if exists['exists']:
            print("system_health table: EXISTS")
            rows = await db.fetch_all("SELECT * FROM system_health LIMIT 3")
            print(f"  Rows: {len(rows)}")
            for row in rows:
                print(f"  - {row}")
        else:
            print("system_health table: MISSING (this is expected - table doesn't exist in schema)")
    except Exception as e:
        print(f"Error: {e}")

    await db.disconnect()

async def main():
    """Main debug function."""
    print("NEXUS Intelligent Context Detailed Debug")
    print("="*80)

    # Run all debug functions
    await debug_finance_retrieval()
    await debug_agent_retrieval()
    await debug_system_retrieval()

    # Test the original issue
    print("\n" + "="*80)
    print("ORIGINAL ISSUE TEST: 'What is in my database?'")
    print("="*80)

    await db.connect()
    context = await retrieve_intelligent_context("What is in my database?", timeout_seconds=2.0)
    print(f"\nRetrieved context:")
    print(context.format_for_ai())
    print(f"\nErrors: {context.errors}")
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())