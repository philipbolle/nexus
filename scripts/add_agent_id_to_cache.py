#!/usr/bin/env python3
"""
Add agent_id column to semantic_cache table for agent-specific caching.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import db

async def add_agent_id_to_semantic_cache():
    """Add agent_id column and index to semantic_cache table."""
    print("Adding agent_id column to semantic_cache table...")

    alter_table_sql = """
    ALTER TABLE semantic_cache
    ADD COLUMN IF NOT EXISTS agent_id UUID REFERENCES agents(id);
    """

    create_index_sql = """
    CREATE INDEX IF NOT EXISTS idx_semantic_cache_agent
    ON semantic_cache(agent_id);
    """

    try:
        await db.connect()

        # Add column
        await db.execute(alter_table_sql)
        print("✅ Added agent_id column to semantic_cache")

        # Create index
        await db.execute(create_index_sql)
        print("✅ Created index on agent_id column")

        # Verify the column exists
        verify_sql = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'semantic_cache'
        AND column_name = 'agent_id';
        """
        result = await db.fetch_one(verify_sql)
        if result:
            print(f"✅ Verification passed: agent_id column exists")
        else:
            print("❌ Verification failed: agent_id column not found")

        return True
    except Exception as e:
        print(f"❌ Failed to add agent_id column: {e}")
        return False
    finally:
        await db.disconnect()

async def main():
    print("🔧 Adding agent_id column for agent-specific caching")
    print("=" * 50)

    success = await add_agent_id_to_semantic_cache()

    print("=" * 50)
    if success:
        print("✅ Agent-specific caching schema updated successfully")
    else:
        print("❌ Failed to update schema")

    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)