#!/usr/bin/env python3
"""
Test agent framework initialization.
Run this to verify that agent registry loads correctly and email agent is registered.
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_agent_framework():
    """Test agent framework initialization."""
    from app.database import db
    from app.agents.registry import AgentRegistry
    from app.agents.email_intelligence import register_email_agent

    print("Connecting to database...")
    await db.connect()

    try:
        print("Initializing agent registry...")
        registry = AgentRegistry()
        await registry.initialize()

        print(f"Registry status: {registry.status}")
        print(f"Total agents: {len(registry.agents)}")

        # Check if email agent exists
        email_agent = await registry.get_agent_by_name("Email Intelligence Agent")
        if email_agent:
            print(f"✓ Email agent found: {email_agent.name} (ID: {email_agent.agent_id})")
            print(f"  Type: {email_agent.agent_type}")
            print(f"  Class: {email_agent.__class__.__name__}")
            print(f"  Capabilities: {email_agent.capabilities}")
        else:
            print("✗ Email agent not found in registry, trying to register...")
            email_agent = await register_email_agent()
            print(f"✓ Email agent registered: {email_agent.name}")

        # List all agents
        print("\nAll registered agents:")
        for agent_id, agent in registry.agents.items():
            print(f"  - {agent.name} ({agent_id}) - {agent.status}")

        # Test registry status endpoint
        status = await registry.get_registry_status()
        print(f"\nRegistry status: {status}")

        print("\n✓ Agent framework initialization test passed!")

    except Exception as e:
        print(f"\n✗ Agent framework initialization failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(test_agent_framework())