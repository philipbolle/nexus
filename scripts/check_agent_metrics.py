#!/usr/bin/env python3
"""
Check agent performance metrics in database.
Verifies tables exist and shows sample data.
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import db
from app.agents.monitoring import performance_monitor


async def check_tables_exist():
    """Check if required monitoring tables exist."""
    tables = [
        "agent_performance",
        "agent_performance_metrics",
        "system_alerts"
    ]

    print("🔍 Checking monitoring tables existence...")

    for table in tables:
        try:
            result = await db.fetch_one(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = $1
                );
                """,
                table
            )
            exists = result["exists"] if result else False
            status = "✅ EXISTS" if exists else "❌ MISSING"
            print(f"  {table:30} {status}")

            if exists:
                # Count rows
                count_result = await db.fetch_one(f"SELECT COUNT(*) as cnt FROM {table}")
                print(f"    Rows: {count_result['cnt']}")
        except Exception as e:
            print(f"  {table:30} ❌ ERROR: {e}")


async def check_agent_performance_data():
    """Check agent_performance table for sample data."""
    print("\n📊 Checking agent_performance data...")

    try:
        # Get recent performance records
        rows = await db.fetch_all(
            """
            SELECT ap.*, a.name as agent_name
            FROM agent_performance ap
            JOIN agents a ON ap.agent_id = a.id
            ORDER BY ap.date DESC
            LIMIT 5
            """
        )

        if rows:
            print(f"  Found {len(rows)} recent performance records:")
            for row in rows:
                print(f"    Agent: {row['agent_name']} ({row['agent_id']})")
                print(f"      Date: {row['date']}, Requests: {row['total_requests']}")
                print(f"      Success: {row['successful_requests']}, Cost: ${row['total_cost_usd']}")
                print(f"      Avg latency: {row['avg_latency_ms']}ms")
                print()
        else:
            print("  No agent_performance records found.")

    except Exception as e:
        print(f"  ❌ Error querying agent_performance: {e}")


async def check_agent_performance_metrics():
    """Check agent_performance_metrics table for sample data."""
    print("\n📈 Checking agent_performance_metrics data...")

    try:
        # Check if table exists first
        result = await db.fetch_one(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'agent_performance_metrics'
            );
            """
        )

        if not result or not result["exists"]:
            print("  Table 'agent_performance_metrics' does not exist.")
            return

        # Get recent metrics
        rows = await db.fetch_all(
            """
            SELECT agent_id, metric_type, COUNT(*) as count,
                   MIN(timestamp) as earliest, MAX(timestamp) as latest
            FROM agent_performance_metrics
            GROUP BY agent_id, metric_type
            ORDER BY count DESC
            LIMIT 10
            """
        )

        if rows:
            print(f"  Found metrics for {len(rows)} agent/metric combinations:")
            for row in rows:
                print(f"    Agent: {row['agent_id']}")
                print(f"      Metric: {row['metric_type']}, Count: {row['count']}")
                print(f"      Time range: {row['earliest']} to {row['latest']}")
                print()
        else:
            print("  No agent_performance_metrics records found.")

    except Exception as e:
        print(f"  ❌ Error querying agent_performance_metrics: {e}")


async def check_performance_monitor_status():
    """Check if performance monitor is initialized."""
    print("\n🤖 Checking PerformanceMonitor status...")

    try:
        # Check if registry is set
        if performance_monitor.registry:
            print("  ✅ PerformanceMonitor has registry reference")

            # Try to get agent status counts
            if hasattr(performance_monitor, '_get_agent_status_counts'):
                counts = await performance_monitor._get_agent_status_counts()
                print(f"  Agent status counts: {counts}")
            else:
                print("  ⚠️  Cannot check agent status counts")
        else:
            print("  ⚠️  PerformanceMonitor registry not set (may not be initialized)")

        # Check if background tasks are running
        if performance_monitor._metrics_task:
            print("  ✅ Metrics collection task is running")
        else:
            print("  ⚠️  Metrics collection task not running")

        if performance_monitor._alert_check_task:
            print("  ✅ Alert check task is running")
        else:
            print("  ⚠️  Alert check task not running")

    except Exception as e:
        print(f"  ❌ Error checking performance monitor: {e}")


async def test_performance_endpoints():
    """Test performance endpoints via HTTP."""
    print("\n🌐 Testing performance endpoints...")

    import httpx

    async with httpx.AsyncClient() as client:
        # Test system performance endpoint
        try:
            response = await client.get("http://localhost:8080/system/performance", timeout=10.0)
            print(f"  GET /system/performance: {response.status_code}")
            if response.status_code == 200:
                print(f"    Response: {response.json()}")
            else:
                print(f"    Error: {response.text}")
        except Exception as e:
            print(f"  ❌ Failed to call /system/performance: {e}")

        # Test agent performance endpoint
        try:
            agent_id = "667c97fc-fa58-4644-8b85-9b7d941fd8d5"  # Email agent
            response = await client.get(
                f"http://localhost:8080/agents/{agent_id}/performance",
                timeout=10.0
            )
            print(f"  GET /agents/{agent_id}/performance: {response.status_code}")
            if response.status_code == 200:
                print(f"    Response: {response.json()}")
            else:
                print(f"    Error: {response.text}")
        except Exception as e:
            print(f"  ❌ Failed to call agent performance endpoint: {e}")


async def main():
    """Run all checks."""
    print("🔧 NEXUS Agent Performance Metrics Check")
    print("=" * 60)

    # Connect to database
    try:
        await db.connect()
        print("✅ Connected to database")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return 1

    try:
        await check_tables_exist()
        await check_agent_performance_data()
        await check_agent_performance_metrics()
        await check_performance_monitor_status()
        await test_performance_endpoints()
    finally:
        await db.disconnect()
        print("\n🔗 Disconnected from database")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)