#!/usr/bin/env python3
"""
Test script showing how to fix the intelligent context retrieval issues.
"""

import asyncio
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

from app.database import db

async def test_database_overview():
    """Test what a proper database overview query should return."""
    print("="*80)
    print("DATABASE OVERVIEW FOR 'What is in my database?'")
    print("="*80)

    await db.connect()

    # Get table counts
    tables_with_data = await db.fetch_all("""
        SELECT table_name,
               (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public') as total_tables,
               (SELECT COUNT(*) FROM information_schema.tables t2
                WHERE t2.table_schema = 'public'
                AND EXISTS (SELECT 1 FROM information_schema.columns c
                           WHERE c.table_name = t2.table_name
                           AND c.table_schema = 'public')) as tables_with_columns
        FROM information_schema.tables t
        WHERE t.table_schema = 'public'
        ORDER BY table_name
        LIMIT 5
    """)

    print(f"Total tables in database: {tables_with_data[0]['total_tables'] if tables_with_data else 'Unknown'}")
    print(f"Tables with columns: {tables_with_data[0]['tables_with_columns'] if tables_with_data else 'Unknown'}")

    # Get key statistics
    stats = await db.fetch_all("""
        SELECT
            (SELECT COUNT(*) FROM agents WHERE is_active = true) as active_agents,
            (SELECT COUNT(*) FROM fin_transactions) as total_transactions,
            (SELECT COUNT(*) FROM messages) as total_messages,
            (SELECT COUNT(*) FROM sessions) as total_sessions,
            (SELECT COUNT(*) FROM api_usage WHERE created_at > NOW() - INTERVAL '24 hours') as api_requests_24h,
            (SELECT COALESCE(SUM(cost_usd), 0) FROM api_usage WHERE created_at > NOW() - INTERVAL '24 hours') as api_cost_24h
    """)

    if stats:
        stat = stats[0]
        print("\nKey Statistics:")
        print(f"  • Active agents: {stat['active_agents']}")
        print(f"  • Total transactions: {stat['total_transactions']}")
        print(f"  • Total messages: {stat['total_messages']}")
        print(f"  • Total sessions: {stat['total_sessions']}")
        print(f"  • API requests (24h): {stat['api_requests_24h']}")
        print(f"  • API cost (24h): ${stat['api_cost_24h']:.4f}")

    # Show sample data from key tables
    print("\nSample Data from Key Tables:")

    # Agents
    agents = await db.fetch_all("SELECT name, is_active FROM agents WHERE is_active = true LIMIT 3")
    print(f"  • Active Agents ({len(agents)} shown):")
    for agent in agents:
        print(f"    - {agent['name']} (active: {agent['is_active']})")

    # Categories
    categories = await db.fetch_all("SELECT name FROM fin_categories WHERE is_active = true LIMIT 3")
    print(f"  • Finance Categories ({len(categories)} shown):")
    for cat in categories:
        print(f"    - {cat['name']}")

    # Recent transactions
    transactions = await db.fetch_all("""
        SELECT amount, merchant, transaction_date
        FROM fin_transactions
        ORDER BY transaction_date DESC
        LIMIT 3
    """)
    print(f"  • Recent Transactions ({len(transactions)} shown):")
    for tx in transactions:
        print(f"    - ${tx['amount']} at {tx['merchant'] or 'Unknown'} on {tx['transaction_date'].strftime('%Y-%m-%d')}")

    await db.disconnect()

async def demonstrate_fixes():
    """Demonstrate what fixes are needed."""
    print("\n" + "="*80)
    print("REQUIRED FIXES FOR INTELLIGENT CONTEXT RETRIEVAL")
    print("="*80)

    print("\n1. ADD 'database' DOMAIN DETECTION:")
    print("   Current code doesn't detect 'database' as a domain.")
    print("   Need to add: if any(word in query_lower for word in ['database', 'table', 'schema']):")
    print("                domains.append('database')")

    print("\n2. FIX FINANCE DATA RETRIEVAL LOGIC:")
    print("   Current: if budget and budget > 0: (line 139)")
    print("   Problem: Categories have monthly_target = NULL")
    print("   Fix: Include data even without budget targets")
    print("        OR set default budget targets")

    print("\n3. FIX AGENT DATA UUID BUG:")
    print("   Current: row['id'][:8] (line 300)")
    print("   Problem: row['id'] is UUID object, not string")
    print("   Fix: str(row['id'])[:8]")

    print("\n4. HANDLE MISSING system_health TABLE:")
    print("   Current: Table doesn't exist in schema")
    print("   Options:")
    print("     a) Create system_health table")
    print("     b) Handle exception gracefully")
    print("     c) Use system_metrics table instead")

    print("\n5. IMPROVE DEFAULT DOMAIN SELECTION:")
    print("   Current: ['finance', 'system', 'agents'] for generic queries")
    print("   Problem: Each checks for specific keywords in query")
    print("   Better: Add 'general' domain that always returns overview data")

async def create_proper_response():
    """Show what a proper response should look like."""
    print("\n" + "="*80)
    print("PROPER RESPONSE FOR 'What is in my database?'")
    print("="*80)

    response = """
Based on your NEXUS database, here's what's currently stored:

DATABASE OVERVIEW:
• Total tables: 193 tables in the schema
• Tables with data: 35 tables contain actual data
• Empty tables: 158 tables are empty (awaiting data)

KEY DATA SUMMARY:
• Agents: 15 agents defined, 5 currently active
• Finance: 12 categories, 6 transactions logged
• Conversations: 24 messages across 12 sessions
• System: 6 API requests in last 24h ($0.0001 cost)

SAMPLE DATA:
• Active Agents: router, wealth, finance, learning, health
• Finance Categories: Food & Groceries, Gas & Transportation, Entertainment, Debt Payment, etc.
• Recent Transactions: $1.00 at Test Merchant (2026-01-21), $12.50 (2026-01-19)
• System: Using Groq API (2 requests, 463ms avg latency)

NOTABLE TABLES WITH DATA:
1. agent_tool_assignments (78 rows) - Agent tool configurations
2. messages (24 rows) - Conversation history
3. agents (15 rows) - Agent definitions
4. fin_categories (12 rows) - Spending categories
5. sessions (12 rows) - Conversation sessions
6. api_usage (6 rows) - API request tracking
7. fin_transactions (6 rows) - Financial transactions

The database is fully operational with core tables populated. Most tables (158) are empty because they're for future features like health tracking, learning progress, and wealth management that haven't been used yet.
"""

    print(response)

async def main():
    """Main test function."""
    print("NEXUS Database Context Analysis")
    print("="*80)

    await test_database_overview()
    await demonstrate_fixes()
    await create_proper_response()

if __name__ == "__main__":
    asyncio.run(main())