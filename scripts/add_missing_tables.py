#!/usr/bin/env python3
"""
Add missing database tables required by the agent framework.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import db

async def add_agent_performance_metrics():
    """Create agent_performance_metrics table if it doesn't exist."""
    print("Creating agent_performance_metrics table...")

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS agent_performance_metrics (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        agent_id UUID REFERENCES agents(id),
        metric_type VARCHAR(100) NOT NULL,
        value DECIMAL(20,6),
        timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        tags JSONB,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(agent_id, metric_type, timestamp)
    );

    CREATE INDEX IF NOT EXISTS idx_agent_performance_metrics_agent_id
    ON agent_performance_metrics(agent_id);

    CREATE INDEX IF NOT EXISTS idx_agent_performance_metrics_timestamp
    ON agent_performance_metrics(timestamp);

    CREATE INDEX IF NOT EXISTS idx_agent_performance_metrics_type
    ON agent_performance_metrics(metric_type);
    """

    try:
        await db.connect()
        await db.execute(create_table_sql)
        print("✅ agent_performance_metrics table created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create table: {e}")
        return False
    finally:
        await db.disconnect()

async def main():
    print("🔧 Adding missing database tables for NEXUS Agent Framework")
    print("=" * 50)

    success = True

    if not await add_agent_performance_metrics():
        success = False

    print("=" * 50)
    if success:
        print("✅ All missing tables added successfully")
    else:
        print("❌ Some operations failed")

    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)