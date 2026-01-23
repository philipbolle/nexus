#!/usr/bin/env python3
"""
Simple test for NEXUS Agent Framework endpoints.
"""

import json
import sys
from datetime import datetime
import requests

BASE_URL = "http://localhost:8080"

def test_endpoint(method, path, name, expected_status=200, data=None):
    """Test a single endpoint."""
    url = f"{BASE_URL}{path}"

    try:
        if method == 'GET':
            response = requests.get(url, timeout=10)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=10)
        elif method == 'PUT':
            response = requests.put(url, json=data, timeout=10)
        elif method == 'DELETE':
            response = requests.delete(url, timeout=10)
        else:
            return {"name": name, "success": False, "error": f"Unsupported method: {method}"}

        success = response.status_code == expected_status
        result = {
            "name": name,
            "method": method,
            "url": url,
            "expected_status": expected_status,
            "actual_status": response.status_code,
            "success": success,
            "error": None if success else f"Expected {expected_status}, got {response.status_code}"
        }

        if response.text:
            try:
                result["response"] = response.json()
            except:
                result["response"] = response.text[:200]

        return result

    except Exception as e:
        return {
            "name": name,
            "success": False,
            "error": f"Exception: {str(e)}",
            "url": url
        }

def main():
    """Test agent framework endpoints."""
    print("Testing NEXUS Agent Framework Endpoints")
    print("="*60)

    results = []

    # Test basic agent endpoints
    print("\n1. Testing Agent Management:")
    print("-"*40)

    # List agents (should be empty initially)
    results.append(test_endpoint("GET", "/agents", "List Agents"))

    # Create a test agent
    agent_data = {
        "name": f"test-agent-{datetime.now().strftime('%H%M%S')}",
        "agent_type": "general",
        "description": "Test agent created by test script",
        "system_prompt": "You are a test agent.",
        "capabilities": ["testing", "debugging"],
        "domain": "testing",
        "config": {"test": True}
    }
    create_result = test_endpoint("POST", "/agents", "Create Agent", 201, agent_data)
    results.append(create_result)

    agent_id = None
    if create_result.get("success") and create_result.get("response", {}).get("id"):
        agent_id = create_result["response"]["id"]
        print(f"  ✓ Created agent: {agent_id}")

        # Get the created agent
        results.append(test_endpoint("GET", f"/agents/{agent_id}", "Get Agent"))

        # Update the agent
        update_data = {"description": "Updated description from test"}
        results.append(test_endpoint("PUT", f"/agents/{agent_id}", "Update Agent", 200, update_data))

        # Get agent status
        results.append(test_endpoint("GET", f"/agents/{agent_id}/status", "Get Agent Status"))

        # Start agent
        results.append(test_endpoint("POST", f"/agents/{agent_id}/start", "Start Agent"))

        # Stop agent
        results.append(test_endpoint("POST", f"/agents/{agent_id}/stop", "Stop Agent"))

        # Get agent errors
        results.append(test_endpoint("GET", f"/agents/{agent_id}/errors", "Get Agent Errors"))

    # Test registry status
    results.append(test_endpoint("GET", "/registry/status", "Get Registry Status"))

    print("\n2. Testing Session Management:")
    print("-"*40)

    # Create a session
    session_data = {
        "title": f"Test Session {datetime.now().strftime('%H:%M')}",
        "session_type": "testing",
        "metadata": {"test": True}
    }
    session_result = test_endpoint("POST", "/sessions", "Create Session", 201, session_data)
    results.append(session_result)

    session_id = None
    if session_result.get("success") and session_result.get("response", {}).get("id"):
        session_id = session_result["response"]["id"]
        print(f"  ✓ Created session: {session_id}")

        # Get the session
        results.append(test_endpoint("GET", f"/sessions/{session_id}", "Get Session"))

        # List sessions
        results.append(test_endpoint("GET", "/sessions", "List Sessions"))

        # Add message to session
        message_data = {
            "content": "Test message from test script",
            "role": "user"
        }
        results.append(test_endpoint("POST", f"/sessions/{session_id}/messages", "Add Message", 200, message_data))

        # Get messages
        results.append(test_endpoint("GET", f"/sessions/{session_id}/messages", "Get Messages"))

        # End session
        results.append(test_endpoint("POST", f"/sessions/{session_id}/end", "End Session"))

    print("\n3. Testing Task Execution:")
    print("-"*40)

    # Submit a task
    task_data = {
        "task": {
            "description": "Test task for agent framework",
            "type": "test",
            "parameters": {"test": True}
        },
        "priority": "normal"
    }
    task_result = test_endpoint("POST", "/tasks", "Submit Task", 200, task_data)
    results.append(task_result)

    if task_result.get("success") and task_result.get("response", {}).get("task_id"):
        task_id = task_result["response"]["task_id"]
        print(f"  ✓ Submitted task: {task_id}")

        # Get task status
        results.append(test_endpoint("GET", f"/tasks/{task_id}", "Get Task Status"))

        # Try to cancel task
        results.append(test_endpoint("POST", f"/tasks/{task_id}/cancel", "Cancel Task"))

    print("\n4. Testing Tool Management:")
    print("-"*40)

    # List tools
    results.append(test_endpoint("GET", "/tools", "List Tools"))

    # Create a test tool
    tool_data = {
        "name": f"test_tool_{datetime.now().strftime('%H%M%S')}",
        "display_name": "Test Tool",
        "description": "A test tool",
        "tool_type": "utility",
        "input_schema": {"type": "object", "properties": {"input": {"type": "string"}}},
        "output_schema": {"type": "object", "properties": {"result": {"type": "string"}}},
        "requires_confirmation": False
    }
    tool_result = test_endpoint("POST", "/tools", "Create Tool", 201, tool_data)
    results.append(tool_result)

    print("\n5. Testing Performance Monitoring:")
    print("-"*40)

    # Get system performance
    results.append(test_endpoint("GET", "/system/performance", "Get System Performance"))

    # Get system alerts
    results.append(test_endpoint("GET", "/system/alerts", "Get System Alerts"))

    # Test agent selection
    selection_data = {
        "task_description": "Test task for agent selection",
        "required_capabilities": ["testing"],
        "preferred_domain": "testing"
    }
    results.append(test_endpoint("POST", "/registry/select-agent", "Select Agent", 200, selection_data))

    print("\n6. Testing Memory System:")
    print("-"*40)

    if agent_id:
        # Get agent memory
        results.append(test_endpoint("GET", f"/memory/{agent_id}", "Get Agent Memory"))

        # Query memory
        query_data = {"text": "test query", "limit": 5}
        results.append(test_endpoint("POST", f"/memory/{agent_id}/query", "Query Memory", 200, query_data))

        # Store memory
        memory_data = {
            "content": "Test memory stored by test script",
            "type": "observation",
            "metadata": {"test": True}
        }
        results.append(test_endpoint("POST", f"/memory/{agent_id}/store", "Store Memory", 200, memory_data))

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    successes = [r for r in results if r.get('success')]
    failures = [r for r in results if not r.get('success')]

    print(f"Total tests: {len(results)}")
    print(f"✅ PASSED: {len(successes)}")
    print(f"❌ FAILED: {len(failures)}")

    if failures:
        print("\nFAILED TESTS:")
        for fail in failures:
            print(f"  ❌ {fail['name']}")
            if fail.get('error'):
                print(f"     Error: {fail['error']}")
            if fail.get('response'):
                resp = fail['response']
                if isinstance(resp, dict):
                    print(f"     Response: {json.dumps(resp, indent=2)[:200]}...")
                else:
                    print(f"     Response: {str(resp)[:200]}...")
            print()

    # Check for common issues
    print("\nANALYSIS:")
    print("-"*40)

    not_found = [f for f in failures if f.get('actual_status') == 404]
    server_errors = [f for f in failures if f.get('actual_status') == 500]
    validation_errors = [f for f in failures if f.get('actual_status') == 422]

    if not_found:
        print(f"⚠️  {len(not_found)} endpoints returned 404 (Not Found)")
        print("   These endpoints may not be implemented yet")

    if server_errors:
        print(f"⚠️  {len(server_errors)} endpoints returned 500 (Internal Server Error)")
        print("   These endpoints have implementation errors")

    if validation_errors:
        print(f"⚠️  {len(validation_errors)} endpoints returned 422 (Validation Error)")
        print("   Check request data formats")

    # Cleanup if we created resources
    if agent_id:
        print(f"\nCleaning up test agent: {agent_id}")
        test_endpoint("DELETE", f"/agents/{agent_id}", "Cleanup Agent", 204)

    print("\n" + "="*60)
    print("RECOMMENDATIONS:")
    print("-"*40)

    if len(failures) == 0:
        print("🎉 All agent framework endpoints are working correctly!")
    else:
        print("Some endpoints need attention. Focus on:")
        print("1. Endpoints returning 500 errors (implementation issues)")
        print("2. Endpoints returning 404 (may not be implemented)")
        print("3. Check database connections and schema")

    return 0 if len(failures) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())