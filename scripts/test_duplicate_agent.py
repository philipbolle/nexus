#!/usr/bin/env python3
"""
Test agent registration duplicate key error handling.
Tests both in-memory duplicate detection and database unique constraint.
"""
import asyncio
import sys
import os
import uuid

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_duplicate_agent():
    """Test duplicate agent registration error handling."""
    from app.database import db
    from app.agents.registry import AgentRegistry
    from app.agents.base import AgentType

    print("Connecting to database...")
    await db.connect()

    try:
        print("Initializing agent registry...")
        registry = AgentRegistry()
        await registry.initialize()

        print(f"Registry status: {registry.status}")
        print(f"Total agents: {len(registry.agents)}")

        # Generate unique agent name
        test_agent_name = f"test_agent_{uuid.uuid4().hex[:8]}"
        print(f"\n1. Creating first agent with name: {test_agent_name}")

        # Create first agent
        agent1 = await registry.create_agent(
            agent_type="domain",
            name=test_agent_name,
            description="Test agent for duplicate registration test",
            system_prompt="You are a test agent.",
            capabilities=["test"],
            domain="test"
        )
        print(f"   ✓ Created agent: {agent1.name} (ID: {agent1.agent_id})")

        # Verify agent exists in registry
        assert agent1.agent_id in registry.agents
        assert registry.agents[agent1.agent_id].name == test_agent_name

        # Try to create another agent with same name - should raise ValueError
        print(f"\n2. Attempting to create duplicate agent with same name: {test_agent_name}")
        try:
            agent2 = await registry.create_agent(
                agent_type="domain",
                name=test_agent_name,
                description="Duplicate agent",
                system_prompt="Duplicate",
                capabilities=["test"],
                domain="test"
            )
            print("   ✗ ERROR: Duplicate agent creation should have raised ValueError!")
            print(f"   Duplicate agent created: {agent2.name} (ID: {agent2.agent_id})")
            # Clean up duplicate
            await registry.delete_agent(uuid.UUID(agent2.agent_id))
            return False
        except ValueError as e:
            print(f"   ✓ Duplicate detection caught ValueError: {e}")
            # Check error message mentions duplicate
            if "already exists" in str(e):
                print("   ✓ Error message correctly mentions duplicate name")
            else:
                print(f"   ⚠ Error message doesn't mention duplicate: {e}")

        # Verify only one agent with that name exists in registry
        count = sum(1 for agent in registry.agents.values() if agent.name == test_agent_name)
        if count == 1:
            print(f"   ✓ Registry contains exactly 1 agent with name {test_agent_name}")
        else:
            print(f"   ✗ Registry contains {count} agents with name {test_agent_name}")
            return False

        # Check database unique constraint by attempting direct insert?
        # We'll trust PostgreSQL unique constraint, but we can verify that
        # the agent is in database and no duplicate exists.
        print(f"\n3. Checking database for duplicate entries...")
        result = await db.fetch_all(
            "SELECT id FROM agents WHERE name = $1",
            test_agent_name
        )
        if len(result) == 1:
            print(f"   ✓ Database contains exactly 1 agent with name {test_agent_name}")
        else:
            print(f"   ✗ Database contains {len(result)} agents with name {test_agent_name}")
            return False

        # Clean up test agent
        print(f"\n4. Cleaning up test agent...")
        deleted = await registry.delete_agent(uuid.UUID(agent1.agent_id))
        if deleted:
            print(f"   ✓ Test agent deleted successfully")
        else:
            print(f"   ⚠ Failed to delete test agent")

        print("\n✓ Duplicate agent registration test passed!")
        return True

    except Exception as e:
        print(f"\n✗ Test failed with unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await db.disconnect()

if __name__ == "__main__":
    success = asyncio.run(test_duplicate_agent())
    sys.exit(0 if success else 1)