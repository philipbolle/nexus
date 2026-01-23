#!/usr/bin/env python3
"""Debug swarm membership API error."""

import asyncio
import httpx
import json
from uuid import uuid4

BASE_URL = "http://localhost:8080"
TIMEOUT = 30.0

async def debug_swarm_membership():
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # 1. Create agent
        agent_data = {
            "name": f"Debug Agent {uuid4().hex[:8]}",
            "agent_type": "domain",
            "description": "Debug agent",
            "system_prompt": "Debug",
            "capabilities": ["debug"],
            "domain": "testing",
            "supervisor_id": None,
            "config": {}
        }
        resp = await client.post(f"{BASE_URL}/agents", json=agent_data)
        print(f"Agent creation: {resp.status_code}")
        if resp.status_code != 201:
            print(f"Error: {resp.text}")
            return
        agent = resp.json()
        agent_id = agent["id"]
        print(f"Agent ID: {agent_id}")

        # 2. Create swarm
        swarm_data = {
            "name": f"Debug Swarm {uuid4().hex[:8]}",
            "description": "Debug swarm",
            "purpose": "testing",
            "swarm_type": "collaborative",
            "max_members": 10,
            "auto_scaling": False,
            "health_check_interval_seconds": 30,
            "metadata": {}
        }
        resp = await client.post(f"{BASE_URL}/swarm/", json=swarm_data)
        print(f"Swarm creation: {resp.status_code}")
        if resp.status_code != 200:
            print(f"Error: {resp.text}")
            return
        swarm = resp.json()
        swarm_id = swarm["id"]
        print(f"Swarm ID: {swarm_id}")

        # 3. Add membership
        membership_data = {
            "agent_id": agent_id,
            "role": "member",
            "metadata": {}
        }
        resp = await client.post(f"{BASE_URL}/swarm/{swarm_id}/members", json=membership_data)
        print(f"Swarm membership: {resp.status_code}")
        print(f"Response headers: {dict(resp.headers)}")
        print(f"Response text: {resp.text}")
        if resp.status_code >= 400:
            print(f"Full response: {resp}")
            # Try to get more details by checking if there's a response body
            try:
                error_json = resp.json()
                print(f"Error JSON: {json.dumps(error_json, indent=2)}")
            except:
                pass

        # 4. Also test swarm message sending
        message_data = {
            "sender_agent_id": agent_id,
            "recipient_agent_id": None,
            "channel": "general",
            "message_type": "test",
            "content": "Debug message",
            "priority": "normal",
            "ttl_seconds": 3600
        }
        resp = await client.post(f"{BASE_URL}/swarm/{swarm_id}/messages", json=message_data)
        print(f"\\nSwarm message: {resp.status_code}")
        print(f"Response text: {resp.text}")

if __name__ == "__main__":
    asyncio.run(debug_swarm_membership())