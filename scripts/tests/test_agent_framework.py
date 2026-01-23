#!/usr/bin/env python3
"""
NEXUS Agent Framework Test Script
Tests all agent framework and evolution system endpoints.
"""

import asyncio
import aiohttp
import json
import sys
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import UUID

# Configuration
BASE_URL = "http://localhost:8080"
TIMEOUT = 30  # seconds

# Test data
TEST_AGENT_DATA = {
    "name": "test-agent-" + datetime.now().strftime("%H%M%S"),
    "agent_type": "domain",
    "description": "Test agent created by agent framework test script",
    "system_prompt": "You are a test agent for the NEXUS system.",
    "capabilities": ["testing", "analysis", "reporting"],
    "domain": "testing",
    "config": {"test_mode": True, "max_iterations": 5}
}

TEST_TASK_DATA = {
    "task": {
        "description": "Test task for agent framework validation",
        "type": "analysis",
        "parameters": {"test": True, "iterations": 3}
    },
    "priority": 3,
    "context": {"source": "test_script", "timestamp": datetime.now().isoformat()}
}

TEST_SESSION_DATA = {
    "title": "Test Session " + datetime.now().strftime("%H:%M:%S"),
    "session_type": "testing",
    "metadata": {"test": True, "purpose": "agent framework validation"}
}

TEST_TOOL_DATA = {
    "name": "test_tool_" + datetime.now().strftime("%H%M%S"),
    "display_name": "Test Tool",
    "description": "A test tool for validation",
    "tool_type": "analysis",
    "input_schema": {"type": "object", "properties": {"input": {"type": "string"}}},
    "output_schema": {"type": "object", "properties": {"result": {"type": "string"}}},
    "requires_confirmation": False
}


class AgentFrameworkTester:
    """Comprehensive tester for NEXUS agent framework endpoints."""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = None
        self.test_results = []
        self.created_agents = []
        self.created_sessions = []
        self.created_tools = []

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=10)
        timeout = aiohttp.ClientTimeout(total=TIMEOUT)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def record_result(self, name: str, success: bool, details: Dict[str, Any] = None):
        """Record a test result."""
        result = {
            "name": name,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.test_results.append(result)
        return result

    async def test_endpoint(self, method: str, path: str, name: str,
                           expected_status: int = 200, data: Dict = None,
                           headers: Dict = None) -> Dict[str, Any]:
        """Test a single endpoint."""
        url = f"{self.base_url}{path}"
        headers = headers or {"Content-Type": "application/json"}

        try:
            if method == 'GET':
                async with self.session.get(url, headers=headers, timeout=TIMEOUT) as response:
                    status = response.status
                    text = await response.text()
            elif method == 'POST':
                async with self.session.post(url, json=data, headers=headers, timeout=TIMEOUT) as response:
                    status = response.status
                    text = await response.text()
            elif method == 'PUT':
                async with self.session.put(url, json=data, headers=headers, timeout=TIMEOUT) as response:
                    status = response.status
                    text = await response.text()
            elif method == 'DELETE':
                async with self.session.delete(url, headers=headers, timeout=TIMEOUT) as response:
                    status = response.status
                    text = await response.text()
            else:
                return self.record_result(name, False, {
                    "error": f"Unsupported method: {method}",
                    "url": url
                })

            # Parse JSON if possible
            try:
                json_data = json.loads(text) if text else {}
            except json.JSONDecodeError:
                json_data = {"raw_response": text[:200] + "..." if len(text) > 200 else text}

            success = status == expected_status
            details = {
                "method": method,
                "url": url,
                "expected_status": expected_status,
                "actual_status": status,
                "response": json_data if success or status < 500 else {},
                "error": None if success else f"Expected {expected_status}, got {status}"
            }

            return self.record_result(name, success, details)

        except asyncio.TimeoutError:
            return self.record_result(name, False, {
                "error": f"Timeout after {TIMEOUT} seconds",
                "url": url
            })
        except Exception as e:
            return self.record_result(name, False, {
                "error": f"Exception: {str(e)}",
                "url": url
            })

    # ============ Agent Management Tests ============

    async def test_agent_management(self):
        """Test agent creation, listing, and management."""
        print("\n" + "="*60)
        print("Testing Agent Management Endpoints")
        print("="*60)

        # 1. List agents (should work even if no agents exist)
        await self.test_endpoint("GET", "/agents", "List Agents")

        # 2. Create a test agent
        create_result = await self.test_endpoint(
            "POST", "/agents", "Create Agent",
            data=TEST_AGENT_DATA, expected_status=201
        )

        if create_result["success"]:
            agent_id = create_result["details"]["response"].get("id")
            if agent_id:
                self.created_agents.append(agent_id)
                print(f"✓ Created test agent: {agent_id}")

                # 3. Get the created agent
                await self.test_endpoint("GET", f"/agents/{agent_id}", "Get Agent")

                # 4. Update the agent
                update_data = {
                    "description": "Updated description from test script",
                    "config": {"test_mode": True, "max_iterations": 10, "updated": True}
                }
                await self.test_endpoint(
                    "PUT", f"/agents/{agent_id}", "Update Agent",
                    data=update_data
                )

                # 5. Get agent status
                await self.test_endpoint("GET", f"/agents/{agent_id}/status", "Get Agent Status")

                # 6. Start agent
                await self.test_endpoint("POST", f"/agents/{agent_id}/start", "Start Agent")

                # 7. Stop agent
                await self.test_endpoint("POST", f"/agents/{agent_id}/stop", "Stop Agent")

                # 8. Get agent errors (should be empty)
                await self.test_endpoint("GET", f"/agents/{agent_id}/errors", "Get Agent Errors")

        # 9. Test registry status
        await self.test_endpoint("GET", "/registry-status", "Get Registry Status")

    # ============ Session Management Tests ============

    async def test_session_management(self):
        """Test session creation and management."""
        print("\n" + "="*60)
        print("Testing Session Management Endpoints")
        print("="*60)

        # 1. Create a session
        create_result = await self.test_endpoint(
            "POST", "/sessions", "Create Session",
            data=TEST_SESSION_DATA, expected_status=201
        )

        if create_result["success"]:
            session_id = create_result["details"]["response"].get("id")
            if session_id:
                self.created_sessions.append(session_id)
                print(f"✓ Created test session: {session_id}")

                # 2. Get the session
                await self.test_endpoint("GET", f"/sessions/{session_id}", "Get Session")

                # 3. List all sessions
                await self.test_endpoint("GET", "/sessions", "List Sessions")

                # 4. Add a message to the session
                message_data = {
                    "content": "Test message from agent framework test",
                    "role": "user",
                    "agent_id": None
                }
                await self.test_endpoint(
                    "POST", f"/sessions/{session_id}/messages", "Add Message",
                    data=message_data
                )

                # 5. Get messages from session
                await self.test_endpoint(
                    "GET", f"/sessions/{session_id}/messages", "Get Session Messages"
                )

                # 6. End the session
                await self.test_endpoint("POST", f"/sessions/{session_id}/end", "End Session")

    # ============ Task Execution Tests ============

    async def test_task_execution(self):
        """Test task submission and management."""
        print("\n" + "="*60)
        print("Testing Task Execution Endpoints")
        print("="*60)

        # 1. Submit a task (without specifying agent - should auto-select)
        submit_result = await self.test_endpoint(
            "POST", "/tasks", "Submit Task",
            data=TEST_TASK_DATA
        )

        if submit_result["success"]:
            task_id = submit_result["details"]["response"].get("task_id")
            if task_id:
                print(f"✓ Submitted task: {task_id}")

                # 2. Get task status
                await self.test_endpoint("GET", f"/tasks/{task_id}", "Get Task Status")

                # 3. Try to cancel task (may fail if already completed)
                await self.test_endpoint("POST", f"/tasks/{task_id}/cancel", "Cancel Task")

    # ============ Tool Management Tests ============

    async def test_tool_management(self):
        """Test tool registration and execution."""
        print("\n" + "="*60)
        print("Testing Tool Management Endpoints")
        print("="*60)

        # 1. List tools
        await self.test_endpoint("GET", "/tools", "List Tools")

        # 2. Create a test tool
        create_result = await self.test_endpoint(
            "POST", "/tools", "Create Tool",
            data=TEST_TOOL_DATA, expected_status=201
        )

        if create_result["success"]:
            tool_id = create_result["details"]["response"].get("id")
            if tool_id:
                self.created_tools.append(tool_id)
                print(f"✓ Created test tool: {tool_id}")

                # 3. Execute tool (will likely fail without proper implementation)
                execute_data = {
                    "tool_name": TEST_TOOL_DATA["name"],
                    "parameters": {"input": "test input"},
                    "require_confirmation": False
                }
                await self.test_endpoint(
                    "POST", "/tools/execute", "Execute Tool",
                    data=execute_data
                )

    # ============ Performance Monitoring Tests ============

    async def test_performance_monitoring(self):
        """Test performance monitoring endpoints."""
        print("\n" + "="*60)
        print("Testing Performance Monitoring Endpoints")
        print("="*60)

        # 1. Get system performance
        await self.test_endpoint("GET", "/system/performance", "Get System Performance")

        # 2. Get system alerts
        await self.test_endpoint("GET", "/system/alerts", "Get System Alerts")

        # 3. Test agent selection
        selection_data = {
            "task_description": "Test task for agent selection",
            "required_capabilities": ["testing", "analysis"],
            "preferred_domain": "testing"
        }
        await self.test_endpoint(
            "POST", "/registry-select-agent", "Select Agent",
            data=selection_data
        )

    # ============ Memory System Tests ============

    async def test_memory_system(self):
        """Test memory system endpoints."""
        print("\n" + "="*60)
        print("Testing Memory System Endpoints")
        print("="*60)

        if self.created_agents:
            agent_id = self.created_agents[0]

            # 1. Get agent memory
            await self.test_endpoint("GET", f"/memory/{agent_id}", "Get Agent Memory")

            # 2. Query memory
            query_data = {"text": "test query", "limit": 5, "threshold": 0.7}
            await self.test_endpoint(
                "POST", f"/memory/{agent_id}/query", "Query Memory",
                data=query_data
            )

            # 3. Store memory
            memory_data = {
                "content": "Test memory stored by test script",
                "type": "observation",
                "metadata": {"test": True, "source": "test_script"}
            }
            await self.test_endpoint(
                "POST", f"/memory/{agent_id}/store", "Store Memory",
                data=memory_data
            )

    # ============ Evolution System Tests ============

    async def test_evolution_system(self):
        """Test evolution system endpoints."""
        print("\n" + "="*60)
        print("Testing Evolution System Endpoints")
        print("="*60)

        # 1. Get evolution status
        await self.test_endpoint("GET", "/evolution/status", "Get Evolution Status")

        # 2. Get recent analyses
        await self.test_endpoint("GET", "/evolution/analysis/recent", "Get Recent Analyses")

        # 3. Get hypotheses
        await self.test_endpoint("GET", "/evolution/hypotheses", "Get Hypotheses")

        # 4. Get experiments
        await self.test_endpoint("GET", "/evolution/experiments", "Get Experiments")

        # 5. Get refactor history
        await self.test_endpoint("GET", "/evolution/refactor/history", "Get Refactor History")

        # Note: POST endpoints for evolution system require actual data
        # and may fail without proper implementation

    # ============ Cleanup Tests ============

    async def test_cleanup(self):
        """Test cleanup operations (delete created resources)."""
        print("\n" + "="*60)
        print("Testing Cleanup Operations")
        print("="*60)

        # Delete created agents
        for agent_id in self.created_agents:
            await self.test_endpoint("DELETE", f"/agents/{agent_id}", f"Delete Agent {agent_id}", expected_status=204)

        # Note: Sessions and tools may not have delete endpoints
        # or may be automatically cleaned up

    # ============ Main Test Runner ============

    async def run_all_tests(self):
        """Run all agent framework tests."""
        print("🚀 Starting NEXUS Agent Framework Comprehensive Test...")
        print(f"Testing against: {self.base_url}")
        print()

        try:
            # Run test suites in sequence
            await self.test_agent_management()
            await self.test_session_management()
            await self.test_task_execution()
            await self.test_tool_management()
            await self.test_performance_monitoring()
            await self.test_memory_system()
            await self.test_evolution_system()
            # await self.test_cleanup()  # Optional cleanup

            # Print summary
            self.print_summary()

        except Exception as e:
            print(f"\n❌ Test execution failed: {e}")
            import traceback
            traceback.print_exc()

    def print_summary(self):
        """Print test results summary."""
        print("\n" + "="*70)
        print("AGENT FRAMEWORK TEST SUMMARY")
        print("="*70)
        print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Base URL: {self.base_url}")
        print(f"Total tests: {len(self.test_results)}")
        print()

        successes = [r for r in self.test_results if r['success']]
        failures = [r for r in self.test_results if not r['success']]

        print(f"✅ PASSED: {len(successes)}")
        print(f"❌ FAILED: {len(failures)}")
        print()

        if failures:
            print("FAILED TESTS:")
            print("-" * 40)
            for fail in failures:
                print(f"  ❌ {fail['name']}")
                if fail['details'].get('error'):
                    print(f"     Error: {fail['details']['error']}")
                if fail['details'].get('response'):
                    resp = fail['details']['response']
                    if isinstance(resp, dict) and resp:
                        resp_str = json.dumps(resp, indent=2)
                        if len(resp_str) > 200:
                            resp_str = resp_str[:200] + "..."
                        print(f"     Response: {resp_str}")
                print()

        print("TEST CATEGORIES:")
        print("-" * 40)

        categories = {}
        for result in self.test_results:
            category = result['name'].split()[0] if ' ' in result['name'] else 'Other'
            if category not in categories:
                categories[category] = {'total': 0, 'passed': 0}
            categories[category]['total'] += 1
            if result['success']:
                categories[category]['passed'] += 1

        for category, stats in sorted(categories.items()):
            percentage = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            status = "✅" if percentage == 100 else "⚠️ " if percentage >= 50 else "❌"
            print(f"  {status} {category}: {stats['passed']}/{stats['total']} ({percentage:.1f}%)")

        print()
        print("="*70)
        print("RECOMMENDATIONS:")
        print("-" * 40)

        if len(failures) == 0:
            print("🎉 All tests passed! Agent framework is fully operational.")
        else:
            # Analyze common failure patterns
            error_patterns = {}
            for fail in failures:
                error = fail['details'].get('error', 'Unknown')
                if error not in error_patterns:
                    error_patterns[error] = 0
                error_patterns[error] += 1

            if error_patterns:
                print("Common issues found:")
                for error, count in sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)[:3]:
                    print(f"  • {error} ({count} occurrences)")

            # Check for missing implementations
            not_found_errors = [f for f in failures if f['details'].get('actual_status') == 404]
            if not_found_errors:
                print(f"\n⚠️  {len(not_found_errors)} endpoints returned 404 (Not Found)")
                print("   This may indicate missing router imports in main.py")

            server_errors = [f for f in failures if f['details'].get('actual_status') == 500]
            if server_errors:
                print(f"\n⚠️  {len(server_errors)} endpoints returned 500 (Internal Server Error)")
                print("   This may indicate missing implementations or database issues")

        print("="*70)


async def main():
    """Main entry point."""
    async with AgentFrameworkTester() as tester:
        await tester.run_all_tests()

    # Exit with appropriate code
    failures = len([r for r in tester.test_results if not r['success']])
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())