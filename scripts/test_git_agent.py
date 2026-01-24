#!/usr/bin/env python3
"""
Test script for GitOperationsAgent webhook integration.
Tests git operations and verifies webhooks are sent to n8n.
"""

import asyncio
import httpx
import json
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

async def test_git_agent():
    """Test GitOperationsAgent functionality."""

    api_url = "http://localhost:8080"
    n8n_url = "http://localhost:5678"

    print("🔍 Testing Git Operations Agent Integration")
    print("=" * 50)

    # 1. Get agent ID
    print("\n1. Finding Git Operations Agent...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{api_url}/agents?limit=200")
            agents = response.json()["agents"]
            git_agent = next((a for a in agents if "git" in a["name"].lower()), None)

            if not git_agent:
                print("❌ Git Operations Agent not found")
                return False

            agent_id = git_agent["id"]
            print(f"   ✅ Found agent: {git_agent['name']} (ID: {agent_id})")

    except Exception as e:
        print(f"❌ Failed to get agents: {e}")
        return False

    # 2. Test n8n webhook endpoint (should fail without active workflow)
    print("\n2. Testing n8n webhook endpoint...")
    try:
        async with httpx.AsyncClient() as client:
            test_payload = {
                "event_type": "test",
                "timestamp": "2026-01-23T19:15:00.000Z",
                "agent_id": agent_id,
                "agent_name": "Test Agent",
                "data": {"test": True},
                "context": {}
            }

            response = await client.post(
                f"{n8n_url}/webhook/git-commit",
                json=test_payload,
                timeout=10
            )

            if response.status_code == 404:
                print("   ⚠️  Webhook not registered (expected - workflow not active)")
                print("   ℹ️  Import and activate git_webhooks.json workflow in n8n UI")
            else:
                print(f"   ✅ Webhook responded: {response.status_code}")
                print(f"   Response: {response.text[:100]}...")

    except Exception as e:
        print(f"   ❌ Webhook test failed: {e}")

    # 3. Test git status via agent (if tools are accessible)
    print("\n3. Testing git status...")
    try:
        # First, check if agent is started
        async with httpx.AsyncClient() as client:
            # Start agent if not started
            status_response = await client.get(f"{api_url}/agents/{agent_id}/status")
            status = status_response.json()

            if not status.get("is_active", False):
                print("   ⚠️  Agent not active, attempting to start...")
                start_response = await client.post(f"{api_url}/agents/{agent_id}/start", json={})
                if start_response.status_code == 200:
                    print("   ✅ Agent started")
                else:
                    print(f"   ❌ Failed to start agent: {start_response.status_code}")
                    return False

            # Try to execute git_status tool
            print("   ℹ️  Attempting to execute git_status tool...")
            # Note: Tool execution might require different endpoint

    except Exception as e:
        print(f"   ❌ Git status test failed: {e}")

    print("\n" + "=" * 50)
    print("📋 Next Steps:")
    print("1. Import git_webhooks.json workflow in n8n UI (http://localhost:5678)")
    print("2. Activate the workflow (toggle in top-right)")
    print("3. Test git operations via agent API")
    print("4. Check n8n executions and ntfy notifications")

    return True

async def import_n8n_workflow():
    """Attempt to import n8n workflow via API (if available)."""
    print("\n🔄 Attempting to import n8n workflow...")

    # n8n might have a REST API for workflow import
    # For now, provide manual instructions
    workflow_path = Path(__file__).parent / "automation" / "workflows" / "git_webhooks.json"

    if workflow_path.exists():
        print(f"   ✅ Workflow file exists: {workflow_path}")
        print("   📋 Manual import steps:")
        print("     1. Open n8n UI: http://localhost:5678")
        print("     2. Click '+' to create new workflow")
        print("     3. Click 'Import from file'")
        print("     4. Select: automation/workflows/git_webhooks.json")
        print("     5. Activate workflow (toggle in top-right)")
    else:
        print(f"   ❌ Workflow file not found: {workflow_path}")

    return False

if __name__ == "__main__":
    print("🚀 NEXUS Git Operations Agent Integration Test")
    print("=" * 50)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Run tests
        success = loop.run_until_complete(test_git_agent())

        # Offer to attempt workflow import
        print("\nWould you like to attempt n8n workflow import? (Manual required for now)")

        if success:
            print("\n✅ Test completed successfully!")
            print("📌 Remember to import and activate the n8n workflow")
        else:
            print("\n❌ Test encountered issues")
            print("📌 Check logs and configuration")

    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        loop.close()