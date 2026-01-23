#!/usr/bin/env python3
"""
Check database for Email Intelligence Agent.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def check_email_agent():
    from app.database import db

    await db.connect()

    try:
        # Check for Email Intelligence Agent
        result = await db.fetch_all(
            "SELECT id, name, agent_type, is_active, created_at FROM agents WHERE name = $1",
            "Email Intelligence Agent"
        )

        print(f"Found {len(result)} agents with name 'Email Intelligence Agent':")
        for row in result:
            print(f"  ID: {row['id']}")
            print(f"  Name: {row['name']}")
            print(f"  Type: {row['agent_type']}")
            print(f"  Active: {row['is_active']}")
            print(f"  Created: {row['created_at']}")
            print()

        # Check all agents for duplicates
        print("\nChecking for duplicate agent names...")
        duplicates = await db.fetch_all(
            """
            SELECT name, COUNT(*) as count, array_agg(id) as ids,
                   array_agg(agent_type) as types, array_agg(is_active) as active_statuses
            FROM agents
            GROUP BY name
            HAVING COUNT(*) > 1
            """
        )

        print(f"Found {len(duplicates)} duplicate agent names:")
        for row in duplicates:
            print(f"  Name: {row['name']} (count: {row['count']})")
            print(f"    IDs: {row['ids']}")
            print(f"    Types: {row['types']}")
            print(f"    Active: {row['active_statuses']}")
            print()

    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(check_email_agent())