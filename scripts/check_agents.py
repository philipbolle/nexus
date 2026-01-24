#!/usr/bin/env python3
import asyncio
import httpx
import json

async def main():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8080/agents")
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            return

        data = response.json()
        agents = data.get('agents', [])
        print(f"Total agents in response: {len(agents)}")

        git_agents = [a for a in agents if 'git' in a['name'].lower()]
        print(f"Git agents: {len(git_agents)}")
        for a in git_agents:
            print(f"  - {a['name']} ({a['id']})")

        # Also check registry status
        reg_response = await client.get("http://localhost:8080/registry-status")
        reg_data = reg_response.json()
        print(f"\nRegistry total agents: {reg_data.get('total_agents')}")
        print(f"Registry active agents: {reg_data.get('active_agents')}")

if __name__ == "__main__":
    asyncio.run(main())