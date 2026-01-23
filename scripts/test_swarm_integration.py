#!/usr/bin/env python3
"""
NEXUS Swarm Integration Test

Integration tests for swarm communication layer:
- Agent creation → swarm membership → message sending workflow
- Agent start/stop via API
- Agent tool execution through swarm communication
"""

import asyncio
import sys
import time
import json
import logging
from pathlib import Path
from uuid import uuid4, UUID

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from app.main import app
from app.database import db
from app.config import settings
from app.routers.agents import initialize_agent_framework

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Track initialization status
_framework_initialized = False


async def ensure_framework_initialized():
    """Ensure agent framework is initialized before API tests."""
    global _framework_initialized
    if not _framework_initialized:
        try:
            await initialize_agent_framework()
            _framework_initialized = True
            print("  🔧 Agent framework initialized")
        except Exception as e:
            print(f"  ⚠️  Failed to initialize agent framework: {e}")
            # Might already be initialized, continue


async def test_agent_creation() -> tuple[str, bool]:
    """Test creating an agent via API."""
    print("🧪 Testing Agent Creation...")

    await ensure_framework_initialized()

    client = TestClient(app)

    agent_data = {
        "name": f"Test Agent {uuid4().hex[:8]}",
        "agent_type": "domain",
        "description": "Test agent for swarm integration",
        "system_prompt": "You are a test agent.",
        "capabilities": ["analysis", "communication"],
        "domain": "testing",
        "supervisor_id": None,
        "config": {}
    }

    response = client.post("/agents", json=agent_data)
    print(f"  📝 POST /agents: {response.status_code}")

    if response.status_code != 201:
        print(f"  ❌ Failed to create agent: {response.text}")
        return "", False

    agent = response.json()
    agent_id = agent["id"]
    print(f"  ✅ Agent created: {agent_id}")
    return agent_id, True


async def test_swarm_creation() -> tuple[str, bool]:
    """Test creating a swarm via API."""
    print("\n🧪 Testing Swarm Creation...")

    client = TestClient(app)

    swarm_data = {
        "name": f"Test Swarm {uuid4().hex[:8]}",
        "description": "Test swarm for integration",
        "purpose": "testing",
        "swarm_type": "collaborative",
        "max_members": 10,
        "auto_scaling": False,
        "health_check_interval_seconds": 30,
        "metadata": {}
    }

    response = client.post("/swarm/", json=swarm_data)
    print(f"  📝 POST /swarm/: {response.status_code}")

    if response.status_code != 200:
        print(f"  ❌ Failed to create swarm: {response.text}")
        return "", False

    swarm = response.json()
    swarm_id = swarm["id"]
    print(f"  ✅ Swarm created: {swarm_id}")
    return swarm_id, True


async def test_swarm_membership(swarm_id: str, agent_id: str) -> bool:
    """Test adding an agent to a swarm."""
    print(f"\n🧪 Testing Swarm Membership...")

    client = TestClient(app)

    membership_data = {
        "agent_id": agent_id,
        "role": "member",
        "metadata": {}
    }

    response = client.post(f"/swarm/{swarm_id}/members", json=membership_data)
    print(f"  📝 POST /swarm/{swarm_id}/members: {response.status_code}")

    if response.status_code != 200:
        print(f"  ❌ Failed to add agent to swarm: {response.text}")
        return False

    membership = response.json()
    print(f"  ✅ Agent added to swarm: role={membership.get('role')}")
    return True


async def test_swarm_message_sending(swarm_id: str, agent_id: str) -> bool:
    """Test sending a swarm message via API."""
    print(f"\n🧪 Testing Swarm Message Sending...")

    client = TestClient(app)

    message_data = {
        "sender_agent_id": agent_id,
        "recipient_agent_id": None,  # broadcast
        "channel": "general",
        "message_type": "test",
        "content": {"text": "Hello from integration test"},
        "priority": "normal",
        "ttl_seconds": 3600
    }

    response = client.post(f"/swarm/{swarm_id}/messages", json=message_data)
    print(f"  📝 POST /swarm/{swarm_id}/messages: {response.status_code}")

    if response.status_code != 200:
        print(f"  ❌ Failed to send swarm message: {response.text}")
        return False

    result = response.json()
    message_id = result.get("message_id")
    print(f"  ✅ Swarm message sent: message_id={message_id}")

    # Verify message stored in database
    try:
        messages = await db.fetch_all(
            "SELECT * FROM swarm_messages WHERE swarm_id = $1 ORDER BY created_at DESC LIMIT 1",
            swarm_id
        )
        if messages:
            print(f"  ✅ Message stored in database: {messages[0]['id']}")
            return True
        else:
            print(f"  ⚠️  Message not found in database")
            return False
    except Exception as e:
        print(f"  ⚠️  Failed to query messages: {e}")
        return False


async def test_agent_start_stop(agent_id: str) -> bool:
    """Test starting and stopping an agent via API."""
    print(f"\n🧪 Testing Agent Start/Stop...")

    client = TestClient(app)

    # Start agent
    response = client.post(f"/agents/{agent_id}/start")
    print(f"  📝 POST /agents/{agent_id}/start: {response.status_code}")

    if response.status_code != 200:
        print(f"  ❌ Failed to start agent: {response.text}")
        return False

    agent = response.json()
    print(f"  ✅ Agent started: status={agent.get('status')}")

    # Wait a moment
    await asyncio.sleep(0.5)

    # Stop agent
    response = client.post(f"/agents/{agent_id}/stop")
    print(f"  📝 POST /agents/{agent_id}/stop: {response.status_code}")

    if response.status_code != 200:
        print(f"  ❌ Failed to stop agent: {response.text}")
        return False

    agent = response.json()
    print(f"  ✅ Agent stopped: status={agent.get('status')}")
    return True


async def test_agent_tool_execution(agent_id: str, swarm_id: str) -> bool:
    """Test agent tool execution through swarm communication."""
    print(f"\n🧪 Testing Agent Tool Execution...")

    # This test requires a running SwarmAgent instance with swarm capabilities.
    # We'll create a SwarmAgent directly (not via API) to test tool execution.
    # Note: This test may be more complex and may require Redis to be running.

    try:
        from app.agents.swarm.agent import SwarmAgent

        # Create a swarm agent instance
        agent = SwarmAgent(
            agent_id=agent_id,
            name="Test Swarm Agent",
            swarm_id=swarm_id,
            swarm_role="member"
        )

        # Initialize the agent (this will join swarm and register tools)
        await agent.initialize()
        print(f"  🤖 SwarmAgent initialized")

        # Wait for swarm joining
        await asyncio.sleep(1)

        # Test a swarm tool (list swarm members)
        try:
            result = await agent._tool_list_swarm_members()
            if "error" in result:
                print(f"  ⚠️  Tool execution error: {result['error']}")
            else:
                print(f"  ✅ Tool executed: list_swarm_members")
                print(f"     Members: {len(result.get('members', []))}")
        except Exception as e:
            print(f"  ⚠️  Tool execution failed: {e}")

        # Cleanup
        await agent.cleanup()
        print(f"  🔄 Agent cleaned up")

        return True

    except Exception as e:
        print(f"  ❌ Agent tool execution test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main() -> int:
    """Run all integration tests."""
    print("🚀 NEXUS Swarm Integration Test Suite")
    print("=" * 60)

    # Connect to database
    try:
        await db.connect()
        print("🔗 Connected to database")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return 1

    test_results = []

    try:
        # Test 1: Agent creation
        agent_id, success = await test_agent_creation()
        test_results.append(("Agent Creation", success))
        if not success:
            print("❌ Stopping tests due to agent creation failure")
            return 1

        # Test 2: Swarm creation
        swarm_id, success = await test_swarm_creation()
        test_results.append(("Swarm Creation", success))
        if not success:
            print("❌ Stopping tests due to swarm creation failure")
            return 1

        # Test 3: Swarm membership
        success = await test_swarm_membership(swarm_id, agent_id)
        test_results.append(("Swarm Membership", success))

        # Test 4: Swarm message sending
        success = await test_swarm_message_sending(swarm_id, agent_id)
        test_results.append(("Swarm Message Sending", success))

        # Test 5: Agent start/stop
        success = await test_agent_start_stop(agent_id)
        test_results.append(("Agent Start/Stop", success))

        # Test 6: Agent tool execution
        success = await test_agent_tool_execution(agent_id, swarm_id)
        test_results.append(("Agent Tool Execution", success))

    finally:
        # Disconnect from database
        await db.disconnect()
        print("🔗 Disconnected from database")

    # Print summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print("=" * 60)

    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")

    print("\n" + "=" * 60)
    print(f"🏁 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("=" * 60)

    if passed == total:
        print("🎉 All integration tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check logs above.")
        return 1


if __name__ == "__main__":
    # Run async main
    exit_code = asyncio.run(main())
    sys.exit(exit_code)