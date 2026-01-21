#!/usr/bin/env python3
"""
Debug agent framework initialization.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.registry import AgentRegistry
from app.agents.tools import ToolSystem
from app.database import db

async def test_initialization():
    """Test agent registry initialization."""
    print("Testing agent registry initialization...")

    # First ensure database is connected
    print("Connecting to database...")
    await db.connect()

    # Create registry instance
    registry = AgentRegistry()
    print(f"Registry status before init: {registry.status}")

    try:
        await registry.initialize()
        print(f"Registry status after init: {registry.status}")
        print(f"Agent types registered: {list(registry.agent_types.keys())}")
        print(f"Agents loaded: {len(registry.agents)}")
    except Exception as e:
        print(f"Error during registry initialization: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Try to create an agent
    print("\nTrying to create an agent...")
    try:
        agent = await registry.register_agent(
            name="test-agent-debug",
            agent_type="domain",
            description="Test agent for debugging",
            system_prompt="You are a test agent.",
            capabilities=["testing", "debugging"],
            domain="testing",
            config={}
        )
        print(f"Agent created successfully: {agent.name} ({agent.agent_id})")
        print(f"Agent type: {agent.__class__.__name__}")
        print(f"Agent status: {agent.status}")
        return True
    except Exception as e:
        print(f"Error creating agent: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await db.disconnect()

async def test_tool_system():
    """Test tool system initialization."""
    print("\nTesting tool system initialization...")
    tool_system = ToolSystem()
    try:
        await tool_system.initialize()
        print("Tool system initialized")
        tools = await tool_system.list_tools()
        print(f"Tools available: {len(tools)}")
        return True
    except Exception as e:
        print(f"Error initializing tool system: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("🔧 Debugging NEXUS Agent Framework")
    print("=" * 50)

    success = True

    # Test registry
    if not await test_initialization():
        success = False

    # Test tool system
    if not await test_tool_system():
        success = False

    print("=" * 50)
    if success:
        print("✅ All tests passed")
    else:
        print("❌ Some tests failed")

    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)