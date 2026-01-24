#!/usr/bin/env python3
"""
Test Finance Agent creation and basic functionality.
"""

import asyncio
import sys
sys.path.insert(0, '/home/philip/nexus')

async def test_finance_agent():
    """Test finance agent creation."""
    try:
        from app.agents.finance_agent import FinanceAgent, register_finance_agent
        from app.agents.registry import registry

        print("Testing Finance Agent creation...")

        # Test 1: Create agent instance
        agent = FinanceAgent()
        print(f"✓ Created FinanceAgent: {agent.name}")
        print(f"  Agent ID: {agent.agent_id}")
        print(f"  Capabilities: {agent.capabilities}")
        print(f"  Domain: {agent.domain}")

        # Test 2: Initialize agent
        await agent.initialize()
        print(f"✓ Initialized agent, status: {agent.status}")

        # Test 3: Check tool registration
        from app.agents.tools import ToolSystem
        tool_system = ToolSystem()
        await tool_system.initialize()

        tools = await tool_system.list_tools(agent_id=agent.agent_id)
        print(f"✓ Registered tools for agent: {len(tools)} tools")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description'][:50]}...")

        # Test 4: Test registry registration
        await registry.initialize()
        existing_agent = await registry.get_agent_by_name("Finance Agent")
        if existing_agent:
            print(f"✓ Agent found in registry: {existing_agent.name}")
        else:
            print("✗ Agent not found in registry")

        # Test 5: Test register_finance_agent function
        registered_agent = await register_finance_agent()
        print(f"✓ Registered finance agent via helper: {registered_agent.name}")

        # Cleanup
        await agent.cleanup()
        await registry.shutdown()

        print("\n✅ All tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_finance_agent())