#!/usr/bin/env python3
"""
NEXUS Swarm Integration Test (Live API)

Integration tests for swarm communication layer using live API (port 8080):
- Agent creation → swarm membership → message sending workflow
- Agent start/stop via API
- Agent tool execution through swarm communication
"""

import asyncio
import sys
import json
import logging
from uuid import uuid4, UUID
import httpx
from typing import Optional, Dict, Any, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "http://localhost:8080"
TIMEOUT = 30.0


class SwarmIntegrationTest:
    """Test suite for swarm integration using live API."""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        self.created_agents = []
        self.created_swarms = []
        self.test_results = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def _log_test(self, name: str, success: bool, message: str = ""):
        """Log test result and store."""
        status = "✅ PASS" if success else "❌ FAIL"
        log_msg = f"{status} {name}"
        if message:
            log_msg += f": {message}"
        print(f"  {log_msg}")
        self.test_results.append((name, success))
        return success

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Tuple[Optional[Dict], bool]:
        """Make HTTP request and handle errors."""
        url = f"{BASE_URL}{endpoint}"
        try:
            response = await self.client.request(method, url, **kwargs)
            if response.status_code >= 400:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("detail", str(error_json))
                except:
                    pass
                # Log full response for debugging
                logger.error(f"Request failed: {method} {url} -> {response.status_code}: {error_detail}")
                if response.status_code == 500:
                    logger.error(f"Full response text: {response.text}")
                return None, False
            if response.status_code == 204:
                return {}, True
            return response.json(), True
        except Exception as e:
            logger.error(f"Request exception: {method} {url}: {e}")
            return None, False

    async def test_agent_creation(self) -> Tuple[Optional[str], bool]:
        """Test creating an agent via API."""
        print("🧪 Testing Agent Creation...")

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

        response, success = await self._make_request("POST", "/agents", json=agent_data)
        if not success:
            return None, await self._log_test("Agent Creation", False, "API request failed")

        agent_id = response.get("id")
        if not agent_id:
            return None, await self._log_test("Agent Creation", False, "No agent ID in response")

        self.created_agents.append(agent_id)
        await self._log_test("Agent Creation", True, f"Agent ID: {agent_id}")
        return agent_id, True

    async def test_swarm_creation(self) -> Tuple[Optional[str], bool]:
        """Test creating a swarm via API."""
        print("\n🧪 Testing Swarm Creation...")

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

        response, success = await self._make_request("POST", "/swarm/", json=swarm_data)
        if not success:
            return None, await self._log_test("Swarm Creation", False, "API request failed")

        swarm_id = response.get("id")
        if not swarm_id:
            return None, await self._log_test("Swarm Creation", False, "No swarm ID in response")

        self.created_swarms.append(swarm_id)
        await self._log_test("Swarm Creation", True, f"Swarm ID: {swarm_id}")
        return swarm_id, True

    async def test_swarm_membership(self, swarm_id: str, agent_id: str) -> bool:
        """Test adding an agent to a swarm."""
        print("\n🧪 Testing Swarm Membership...")

        membership_data = {
            "agent_id": agent_id,
            "role": "member",
            "metadata": {}
        }

        response, success = await self._make_request("POST", f"/swarm/{swarm_id}/members", json=membership_data)
        if not success:
            return await self._log_test("Swarm Membership", False, "API request failed")

        role = response.get("role")
        return await self._log_test("Swarm Membership", True, f"Agent added as {role}")

    async def test_swarm_message_sending(self, swarm_id: str, agent_id: str) -> bool:
        """Test sending a swarm message via API."""
        print("\n🧪 Testing Swarm Message Sending...")

        message_data = {
            "sender_agent_id": agent_id,
            "recipient_agent_id": None,
            "channel": "general",
            "message_type": "test",
            "content": "Hello from integration test",
            "priority": "normal",
            "ttl_seconds": 3600
        }

        response, success = await self._make_request("POST", f"/swarm/{swarm_id}/messages", json=message_data)
        if not success:
            return await self._log_test("Swarm Message Sending", False, "API request failed")

        message_id = response.get("message_id")
        return await self._log_test("Swarm Message Sending", True, f"Message ID: {message_id}")

    async def test_agent_start_stop(self, agent_id: str) -> bool:
        """Test starting and stopping an agent via API."""
        print("\n🧪 Testing Agent Start/Stop...")

        # Start agent
        response, success = await self._make_request("POST", f"/agents/{agent_id}/start")
        if not success:
            return await self._log_test("Agent Start", False, "API request failed")
        status = response.get("status")
        await self._log_test("Agent Start", True, f"Status: {status}")

        # Wait a moment
        await asyncio.sleep(1)

        # Stop agent
        response, success = await self._make_request("POST", f"/agents/{agent_id}/stop")
        if not success:
            return await self._log_test("Agent Stop", False, "API request failed")
        status = response.get("status")
        return await self._log_test("Agent Stop", True, f"Status: {status}")

    async def test_agent_tool_execution(self, agent_id: str, swarm_id: str) -> bool:
        """Test agent tool execution through swarm communication."""
        print("\n🧪 Testing Agent Tool Execution...")

        # This test requires Redis and swarm Pub/Sub to be running.
        # We'll attempt to create a SwarmAgent directly (bypassing API) to test tools.
        # This is a more complex integration test.

        try:
            # Add project root to Python path
            import sys
            from pathlib import Path
            project_root = Path(__file__).parent.parent
            sys.path.insert(0, str(project_root))

            from app.agents.swarm.agent import SwarmAgent

            # Create swarm agent instance
            agent = SwarmAgent(
                agent_id=agent_id,
                name="Test Swarm Agent",
                swarm_id=swarm_id,
                swarm_role="member"
            )

            # Initialize agent (joins swarm, registers tools)
            await agent.initialize()
            print(f"  🤖 SwarmAgent initialized")

            # Wait for swarm joining
            await asyncio.sleep(2)

            # Test a swarm tool (list swarm members)
            try:
                result = await agent._tool_list_swarm_members()
                if "error" in result:
                    print(f"  ⚠️  Tool execution error: {result['error']}")
                    success = False
                else:
                    member_count = len(result.get('members', []))
                    print(f"  ✅ Tool executed: list_swarm_members ({member_count} members)")
                    success = True
            except Exception as e:
                print(f"  ⚠️  Tool execution failed: {e}")
                success = False

            # Cleanup
            await agent.cleanup()
            print(f"  🔄 Agent cleaned up")

            return await self._log_test("Agent Tool Execution", success,
                                       "Direct SwarmAgent tool test" if success else "Tool test failed")

        except Exception as e:
            print(f"  ❌ Agent tool execution test failed: {e}")
            import traceback
            traceback.print_exc()
            return await self._log_test("Agent Tool Execution", False, f"Exception: {e}")

    async def run_all_tests(self) -> bool:
        """Execute all integration tests."""
        print("🚀 NEXUS Swarm Integration Test Suite (Live API)")
        print("=" * 60)

        # Check API health first
        print("🔍 Checking API health...")
        response, success = await self._make_request("GET", "/health")
        if not success:
            print("❌ API health check failed. Make sure the API is running on port 8080.")
            return False
        print(f"  ✅ API healthy: {response.get('status')}")

        # Run tests in sequence
        agent_id = None
        swarm_id = None

        try:
            # Test 1: Agent creation
            agent_id, success = await self.test_agent_creation()
            if not success:
                return False

            # Test 2: Swarm creation
            swarm_id, success = await self.test_swarm_creation()
            if not success:
                return False

            # Test 3: Swarm membership
            success = await self.test_swarm_membership(swarm_id, agent_id)
            if not success:
                # Continue anyway
                pass

            # Test 4: Swarm message sending
            success = await self.test_swarm_message_sending(swarm_id, agent_id)
            if not success:
                # Continue anyway
                pass

            # Test 5: Agent start/stop
            success = await self.test_agent_start_stop(agent_id)
            if not success:
                # Continue anyway
                pass

            # Test 6: Agent tool execution
            success = await self.test_agent_tool_execution(agent_id, swarm_id)
            if not success:
                # Continue anyway
                pass

        except Exception as e:
            print(f"❌ Test suite exception: {e}")
            import traceback
            traceback.print_exc()
            return False

        return True

    def print_summary(self):
        """Print test results summary."""
        print("\n" + "=" * 60)
        print("📊 Test Results Summary:")
        print("=" * 60)

        passed = sum(1 for _, result in self.test_results if result)
        total = len(self.test_results)

        for test_name, result in self.test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status} {test_name}")

        print("\n" + "=" * 60)
        print(f"🏁 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        print("=" * 60)

        if passed == total:
            print("🎉 All integration tests passed!")
        else:
            print("⚠️  Some tests failed. Check logs above.")


async def main() -> int:
    """Main async entry point."""
    async with SwarmIntegrationTest() as tester:
        success = await tester.run_all_tests()
        tester.print_summary()
        return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)