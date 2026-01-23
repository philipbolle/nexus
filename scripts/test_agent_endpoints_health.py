#!/usr/bin/env python3
"""
Test agent API endpoints return appropriate HTTP status codes.
Tests GET endpoints and safe POST endpoints.
"""
import asyncio
import httpx
import sys
import uuid
from typing import List, Tuple, Dict, Any

BASE_URL = "http://localhost:8080"

async def test_endpoint(client: httpx.AsyncClient, method: str, path: str,
                       expected_status: int = 200, json_data: Dict = None) -> bool:
    """Test a single endpoint and return success status."""
    try:
        if method == "GET":
            resp = await client.get(path)
        elif method == "POST":
            resp = await client.post(path, json=json_data if json_data else {})
        elif method == "PUT":
            resp = await client.put(path, json=json_data if json_data else {})
        elif method == "DELETE":
            resp = await client.delete(path)
        else:
            print(f"  ⚠ Unknown method {method} for {path}")
            return False

        if resp.status_code == expected_status:
            print(f"  ✅ {method} {path} - {resp.status_code}")
            return True
        else:
            print(f"  ❌ {method} {path} - expected {expected_status}, got {resp.status_code}")
            if resp.status_code >= 400:
                try:
                    error_detail = resp.json()
                    print(f"     Error detail: {error_detail}")
                except:
                    print(f"     Response text: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"  ❌ {method} {path} - exception: {e}")
        return False

async def test_agent_endpoints():
    """Test agent framework endpoints."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        print("Testing agent framework endpoints...")

        # First, get list of agents to have valid agent_id
        resp = await client.get("/agents")
        if resp.status_code != 200:
            print("❌ Cannot fetch agents list, aborting")
            return False
        agents = resp.json().get("agents", [])
        if not agents:
            print("⚠ No agents found, some tests will be skipped")
            agent_id = None
        else:
            agent = agents[0]  # Use first agent (router)
            agent_id = agent["id"]
            print(f"Using agent ID: {agent_id} ({agent['name']})")

        # Define endpoints to test
        endpoints = [
            # GET endpoints (safe)
            ("GET", "/agents", 200),
            ("GET", "/registry-status", 200),
            ("GET", "/tools", 200),
            ("GET", "/system/performance", 200),
            ("GET", "/system/alerts", 200),  # may 404 if table missing
            ("GET", "/swarm/", 200),
            ("GET", "/distributed-tasks/queues", 200),
            ("GET", "/evolution/status", 200),
        ]

        # Add agent-specific GET endpoints if we have an agent_id
        if agent_id:
            endpoints.extend([
                ("GET", f"/agents/{agent_id}", 200),
                ("GET", f"/agents/{agent_id}/status", 200),
                ("GET", f"/agents/{agent_id}/performance", 200),
                ("GET", f"/memory/{agent_id}", 200),  # may error due to missing method
                ("GET", f"/agents/{agent_id}/errors", 200),
            ])

        # Test all endpoints
        results = []
        for method, path, expected in endpoints:
            success = await test_endpoint(client, method, path, expected)
            results.append(success)

        # Test POST /agents with random name (safe creation and deletion)
        print("\nTesting agent creation and deletion...")
        test_agent_name = f"test_{uuid.uuid4().hex[:8]}"
        create_data = {
            "name": test_agent_name,
            "agent_type": "domain",
            "description": "Test agent for endpoint validation",
            "system_prompt": "You are a test agent.",
            "capabilities": ["test"],
            "domain": "test"
        }
        # Create agent
        success_create = await test_endpoint(client, "POST", "/agents", 201, create_data)
        results.append(success_create)

        if success_create:
            # Get the new agent ID from response (we'd need to parse)
            # Instead, fetch agents list and find by name
            resp = await client.get("/agents")
            if resp.status_code == 200:
                agents = resp.json().get("agents", [])
                test_agent = next((a for a in agents if a["name"] == test_agent_name), None)
                if test_agent:
                    test_agent_id = test_agent["id"]
                    # Delete test agent
                    success_delete = await test_endpoint(client, "DELETE", f"/agents/{test_agent_id}", 200)
                    results.append(success_delete)
                else:
                    print("  ⚠ Created agent not found in list")
                    results.append(False)
            else:
                results.append(False)

        # Test swarm GET endpoints
        swarm_endpoints = [
            ("GET", "/swarm/", 200),
            # Other swarm endpoints may require swarm_id, skip for now
        ]
        print("\nTesting swarm endpoints...")
        for method, path, expected in swarm_endpoints:
            success = await test_endpoint(client, method, path, expected)
            results.append(success)

        # Calculate success rate
        total = len(results)
        passed = sum(results)
        print(f"\n📊 Results: {passed}/{total} endpoints passed ({passed/total*100:.1f}%)")
        return passed == total

async def main():
    try:
        success = await test_agent_endpoints()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())