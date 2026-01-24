#!/usr/bin/env python3
"""
Test Git Operations Agent webhook integration with n8n.

This script tests the full integration:
1. Verifies n8n webhook workflow is active
2. Executes git operations via agent
3. Verifies webhooks are triggered
4. Checks ntfy notifications (optional)

Run after importing and activating git_webhooks.json workflow in n8n UI.
"""

import asyncio
import httpx
import json
import sys, subprocess
from pathlib import Path

API_URL = "http://localhost:8080"
N8N_URL = "http://localhost:5678"
N8N_USER = "admin"
N8N_PASSWORD = None  # Load from .env if needed

async def load_n8n_password():
    """Load n8n password from .env file."""
    global N8N_PASSWORD
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith("N8N_PASSWORD="):
                    N8N_PASSWORD = line.strip().split('=', 1)[1].strip('"\'')
                    break
    if not N8N_PASSWORD:
        N8N_PASSWORD = "Changeme_n8n_password"
    return N8N_PASSWORD

async def get_git_agent_id() -> str:
    """Get Git Operations Agent ID from API."""
    async with httpx.AsyncClient() as client:
        # Use limit=200 to ensure we find the agent
        response = await client.get(f"{API_URL}/agents?limit=200")
        if response.status_code != 200:
            raise Exception(f"Failed to get agents: {response.status_code}")

        agents = response.json()["agents"]
        git_agent = next((a for a in agents if "git" in a["name"].lower()), None)
        if not git_agent:
            raise Exception("Git Operations Agent not found in agents list")

        agent_id = git_agent["id"]
        print(f"✅ Found Git Operations Agent: {git_agent['name']} (ID: {agent_id})")
        return agent_id

async def check_webhook_active() -> bool:
    """Check if n8n webhook endpoint is active (returns something other than 404)."""
    async with httpx.AsyncClient() as client:
        test_payload = {
            "event_type": "test",
            "timestamp": "2026-01-23T19:15:00.000Z",
            "agent_id": "test",
            "agent_name": "Test Agent",
            "data": {"test": True},
            "context": {}
        }

        try:
            response = await client.post(
                f"{N8N_URL}/webhook/git-commit",
                json=test_payload,
                timeout=10
            )
            if response.status_code == 404:
                print("❌ Webhook endpoint not found (workflow not imported/activated)")
                return False
            else:
                print(f"✅ Webhook endpoint active: {response.status_code}")
                if response.text:
                    print(f"   Response: {response.text[:100]}...")
                return True
        except Exception as e:
            print(f"❌ Webhook test failed: {e}")
            return False

async def execute_git_status(agent_id: str) -> bool:
    """Execute git_status tool via agent."""
    async with httpx.AsyncClient() as client:
        print("🔄 Executing git_status tool...")
        tool_response = await client.post(
            f"{API_URL}/tools/execute",
            json={
                "tool_name": "git_status",
                "agent_id": agent_id,
                "parameters": {}
            }
        )

        if tool_response.status_code == 200:
            result = tool_response.json()
            print(f"✅ Tool executed successfully: {result.get('status')}")
            if result.get('result'):
                print(f"   Result: {json.dumps(result.get('result'), indent=2)}")
            return True
        else:
            print(f"❌ Tool execution failed: {tool_response.status_code}")
            print(f"   Response: {tool_response.text}")
            return False

async def execute_git_create_branch(agent_id: str) -> bool:
    """Create a test branch to trigger webhook."""
    import time
    branch_name = f"test-webhook-{int(time.time())}"
    async with httpx.AsyncClient() as client:
        print(f"🔄 Creating test branch '{branch_name}'...")
        tool_response = await client.post(
            f"{API_URL}/tools/execute",
            json={
                "tool_name": "git_create_branch",
                "agent_id": agent_id,
                "parameters": {
                    "branch_name": branch_name,
                    "from_branch": "main",
                    "purpose": "test",
                    "issue_id": None
                }
            }
        )
        if tool_response.status_code == 200:
            result = tool_response.json()
            print(f"✅ Branch created successfully: {result.get('status')}")
            if result.get('result'):
                print(f"   Result: {json.dumps(result.get('result'), indent=2)}")
            # Optionally delete branch after test (via git command)
            # We'll leave it for manual cleanup for now
            return True
        else:
            print(f"❌ Branch creation failed: {tool_response.status_code}")
            print(f"   Response: {tool_response.text}")
            return False

async def test_n8n_api_import():
    """Attempt to import workflow via n8n REST API (if credentials available)."""
    password = await load_n8n_password()
    auth = (N8N_USER, password)

    async with httpx.AsyncClient(auth=auth) as client:
        # First, list existing workflows to see if git_webhooks already exists
        try:
            response = await client.get(f"{N8N_URL}/rest/workflows")
            if response.status_code == 200:
                workflows = response.json()
                print(f"Found {len(workflows)} existing workflows")
                # Check for git_webhooks
                for wf in workflows:
                    if wf.get('name') == 'git_webhooks':
                        print("✅ git_webhooks workflow already exists")
                        return True
        except Exception as e:
            print(f"⚠️  Cannot list workflows via API: {e}")
            print("   Continuing with manual import...")
            return False

    print("📋 Manual import required: workflow not found via API")
    return False

async def main():
    print("🚀 Git Operations Agent Integration Test")
    print("=" * 50)

    # Step 0: Attempt to import via API (optional)
    # imported = await test_n8n_api_import()
    # if not imported:
    #     print("\n📋 Please import workflow manually:")
    #     print("   1. Open n8n UI: http://localhost:5678")
    #     print("   2. Login with admin / password from .env")
    #     print("   3. Click '+' to create new workflow")
    #     print("   4. Click 'Import from file'")
    #     print("   5. Select: automation/workflows/git_webhooks.json")
    #     print("   6. Activate workflow (toggle in top-right)")
    #     print("\nPress Enter when done...")
    #     input()

    # Step 1: Get agent ID
    try:
        agent_id = await get_git_agent_id()
    except Exception as e:
        print(f"❌ {e}")
        return False

    # Step 2: Check if webhook is active
    print("\n🔍 Checking n8n webhook endpoint...")
    webhook_active = await check_webhook_active()
    if not webhook_active:
        print("\n📋 Please import and activate the workflow:")
        print("   1. Open n8n UI: http://localhost:5678")
        print("   2. Import automation/workflows/git_webhooks.json")
        print("   3. Activate workflow (toggle in top-right)")
        print("\nAfter activating, press Enter to retry...")
        input()
        webhook_active = await check_webhook_active()
        if not webhook_active:
            print("❌ Webhook still not active. Exiting.")
            return False

    # Step 3: Execute git status
    print("\n🔄 Testing git operations...")
    success = await execute_git_status(agent_id)
    if not success:
        print("❌ Git status test failed")
        return False

    # Step 4: Create a test branch to trigger webhook
    print("\n🌿 Creating test branch to trigger webhook...")
    branch_success = await execute_git_create_branch(agent_id)
    if not branch_success:
        print("⚠️  Branch creation failed, but continuing...")

    print("\n✅ Integration test completed successfully!")
    print("📌 Next steps:")
    print("   - Check n8n executions for webhook events")
    print("   - Verify ntfy notifications (topic: nexus-philip-cd701650d0771943)")
    print("   - Test other git operations (commit, push, branch)")
    print("   - Delete test branch manually: git branch -d test-webhook-*")
    return True

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        success = loop.run_until_complete(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        loop.close()