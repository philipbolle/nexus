#!/usr/bin/env python3
"""
Test email agent duplicate key error fix.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_email_agent_fix():
    from app.database import db
    from app.agents.registry import AgentRegistry
    from app.agents.email_intelligence import register_email_agent

    print("Connecting to database...")
    await db.connect()

    try:
        print("1. Initializing agent registry...")
        registry = AgentRegistry()
        await registry.initialize()

        print(f"   Registry status: {registry.status}")
        print(f"   Agents loaded: {len(registry.agents)}")

        # Check if email agent already loaded
        email_agent_in_registry = None
        for agent in registry.agents.values():
            if agent.name == "Email Intelligence Agent":
                email_agent_in_registry = agent
                break

        if email_agent_in_registry:
            print(f"   Email agent found in registry: {email_agent_in_registry.agent_id}")
        else:
            print("   Email agent not yet in registry")

        # Query database for email agent
        db_agent = await db.fetch_one(
            "SELECT id FROM agents WHERE name = $1",
            "Email Intelligence Agent"
        )
        if db_agent:
            print(f"   Email agent in database: {db_agent['id']}")
        else:
            print("   ERROR: Email agent not found in database!")
            return False

        print("\n2. Calling register_email_agent()...")
        try:
            email_agent = await register_email_agent()
            print(f"   Success! Email agent returned: {email_agent.name} (ID: {email_agent.agent_id})")

            # Verify agent ID matches database ID
            if email_agent.agent_id == str(db_agent['id']):
                print(f"   ✅ Agent ID matches database ID")
            else:
                print(f"   ⚠ Agent ID mismatch: agent={email_agent.agent_id}, db={db_agent['id']}")
                # Check if agent is in registry with correct ID
                if email_agent.agent_id in registry.agents:
                    print(f"   Agent registered with ID {email_agent.agent_id}")

            # Verify no duplicate agents in database
            duplicate_check = await db.fetch_all(
                "SELECT id FROM agents WHERE name = $1",
                "Email Intelligence Agent"
            )
            if len(duplicate_check) == 1:
                print(f"   ✅ Only one email agent in database")
            else:
                print(f"   ❌ Multiple email agents in database: {len(duplicate_check)}")
                for row in duplicate_check:
                    print(f"      ID: {row['id']}")
                return False

            return True

        except Exception as e:
            print(f"   ❌ register_email_agent failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    finally:
        await db.disconnect()

if __name__ == "__main__":
    success = asyncio.run(test_email_agent_fix())
    sys.exit(0 if success else 1)