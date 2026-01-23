#!/usr/bin/env python3
"""
Diagnose swarm issues.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from app.database import db

async def check_tables():
    await db.connect()

    # Check if swarm tables exist
    tables = [
        'swarms', 'swarm_memberships', 'consensus_groups',
        'consensus_log_entries', 'votes', 'vote_responses',
        'swarm_messages', 'swarm_events', 'swarm_performance'
    ]

    for table in tables:
        try:
            result = await db.fetch_one(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
            exists = result['exists']
            print(f"{table}: {'✅ EXISTS' if exists else '❌ MISSING'}")

            if exists:
                # Count rows
                count_result = await db.fetch_one(f"SELECT COUNT(*) as count FROM {table}")
                print(f"  Rows: {count_result['count']}")
        except Exception as e:
            print(f"{table}: ❌ ERROR - {e}")

    # Keep connection for endpoint test

async def test_swarm_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # Test GET /swarm/
    print("\nTesting GET /swarm/:")
    response = client.get("/swarm/")
    print(f"  Status: {response.status_code}")
    if response.status_code != 200:
        print(f"  Error: {response.text}")

    # Test POST /swarm/
    print("\nTesting POST /swarm/:")
    swarm_data = {
        "name": "Test Swarm Diagnostic",
        "description": "Test swarm for diagnostics",
        "purpose": "testing",
        "max_members": 5,
        "consensus_required": False,
        "voting_enabled": True
    }
    response = client.post("/swarm/", json=swarm_data)
    print(f"  Status: {response.status_code}")
    if response.status_code != 200:
        print(f"  Error: {response.text}")
    else:
        print(f"  Response: {response.json()}")

async def main():
    print("🔍 Swarm System Diagnostic")
    print("=" * 60)

    print("\n1. Checking database tables...")
    await check_tables()

    print("\n2. Testing API endpoints...")
    await test_swarm_endpoint()
    await db.disconnect()

    print("\n" + "=" * 60)
    print("Diagnostic complete.")

if __name__ == "__main__":
    asyncio.run(main())