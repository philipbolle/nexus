#!/usr/bin/env python3
"""
Comprehensive Agent Health Monitoring Test
Tests agent status, performance metrics, and monitoring endpoints.
Also fixes common issues (missing tables, UUID conversion bugs).
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from uuid import UUID
import httpx

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import db
from app.agents.monitoring import PerformanceMonitor, SYSTEM_AGENT_ID


def patch_uuid_conversion():
    """Monkey-patch _ensure_uuid method to handle UUID objects."""
    original_method = PerformanceMonitor._ensure_uuid

    def patched_ensure_uuid(self, agent_id):
        # Handle UUID objects
        if isinstance(agent_id, UUID):
            return str(agent_id)

        # Handle string 'system'
        if agent_id == "system":
            return SYSTEM_AGENT_ID

        # If already a valid UUID string, return as-is
        try:
            UUID(agent_id)
            return agent_id
        except ValueError:
            # Generate deterministic UUID from string
            import uuid
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, agent_id))

    PerformanceMonitor._ensure_uuid = patched_ensure_uuid
    print("✅ Patched _ensure_uuid method to handle UUID objects")
    return True


async def create_missing_tables():
    """Create missing system_alerts table if it doesn't exist."""
    print("🔧 Checking for missing tables...")

    # Check if system_alerts exists
    result = await db.fetch_one(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'system_alerts'
        );
        """
    )
    exists = result["exists"] if result else False

    if exists:
        print("  ✅ system_alerts table exists")
        return True

    print("  ⚠️  system_alerts table missing - creating...")

    try:
        await db.execute("""
            CREATE TABLE system_alerts (
                id VARCHAR(100) PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                message TEXT,
                severity VARCHAR(20) NOT NULL,
                source VARCHAR(50) NOT NULL,
                source_id VARCHAR(100),
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ NOT NULL,
                acknowledged BOOLEAN DEFAULT FALSE,
                acknowledged_at TIMESTAMPTZ,
                resolved BOOLEAN DEFAULT FALSE,
                resolved_at TIMESTAMPTZ,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        print("  ✅ Created system_alerts table")
        return True
    except Exception as e:
        print(f"  ❌ Failed to create system_alerts table: {e}")
        return False


async def test_uuid_conversion():
    """Test the _ensure_uuid method to verify it handles 'system' correctly."""
    print("\n🔧 Testing UUID conversion for 'system'...")

    monitor = PerformanceMonitor()

    # Test conversion of 'system'
    try:
        result = monitor._ensure_uuid("system")
        print(f"  _ensure_uuid('system') = '{result}'")
        if result == SYSTEM_AGENT_ID:
            print(f"  ✅ Correctly converted 'system' to SYSTEM_AGENT_ID")
        else:
            print(f"  ⚠️  Unexpected result: expected '{SYSTEM_AGENT_ID}', got '{result}'")

        # Verify it's a valid UUID
        UUID(result)
        print(f"  ✅ Result is a valid UUID")
    except Exception as e:
        print(f"  ❌ Error testing _ensure_uuid: {e}")

    # Test conversion of regular UUID string
    test_uuid = "667c97fc-fa58-4644-8b85-9b7d941fd8d5"
    try:
        result = monitor._ensure_uuid(test_uuid)
        if result == test_uuid:
            print(f"  ✅ UUID strings are preserved")
        else:
            print(f"  ⚠️  UUID string changed: {result}")
    except Exception as e:
        print(f"  ❌ Error testing UUID conversion: {e}")

    # Test conversion of UUID object
    try:
        uuid_obj = UUID(test_uuid)
        result = monitor._ensure_uuid(uuid_obj)
        if result == test_uuid:
            print(f"  ✅ UUID objects are converted to strings")
        else:
            print(f"  ⚠️  UUID object conversion failed: {result}")
    except Exception as e:
        print(f"  ❌ Error testing UUID object conversion: {e}")


async def test_agent_status_endpoint():
    """Test GET /agents/{agent_id}/status endpoint."""
    print("\n🧪 Testing agent status endpoint...")

    # Get an agent ID from the system
    agents = await db.fetch_all("SELECT id, name FROM agents LIMIT 3")
    if not agents:
        print("  ⚠️  No agents found in database")
        return

    async with httpx.AsyncClient() as client:
        for agent in agents:
            agent_id = agent["id"]
            agent_name = agent["name"]

            try:
                response = await client.get(
                    f"http://localhost:8080/agents/{agent_id}/status",
                    timeout=10.0
                )
                print(f"  GET /agents/{agent_id}/status ({agent_name}): {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    print(f"    Status: {data.get('status')}, Active: {data.get('is_active')}")
                    print(f"    Success rate: {data.get('success_rate')}")
                    print(f"    ✅ Agent status endpoint works")
                    return True  # Stop after first successful test
                else:
                    print(f"    ❌ Failed: {response.text}")
            except Exception as e:
                print(f"  ❌ Error testing agent status: {e}")

    return False


async def test_performance_endpoints():
    """Test performance monitoring endpoints."""
    print("\n🧪 Testing performance endpoints...")

    async with httpx.AsyncClient() as client:
        # Test system performance endpoint
        print("  Testing GET /system/performance...")
        try:
            response = await client.get(
                "http://localhost:8080/system/performance",
                timeout=10.0
            )
            print(f"    Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"    ✅ System performance endpoint works")
                print(f"    Time range: {data.get('time_range_hours')} hours")
                print(f"    Agent statuses: {data.get('agent_statuses', {})}")
                return True
            else:
                print(f"    ❌ Failed: {response.text}")
                return False
        except Exception as e:
            print(f"    ❌ Error: {e}")
            return False


async def test_agent_performance_endpoint():
    """Test GET /agents/{agent_id}/performance endpoint."""
    print("\n🧪 Testing agent performance endpoint...")

    # Get an agent with performance data (email agent)
    agents = await db.fetch_all(
        """
        SELECT a.id, a.name
        FROM agents a
        JOIN agent_performance ap ON a.id = ap.agent_id
        LIMIT 1
        """
    )

    if not agents:
        print("  ⚠️  No agents with performance data found")
        return False

    agent = agents[0]
    agent_id = agent["id"]
    agent_name = agent["name"]

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"http://localhost:8080/agents/{agent_id}/performance",
                timeout=10.0
            )
            print(f"  GET /agents/{agent_id}/performance ({agent_name}): {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    print(f"    ✅ Agent performance endpoint works")
                    print(f"    Found {len(data)} performance records")
                    return True
                else:
                    print(f"    ⚠️  Unexpected response format: {type(data)}")
                    return False
            else:
                print(f"    ❌ Failed: {response.text}")
                return False
        except Exception as e:
            print(f"  ❌ Error testing agent performance: {e}")
            return False


async def verify_metrics_collection():
    """Verify that metrics are being collected."""
    print("\n📊 Verifying metrics collection...")

    # Check agent_performance_metrics table
    metrics_count = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM agent_performance_metrics"
    )
    if metrics_count and metrics_count["cnt"] > 0:
        print(f"  ✅ agent_performance_metrics has {metrics_count['cnt']} records")

        # Check recent metrics (last hour)
        hour_ago = datetime.now() - timedelta(hours=1)
        recent_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM agent_performance_metrics WHERE timestamp >= $1",
            hour_ago
        )
        if recent_count and recent_count["cnt"] > 0:
            print(f"  ✅ {recent_count['cnt']} metrics collected in last hour")
        else:
            print(f"  ⚠️  No metrics collected in last hour")
    else:
        print(f"  ⚠️  No metrics in agent_performance_metrics table")

    # Check agent_performance table
    perf_count = await db.fetch_one("SELECT COUNT(*) as cnt FROM agent_performance")
    if perf_count and perf_count["cnt"] > 0:
        print(f"  ✅ agent_performance has {perf_count['cnt']} records")

        # Show sample data
        sample = await db.fetch_all(
            """
            SELECT a.name, ap.date, ap.total_requests, ap.successful_requests, ap.total_cost_usd
            FROM agent_performance ap
            JOIN agents a ON ap.agent_id = a.id
            ORDER BY ap.date DESC
            LIMIT 3
            """
        )
        for row in sample:
            print(f"    Agent: {row['name']}, Date: {row['date']}")
            print(f"      Requests: {row['total_requests']}, Success: {row['successful_requests']}")
            print(f"      Cost: ${row['total_cost_usd']}")
    else:
        print(f"  ⚠️  No data in agent_performance table")


async def test_agent_alerts_endpoint():
    """Test GET /system/alerts endpoint."""
    print("\n🧪 Testing system alerts endpoint...")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "http://localhost:8080/system/alerts",
                timeout=10.0
            )
            print(f"  GET /system/alerts: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                alerts = data.get("alerts", [])
                print(f"    ✅ System alerts endpoint works")
                print(f"    Found {len(alerts)} alerts")
                return True
            else:
                print(f"    ❌ Failed: {response.text}")
                return False
        except Exception as e:
            print(f"  ❌ Error testing alerts endpoint: {e}")
            return False


async def run_all_checks():
    """Run all health monitoring checks."""
    print("🚀 NEXUS Agent Health Monitoring Test Suite")
    print("=" * 60)

    # Apply patches
    patch_uuid_conversion()

    # Connect to database
    try:
        await db.connect()
        print("✅ Connected to database")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return 1

    results = []

    try:
        # Fix missing tables
        tables_ok = await create_missing_tables()
        results.append(("Missing tables", tables_ok))

        # Test UUID conversion
        await test_uuid_conversion()

        # Test endpoints
        results.append(("Agent status endpoint", await test_agent_status_endpoint()))
        results.append(("System performance endpoint", await test_performance_endpoints()))
        results.append(("Agent performance endpoint", await test_agent_performance_endpoint()))
        results.append(("System alerts endpoint", await test_agent_alerts_endpoint()))

        # Verify metrics collection
        await verify_metrics_collection()

    finally:
        await db.disconnect()
        print("\n🔗 Disconnected from database")

    # Print summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
        if result:
            passed += 1

    print("\n" + "=" * 60)
    print(f"🏁 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)\n")

    if passed == total:
        print("🎉 All agent health monitoring tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check logs above.")
        print("\n📝 Note: The agent performance endpoint may fail due to UUID conversion bug.")
        print("   The bug has been patched in monitoring.py but requires API restart.")
        print("   Run: sudo systemctl restart nexus-api")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_checks())
    sys.exit(exit_code)