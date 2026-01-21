#!/usr/bin/env python3
"""
Test agent framework endpoints.
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8080"
TIMEOUT = 30

async def test_agent_creation():
    """Test creating an agent."""
    url = f"{BASE_URL}/agents"

    agent_data = {
        "name": "test-agent-1",
        "agent_type": "domain",
        "description": "Test agent for validation",
        "system_prompt": "You are a test agent.",
        "capabilities": ["testing", "validation"],
        "domain": "testing",
        "config": {}
    }

    async with aiohttp.ClientSession() as session:
        try:
            print(f"Creating agent: {agent_data['name']}")
            async with session.post(url, json=agent_data, timeout=TIMEOUT) as resp:
                status = resp.status
                text = await resp.text()

                if status == 201:
                    print(f"✅ Agent created successfully: {text}")
                    return json.loads(text)
                else:
                    print(f"❌ Failed to create agent: {status} - {text}")
                    return None
        except Exception as e:
            print(f"❌ Error creating agent: {e}")
            return None

async def test_tool_creation():
    """Test creating a tool."""
    url = f"{BASE_URL}/tools"

    tool_data = {
        "name": "test_tool",
        "display_name": "Test Tool",
        "description": "A test tool for validation",
        "tool_type": "other",
        "input_schema": {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "Test input"}
            },
            "required": ["input"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "result": {"type": "string", "description": "Test result"}
            }
        },
        "requires_confirmation": False
    }

    async with aiohttp.ClientSession() as session:
        try:
            print(f"Creating tool: {tool_data['name']}")
            async with session.post(url, json=tool_data, timeout=TIMEOUT) as resp:
                status = resp.status
                text = await resp.text()

                if status == 201:
                    print(f"✅ Tool created successfully: {text}")
                    return json.loads(text)
                else:
                    print(f"❌ Failed to create tool: {status} - {text}")
                    return None
        except Exception as e:
            print(f"❌ Error creating tool: {e}")
            return None

async def test_list_agents():
    """Test listing agents."""
    url = f"{BASE_URL}/agents"

    async with aiohttp.ClientSession() as session:
        try:
            print("Listing agents...")
            async with session.get(url, timeout=TIMEOUT) as resp:
                status = resp.status
                text = await resp.text()

                if status == 200:
                    data = json.loads(text)
                    print(f"✅ Agents listed: {len(data.get('agents', []))} agents")
                    return data
                else:
                    print(f"❌ Failed to list agents: {status} - {text}")
                    return None
        except Exception as e:
            print(f"❌ Error listing agents: {e}")
            return None

async def test_list_tools():
    """Test listing tools."""
    url = f"{BASE_URL}/tools"

    async with aiohttp.ClientSession() as session:
        try:
            print("Listing tools...")
            async with session.get(url, timeout=TIMEOUT) as resp:
                status = resp.status
                text = await resp.text()

                if status == 200:
                    data = json.loads(text)
                    print(f"✅ Tools listed: {len(data)} tools")
                    return data
                else:
                    print(f"❌ Failed to list tools: {status} - {text}")
                    return None
        except Exception as e:
            print(f"❌ Error listing tools: {e}")
            return None

async def main():
    print("🚀 Testing NEXUS Agent Framework Endpoints")
    print("=" * 50)

    # Test list agents (should be empty)
    await test_list_agents()

    # Test create agent
    agent = await test_agent_creation()

    # Test list agents again (should have 1)
    await test_list_agents()

    # Test list tools (should have built-in tools)
    await test_list_tools()

    # Test create tool
    tool = await test_tool_creation()

    # Test list tools again
    await test_list_tools()

    print("=" * 50)
    print("✅ Agent framework tests completed")

if __name__ == "__main__":
    asyncio.run(main())