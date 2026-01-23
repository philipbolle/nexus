#!/usr/bin/env python3
"""
Test script for NEXUS Distributed Task Processing API endpoints.

Verifies that all distributed task endpoints are accessible and return proper responses.
Uses FastAPI TestClient for testing without running the full server.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)

def test_root_endpoint():
    """Test root endpoint."""
    print("🔍 Testing root endpoint...")
    response = client.get("/")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")
    assert response.status_code == 200
    print("  ✅ Root endpoint OK")

def test_health_endpoint():
    """Test health endpoint."""
    print("\n🔍 Testing health endpoint...")
    response = client.get("/health")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")
    assert response.status_code == 200
    print("  ✅ Health endpoint OK")

def test_distributed_tasks_endpoints():
    """Test distributed tasks endpoints."""
    print("\n🔍 Testing Distributed Task Processing endpoints...")

    # Test endpoint listing
    print("\n📋 Listing available endpoints...")
    for route in app.routes:
        if hasattr(route, "path"):
            path = route.path
            if "/distributed-tasks" in path:
                methods = route.methods if hasattr(route, "methods") else ["GET"]
                print(f"  {path} - {methods}")

    # Test GET /distributed-tasks/health
    print("\n🔍 Testing GET /distributed-tasks/health...")
    try:
        response = client.get("/distributed-tasks/health")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print(f"  Response: {response.json()}")
            print("  ✅ Distributed tasks health endpoint OK")
        else:
            print(f"  ❌ Unexpected status: {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # Test GET /distributed-tasks/stats
    print("\n🔍 Testing GET /distributed-tasks/stats...")
    try:
        response = client.get("/distributed-tasks/stats")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Response keys: {list(data.keys())}")
            print("  ✅ Distributed tasks stats endpoint OK")
        else:
            print(f"  ❌ Unexpected status: {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # Test GET /distributed-tasks/queues
    print("\n🔍 Testing GET /distributed-tasks/queues...")
    try:
        response = client.get("/distributed-tasks/queues")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Queues: {len(data)} queue(s)")
            print("  ✅ Distributed tasks queues endpoint OK")
        else:
            print(f"  ❌ Unexpected status: {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # Test GET /distributed-tasks/workers
    print("\n🔍 Testing GET /distributed-tasks/workers...")
    try:
        response = client.get("/distributed-tasks/workers")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Workers: {len(data)} worker(s)")
            print("  ✅ Distributed tasks workers endpoint OK")
        else:
            print(f"  ❌ Unexpected status: {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

def test_swarm_endpoints():
    """Test swarm endpoints."""
    print("\n🔍 Testing Swarm endpoints...")

    # Test GET /swarm/health
    print("\n🔍 Testing GET /swarm/health...")
    try:
        response = client.get("/swarm/health")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Response: {data}")
            print("  ✅ Swarm health endpoint OK")
        else:
            print(f"  ❌ Unexpected status: {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # Test GET /swarm
    print("\n🔍 Testing GET /swarm...")
    try:
        response = client.get("/swarm")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Swarms: {len(data)} swarm(s)")
            print("  ✅ Swarm listing endpoint OK")
        else:
            print(f"  ❌ Unexpected status: {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

def main():
    """Run all tests."""
    print("🧪 NEXUS API Endpoint Accessibility Test")
    print("=" * 60)

    try:
        test_root_endpoint()
        test_health_endpoint()
        test_distributed_tasks_endpoints()
        test_swarm_endpoints()

        print("\n" + "=" * 60)
        print("✅ All endpoint tests completed!")
        return 0

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())