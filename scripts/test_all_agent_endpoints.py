#!/usr/bin/env python3
"""
Test all agent framework endpoints from CLAUDE.md.
Checks that endpoints return appropriate HTTP status codes (2xx, 4xx, not 5xx).
"""
import asyncio
import httpx
import sys
import uuid
from typing import List, Tuple, Dict, Any

BASE_URL = "http://localhost:8080"

async def test_endpoint(client: httpx.AsyncClient, method: str, path: str,
                       json_data: Dict = None, expected_ok: bool = True) -> Tuple[bool, int]:
    """Test a single endpoint and return (success, status_code)."""
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
            return False, 0

        status = resp.status_code
        # Success criteria: status not 5xx (server error)
        success = status < 500
        if success:
            print(f"  ✅ {method} {path} - {status}")
        else:
            print(f"  ❌ {method} {path} - {status} (server error)")
            try:
                error_detail = resp.json()
                print(f"     Error detail: {error_detail}")
            except:
                print(f"     Response text: {resp.text[:200]}")
        return success, status

    except Exception as e:
        print(f"  ❌ {method} {path} - exception: {e}")
        return False, 0

async def test_all_endpoints():
    """Test all agent framework endpoints."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        print("Testing all agent framework endpoints...")

        # First, fetch necessary IDs
        print("Fetching existing IDs...")
        resp = await client.get("/agents")
        if resp.status_code != 200:
            print("❌ Cannot fetch agents list")
            return False
        agents = resp.json().get("agents", [])
        agent_id = agents[0]["id"] if agents else None
        print(f"Using agent ID: {agent_id}")

        resp = await client.get("/sessions")
        if resp.status_code != 200:
            print("❌ Cannot fetch sessions list")
            session_id = None
        else:
            sessions = resp.json()
            session_id = sessions[0]["id"] if sessions else None
            print(f"Using session ID: {session_id}")

        # Define endpoints from CLAUDE.md (31 endpoints)
        # Format: (method, path, json_data or None)
        endpoints = []

        # 1. GET /agents
        endpoints.append(("GET", "/agents", None))
        # 2. POST /agents (will create temporary agent)
        # 3. GET /registry-status
        endpoints.append(("GET", "/registry-status", None))
        # 4. POST /registry-select-agent (needs task_description)
        endpoints.append(("POST", "/registry-select-agent", {"task_description": "Test task"}))
        # 5. GET /agents/{agent_id}
        if agent_id:
            endpoints.append(("GET", f"/agents/{agent_id}", None))
        # 6. PUT /agents/{agent_id} (update)
        if agent_id:
            endpoints.append(("PUT", f"/agents/{agent_id}", {"description": "Updated description"}))
        # 7. DELETE /agents/{agent_id} (skip to avoid deletion)
        # 8. POST /agents/{agent_id}/start
        if agent_id:
            endpoints.append(("POST", f"/agents/{agent_id}/start", None))
        # 9. POST /agents/{agent_id}/stop
        if agent_id:
            endpoints.append(("POST", f"/agents/{agent_id}/stop", None))
        # 10. GET /agents/{agent_id}/status
        if agent_id:
            endpoints.append(("GET", f"/agents/{agent_id}/status", None))
        # 11. POST /tasks (submit task)
        endpoints.append(("POST", "/tasks", {"task_description": "Test task", "agent_id": agent_id}))
        # 12. GET /tasks/{task_id} (need task_id, skip)
        # 13. POST /tasks/{task_id}/cancel (skip)
        # 14. POST /sessions (create session)
        endpoints.append(("POST", "/sessions", {"title": "Test session", "session_type": "chat"}))
        # 15. GET /sessions/{session_id}
        if session_id:
            endpoints.append(("GET", f"/sessions/{session_id}", None))
        # 16. GET /sessions
        endpoints.append(("GET", "/sessions", None))
        # 17. POST /sessions/{session_id}/messages
        if session_id:
            endpoints.append(("POST", f"/sessions/{session_id}/messages", {"content": "Test message", "role": "user"}))
        # 18. GET /sessions/{session_id}/messages
        if session_id:
            endpoints.append(("GET", f"/sessions/{session_id}/messages", None))
        # 19. POST /sessions/{session_id}/end
        if session_id:
            endpoints.append(("POST", f"/sessions/{session_id}/end", None))
        # 20. GET /tools
        endpoints.append(("GET", "/tools", None))
        # 21. POST /tools (register tool)
        endpoints.append(("POST", "/tools", {"name": "test_tool", "description": "Test tool", "function_name": "test_tool"}))
        # 22. POST /tools/execute
        endpoints.append(("POST", "/tools/execute", {"tool_name": "test_tool", "parameters": {}}))
        # 23. GET /agents/{agent_id}/performance
        if agent_id:
            endpoints.append(("GET", f"/agents/{agent_id}/performance", None))
        # 24. GET /system/performance
        endpoints.append(("GET", "/system/performance", None))
        # 25. GET /system/alerts
        endpoints.append(("GET", "/system/alerts", None))
        # 26. POST /agents/{agent_id}/delegate
        if agent_id:
            endpoints.append(("POST", f"/agents/{agent_id}/delegate", {"task_description": "Delegate task", "target_agent_id": agent_id}))
        # 27. GET /memory/{agent_id}
        if agent_id:
            endpoints.append(("GET", f"/memory/{agent_id}", None))
        # 28. POST /memory/{agent_id}/query
        if agent_id:
            endpoints.append(("POST", f"/memory/{agent_id}/query", {"query": "test query"}))
        # 29. POST /memory/{agent_id}/store
        if agent_id:
            endpoints.append(("POST", f"/memory/{agent_id}/store", {"content": "test memory", "metadata": {}}))
        # 30. GET /agents/{agent_id}/errors
        if agent_id:
            endpoints.append(("GET", f"/agents/{agent_id}/errors", None))
        # 31. POST /agents/{agent_id}/errors/{error_id}/resolve (need error_id, skip)

        # Swarm endpoints (optional)
        endpoints.append(("GET", "/swarm/", None))

        print(f"Testing {len(endpoints)} endpoints...")
        results = []
        for method, path, data in endpoints:
            success, status = await test_endpoint(client, method, path, data)
            results.append(success)

        # Special test: create a temporary agent and delete it (to test full lifecycle)
        print("\nTesting agent creation and deletion lifecycle...")
        temp_agent_name = f"temp_{uuid.uuid4().hex[:8]}"
        create_data = {
            "name": temp_agent_name,
            "agent_type": "domain",
            "description": "Temporary agent for lifecycle test",
            "system_prompt": "You are a temporary agent.",
            "capabilities": ["test"],
            "domain": "test"
        }
        success_create, status_create = await test_endpoint(client, "POST", "/agents", create_data)
        results.append(success_create)
        temp_agent_id = None
        if success_create and status_create == 201:
            # Find the new agent ID
            resp = await client.get("/agents")
            if resp.status_code == 200:
                agents = resp.json().get("agents", [])
                temp_agent = next((a for a in agents if a["name"] == temp_agent_name), None)
                if temp_agent:
                    temp_agent_id = temp_agent["id"]
                    # Delete the temporary agent
                    success_delete, status_delete = await test_endpoint(client, "DELETE", f"/agents/{temp_agent_id}", None)
                    results.append(success_delete)
                else:
                    print("  ⚠ Created temporary agent not found in list")
                    results.append(False)
            else:
                results.append(False)

        # Calculate success rate (excluding 5xx errors)
        total = len(results)
        passed = sum(results)
        print(f"\n📊 Results: {passed}/{total} endpoints without server errors ({passed/total*100:.1f}%)")
        return passed == total

async def main():
    try:
        success = await test_all_endpoints()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())