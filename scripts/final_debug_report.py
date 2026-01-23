#!/usr/bin/env python3
"""
Final debug report showing exactly why "What is in my database?" returns no context.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

from app.services.intelligent_context import retrieve_intelligent_context
from app.database import db

async def analyze_query(query: str):
    """Analyze why a query returns no context."""
    print(f"\n{'='*80}")
    print(f"ANALYSIS FOR QUERY: '{query}'")
    print(f"{'='*80}")

    await db.connect()

    # Get the context
    context = await retrieve_intelligent_context(query, timeout_seconds=2.0)

    # Analyze the query
    query_lower = query.lower()

    print("\n1. QUERY ANALYSIS:")
    print(f"   Query: '{query}'")
    print(f"   Contains 'database' word: {'database' in query_lower}")
    print(f"   Contains 'table' word: {'table' in query_lower}")
    print(f"   Contains 'schema' word: {'schema' in query_lower}")

    # Check what domains would be detected
    domains = []
    if any(word in query_lower for word in ['spent', 'budget', 'debt', 'money', 'expense', 'finance']):
        domains.append('finance')
    if any(word in query_lower for word in ['email', 'inbox', 'gmail', 'message', 'sender']):
        domains.append('email')
    if any(word in query_lower for word in ['agent', 'session', 'task', 'tool', 'memory']):
        domains.append('agents')
    if any(word in query_lower for word in ['system', 'status', 'health', 'error', 'docker', 'api']):
        domains.append('system')

    print(f"\n2. DOMAIN DETECTION:")
    print(f"   Detected domains: {domains}")
    if not domains:
        print(f"   Default domains (when none detected): ['finance', 'system', 'agents']")

    print(f"\n3. CONTEXT RETRIEVAL RESULTS:")
    print(f"   finance_data: {len(context.finance_data) if context.finance_data else 0} items")
    print(f"   email_data: {len(context.email_data) if context.email_data else 0} items")
    print(f"   agent_data: {len(context.agent_data) if context.agent_data else 0} items")
    print(f"   system_data: {len(context.system_data) if context.system_data else 0} items")
    print(f"   conversation_history: {len(context.conversation_history) if context.conversation_history else 0} items")
    print(f"   usage_data: {len(context.usage_data) if context.usage_data else 0} items")
    print(f"   errors: {context.errors}")

    print(f"\n4. FORMATTED CONTEXT:")
    formatted = context.format_for_ai()
    if formatted:
        print(f"   Length: {len(formatted)} characters")
        print(f"   Content preview: {formatted[:200]}...")
    else:
        print("   (Empty)")

    print(f"\n5. WHY NO DATA WAS RETRIEVED:")

    if 'finance' in domains or (not domains and 'finance' in ['finance', 'system', 'agents']):
        print(f"   • Finance data: Query doesn't contain finance keywords")
        print(f"     Required keywords: 'spent', 'budget', 'debt', 'money', 'expense', 'finance'")
        print(f"     Query contains: {[w for w in ['spent', 'budget', 'debt', 'money', 'expense', 'finance'] if w in query_lower]}")

    if 'agents' in domains or (not domains and 'agents' in ['finance', 'system', 'agents']):
        print(f"   • Agent data: Query doesn't contain agent keywords")
        print(f"     Required keywords: 'agent', 'session', 'task', 'tool', 'memory'")
        print(f"     Query contains: {[w for w in ['agent', 'session', 'task', 'tool', 'memory'] if w in query_lower]}")

    if 'system' in domains or (not domains and 'system' in ['finance', 'system', 'agents']):
        print(f"   • System data: Query doesn't contain system keywords")
        print(f"     Required keywords: 'system', 'status', 'health', 'error', 'docker', 'api'")
        print(f"     Query contains: {[w for w in ['system', 'status', 'health', 'error', 'docker', 'api'] if w in query_lower]}")

    await db.disconnect()

async def show_what_should_happen():
    """Show what should happen with proper implementation."""
    print(f"\n{'='*80}")
    print("WHAT SHOULD HAPPEN WITH PROPER IMPLEMENTATION")
    print(f"{'='*80}")

    print("\n1. Add 'database' domain detection:")
    print("   In retrieve_intelligent_context(), add:")
    print("   if any(word in query_lower for word in ['database', 'table', 'schema', 'what is in']):")
    print("       domains.append('database')")

    print("\n2. Create retrieve_database_data() function:")
    print("   Should return:")
    print("   - Table counts and statistics")
    print("   - Key tables with row counts")
    print("   - Sample data from important tables")
    print("   - Database health status")

    print("\n3. Fix the finance data logic:")
    print("   Change line 139 from:")
    print("   if budget and budget > 0:")
    print("   To:")
    print("   if spent > 0:  # Include any spending data")
    print("   OR set default monthly_target values")

    print("\n4. Fix agent UUID bug:")
    print("   Change line 300 from:")
    print("   f\"Session {row['id'][:8]}... ({row['status']})\"")
    print("   To:")
    print("   f\"Session {str(row['id'])[:8]}... ({row['status']})\"")

async def test_with_fixes():
    """Test what would happen with fixes."""
    print(f"\n{'='*80}")
    print("TESTING WITH HYPOTHETICAL FIXES")
    print(f"{'='*80}")

    test_queries = [
        "What is in my database?",
        "Show me database tables",
        "What tables do I have?",
        "Database schema overview"
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        query_lower = query.lower()

        # Simulate fixed domain detection
        domains = []
        if any(word in query_lower for word in ['spent', 'budget', 'debt', 'money', 'expense', 'finance']):
            domains.append('finance')
        if any(word in query_lower for word in ['email', 'inbox', 'gmail', 'message', 'sender']):
            domains.append('email')
        if any(word in query_lower for word in ['agent', 'session', 'task', 'tool', 'memory']):
            domains.append('agents')
        if any(word in query_lower for word in ['system', 'status', 'health', 'error', 'docker', 'api']):
            domains.append('system')
        # ADDED FIX: database domain detection
        if any(word in query_lower for word in ['database', 'table', 'schema', 'what is in']):
            domains.append('database')

        print(f"  With fix: Detected domains: {domains}")
        if 'database' in domains:
            print(f"  ✓ Would retrieve database overview data")

async def main():
    """Main analysis function."""
    print("FINAL DEBUG REPORT: Why 'What is in my database?' returns no context")
    print("="*80)

    await analyze_query("What is in my database?")
    await analyze_query("How much have I spent this month?")  # For comparison
    await show_what_should_happen()
    await test_with_fixes()

    print(f"\n{'='*80}")
    print("CONCLUSION")
    print(f"{'='*80}")
    print("""
The query "What is in my database?" returns no context because:

1. NO DOMAIN DETECTION: The query doesn't contain keywords for any domain
   (finance, email, agents, system).

2. DEFAULT DOMAINS FAIL: When no domains detected, it defaults to
   ['finance', 'system', 'agents'], but each checks for specific keywords:
   - Finance: requires 'spent', 'budget', 'debt', etc.
   - Agents: requires 'agent', 'session', 'task', etc.
   - System: requires 'system', 'status', 'health', etc.

3. NO 'DATABASE' DOMAIN: There's no domain for database/schema queries.

FIXES NEEDED:
1. Add 'database' domain detection
2. Create retrieve_database_data() function
3. Fix finance data logic (budget = NULL issue)
4. Fix agent UUID bug
5. Consider adding 'general' domain for overview queries
""")

if __name__ == "__main__":
    asyncio.run(main())