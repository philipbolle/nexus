#!/usr/bin/env python3
"""
Detailed test to diagnose agent framework issues.
"""

import json
import sys
from datetime import datetime
import requests

BASE_URL = "http://localhost:8080"

def test_with_details(method, path, data=None):
    """Test endpoint with detailed error reporting."""
    url = f"{BASE_URL}{path}"

    print(f"\nTesting: {method} {path}")
    print("-" * 50)

    try:
        if method == 'GET':
            response = requests.get(url, timeout=10)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=10)
        elif method == 'PUT':
            response = requests.put(url, json=data, timeout=10)
        else:
            print(f"  ❌ Unsupported method: {method}")
            return False

        print(f"  Status: {response.status_code}")

        if response.text:
            try:
                resp_json = response.json()
                print(f"  Response: {json.dumps(resp_json, indent=2)}")
            except:
                print(f"  Response (text): {response.text[:500]}")

        if response.status_code >= 400:
            print(f"  ❌ Failed with status: {response.status_code}")
            if response.status_code == 422:
                print("  This is a validation error - check request data format")
            elif response.status_code == 500:
                print("  This is a server error - check implementation")
            return False
        else:
            print(f"  ✅ Success")
            return True

    except Exception as e:
        print(f"  ❌ Exception: {str(e)}")
        return False

def main():
    """Run detailed diagnostic tests."""
    print("NEXUS Agent Framework Diagnostic Test")
    print("="*60)

    # First, check what agent types are valid
    print("\n1. Checking valid agent types...")
    test_with_details("GET", "/docs")

    # Test with correct enum values based on earlier import test
    print("\n2. Testing agent creation with correct enum values...")

    # From earlier test, valid AgentType values are: 'domain', 'orchestrator', 'supervisor', 'worker', 'analyzer'
    agent_data = {
        "name": f"test-agent-{datetime.now().strftime('%H%M%S')}",
        "agent_type": "worker",  # Using valid enum value
        "description": "Test agent",
        "system_prompt": "You are a test agent.",
        "capabilities": ["testing"],
        "domain": "testing",
        "config": {"test": True}
    }
    agent_created = test_with_details("POST", "/agents", agent_data)

    agent_id = None
    if agent_created:
        # Try to get the list of agents to see what was created
        print("\n3. Checking agent list...")
        test_with_details("GET", "/agents")

    # Test session creation
    print("\n4. Testing session creation...")
    session_data = {
        "title": f"Test Session {datetime.now().strftime('%H:%M')}",
        "session_type": "testing",
        "metadata": {"test": True}
    }
    test_with_details("POST", "/sessions", session_data)

    # Test task submission with correct priority (should be integer based on error)
    print("\n5. Testing task submission...")
    task_data = {
        "task": {
            "description": "Test task",
            "type": "test"
        },
        "priority": 1  # Changed from string "normal" to integer 1
    }
    test_with_details("POST", "/tasks", task_data)

    # Test tool creation - need to check valid tool_type values
    print("\n6. Testing tool creation...")
    tool_data = {
        "name": f"test_tool_{datetime.now().strftime('%H%M%S')}",
        "display_name": "Test Tool",
        "description": "A test tool",
        "tool_type": "analysis",  # Valid values: database, api, file, calculation, notification, automation, analysis, python_function, web_search
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "requires_confirmation": False
    }
    test_with_details("POST", "/tools", tool_data)

    # Test registry status
    print("\n7. Testing registry status...")
    test_with_details("GET", "/registry/status")

    # Test system performance
    print("\n8. Testing system performance endpoint...")
    test_with_details("GET", "/system/performance")

    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    print("\nCommon issues found:")
    print("1. Enum validation errors - need to use correct enum values")
    print("2. Server errors (500) - implementation issues in agent framework")
    print("3. Priority field should be integer, not string")
    print("\nNext steps:")
    print("1. Check agent framework implementation files for missing methods")
    print("2. Verify database schema for agent-related tables")
    print("3. Check if agent components are properly initialized")

if __name__ == "__main__":
    main()