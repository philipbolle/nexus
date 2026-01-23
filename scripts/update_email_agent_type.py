#!/usr/bin/env python3
"""
Update the Email Intelligence Agent record to use agent_type 'email_intelligence'.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def update_agent_type():
    from app.database import db
    from app.agents.registry import AgentRegistry

    print("Connecting to database...")
    await db.connect()

    try:
        # Find the email agent record
        agent_record = await db.fetch_one(
            "SELECT id, name, agent_type FROM agents WHERE name = $1",
            "Email Intelligence Agent"
        )
        if not agent_record:
            print("Email agent not found in database.")
            return

        print(f"Found email agent: {agent_record['name']} (ID: {agent_record['id']})")
        print(f"Current agent_type: {agent_record['agent_type']}")

        if agent_record['agent_type'] == 'email_intelligence':
            print("Agent already has correct agent_type.")
            return

        # Update agent_type
        await db.execute(
            "UPDATE agents SET agent_type = $1, updated_at = NOW() WHERE id = $2",
            'email_intelligence',
            agent_record['id']
        )
        print("Updated agent_type to 'email_intelligence'")

        # Verify update
        updated = await db.fetch_one(
            "SELECT agent_type FROM agents WHERE id = $1",
            agent_record['id']
        )
        print(f"Verified agent_type: {updated['agent_type']}")

        # Re-initialize registry to load with correct type
        print("\nRe-initializing registry...")
        registry = AgentRegistry()
        # Need to shutdown if already running
        if registry.status.name == 'RUNNING':
            await registry.shutdown()
        await registry.initialize()

        # Check email agent class
        email_agent = await registry.get_agent_by_name("Email Intelligence Agent")
        if email_agent:
            print(f"Email agent loaded: {email_agent.name}")
            print(f"  Class: {email_agent.__class__.__name__}")
            print(f"  Type: {email_agent.agent_type}")
            if email_agent.__class__.__name__ == 'EmailIntelligenceAgent':
                print("✓ Successfully loaded as EmailIntelligenceAgent")
            else:
                print("✗ Still loaded as wrong class")
        else:
            print("✗ Email agent not found in registry after update")

    except Exception as e:
        print(f"Error updating agent type: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(update_agent_type())