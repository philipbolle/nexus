#!/usr/bin/env python3
"""
Apply missing database migrations.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def check_column_exists(table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    from app.database import db
    result = await db.fetch_one(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = $1 AND column_name = $2
        """,
        table, column
    )
    return bool(result)

async def check_table_exists(table: str) -> bool:
    """Check if a table exists."""
    from app.database import db
    result = await db.fetch_one(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_name = $1
        """,
        table
    )
    return bool(result)

async def apply_migrations():
    """Apply missing migrations."""
    from app.database import db

    await db.connect()

    try:
        print("Checking database schema...")

        # 1. Check config column in agents table
        if not await check_column_exists("agents", "config"):
            print("Adding config column to agents table...")
            await db.execute("""
                ALTER TABLE agents ADD COLUMN IF NOT EXISTS config JSONB DEFAULT '{}';
                UPDATE agents SET config = '{}' WHERE config IS NULL;
            """)
            print("✅ Added config column to agents table")
        else:
            print("✅ config column already exists in agents table")

        # 2. Check system_alerts table
        if not await check_table_exists("system_alerts"):
            print("Creating system_alerts table...")
            await db.execute("""
                CREATE TABLE system_alerts (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    alert_type VARCHAR(100) NOT NULL,
                    severity VARCHAR(20) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    source_service VARCHAR(100),
                    related_entity_type VARCHAR(100),
                    related_entity_id UUID,
                    acknowledged BOOLEAN DEFAULT false,
                    acknowledged_at TIMESTAMPTZ,
                    acknowledged_by VARCHAR(100),
                    resolved BOOLEAN DEFAULT false,
                    resolved_at TIMESTAMPTZ,
                    resolution_notes TEXT,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE INDEX idx_system_alerts_severity ON system_alerts(severity);
                CREATE INDEX idx_system_alerts_acknowledged ON system_alerts(acknowledged) WHERE acknowledged = false;
                CREATE INDEX idx_system_alerts_created_at ON system_alerts(created_at DESC);
            """)
            print("✅ Created system_alerts table")
        else:
            print("✅ system_alerts table already exists")

        # 3. Check swarm tables (should exist via schema/04_SWARM_COMMUNICATION.sql)
        # Just verify swarms table exists
        if not await check_table_exists("swarms"):
            print("⚠ swarms table missing - swarm schema may not be applied")
        else:
            print("✅ swarms table exists")

        print("\n✅ Migration check completed")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(apply_migrations())