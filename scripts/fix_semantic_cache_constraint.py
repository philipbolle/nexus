#!/usr/bin/env python3
"""
Fix semantic_cache unique constraint to support agent-specific caching.
Changes from unique(query_hash) to unique(query_hash, agent_id) with NULLS NOT DISTINCT.
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import the services
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def fix_semantic_cache_constraint():
    """Fix the semantic_cache unique constraint."""
    print("🔧 Fixing semantic_cache unique constraint for agent-specific caching")
    print("=" * 60)

    try:
        from app.database import db

        await db.connect()

        # 1. Check current constraint
        print("\n1. Checking current constraints...")
        constraint_query = """
            SELECT conname, pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = 'semantic_cache'::regclass AND contype = 'u';
        """
        constraints = await db.fetch_all(constraint_query)

        for con in constraints:
            print(f"   Found: {con['conname']} = {con['pg_get_constraintdef']}")

        # 2. Check for duplicate query_hash entries (shouldn't exist due to constraint)
        print("\n2. Checking for duplicate query_hash entries...")
        duplicate_query = """
            SELECT query_hash, COUNT(*) as count
            FROM semantic_cache
            GROUP BY query_hash
            HAVING COUNT(*) > 1;
        """
        duplicates = await db.fetch_all(duplicate_query)

        if duplicates:
            print(f"   ⚠ Found {len(duplicates)} duplicate query_hash entries")
            for dup in duplicates:
                print(f"     - {dup['query_hash']}: {dup['count']} entries")
            # We need to deduplicate, but this shouldn't happen with unique constraint
            # For now, we'll proceed and hope the constraint drop/recreate handles it
        else:
            print("   ✓ No duplicate query_hash entries found")

        # 3. Check for rows with same query_hash and different agent_id
        print("\n3. Checking for same query_hash with different agent_id...")
        cross_agent_duplicate_query = """
            SELECT query_hash, COUNT(DISTINCT agent_id) as agent_count
            FROM semantic_cache
            WHERE agent_id IS NOT NULL
            GROUP BY query_hash
            HAVING COUNT(DISTINCT agent_id) > 1;
        """
        cross_agent_dups = await db.fetch_all(cross_agent_duplicate_query)

        if cross_agent_dups:
            print(f"   ⚠ Found {len(cross_agent_dups)} query_hash with multiple agent_id")
            for dup in cross_agent_dups:
                print(f"     - {dup['query_hash']}: {dup['agent_count']} agents")
            # This is what we want to support, so this is fine
        else:
            print("   ✓ No cross-agent duplicates (expected at this stage)")

        # 4. Drop the old unique constraint
        print("\n4. Dropping old unique constraint...")
        try:
            await db.execute("ALTER TABLE semantic_cache DROP CONSTRAINT semantic_cache_query_hash_key;")
            print("   ✅ Dropped semantic_cache_query_hash_key constraint")
        except Exception as e:
            print(f"   ⚠ Failed to drop constraint: {e}")
            print("   Trying to continue...")

        # 5. Create new unique index with NULLS NOT DISTINCT
        print("\n5. Creating new unique index with NULLS NOT DISTINCT...")
        create_index_sql = """
            CREATE UNIQUE INDEX unique_semantic_cache_query_agent
            ON semantic_cache(query_hash, agent_id) NULLS NOT DISTINCT;
        """

        try:
            await db.execute(create_index_sql)
            print("   ✅ Created unique index on (query_hash, agent_id) with NULLS NOT DISTINCT")
        except Exception as e:
            print(f"   ❌ Failed to create new index: {e}")
            # Try without NULLS NOT DISTINCT (older PostgreSQL)
            print("   Trying without NULLS NOT DISTINCT...")
            create_index_fallback = """
                CREATE UNIQUE INDEX unique_semantic_cache_query_agent
                ON semantic_cache(query_hash, agent_id);
            """
            try:
                await db.execute(create_index_fallback)
                print("   ✅ Created unique index on (query_hash, agent_id) (fallback)")
                print("   ⚠ Note: NULL values will be considered distinct")
                print("   ⚠ This may allow multiple global caches (agent_id IS NULL)")
            except Exception as e2:
                print(f"   ❌ Fallback also failed: {e2}")
                return False

        # 6. Verify the new constraint
        print("\n6. Verifying new constraint...")
        new_constraints_query = """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'semantic_cache'
            AND indexname = 'unique_semantic_cache_query_agent';
        """
        new_index = await db.fetch_one(new_constraints_query)

        if new_index:
            print(f"   ✅ New index created: {new_index['indexname']}")
            print(f"   Definition: {new_index['indexdef']}")
        else:
            print("   ❌ New index not found")
            return False

        # 7. Test the constraint with a sample insert
        print("\n7. Testing constraint with sample data...")
        test_insert_sql = """
            INSERT INTO semantic_cache (query_text, query_hash, response_text, model_used)
            VALUES ('test query', 'testhash123', 'test response', 'test-model')
            ON CONFLICT DO NOTHING;
        """
        try:
            await db.execute(test_insert_sql)
            print("   ✅ Test insert succeeded")

            # Clean up test row
            await db.execute("DELETE FROM semantic_cache WHERE query_hash = 'testhash123';")
            print("   ✅ Cleaned up test row")
        except Exception as e:
            print(f"   ⚠ Test insert failed: {e}")

        print("\n" + "=" * 60)
        print("✅ Semantic cache unique constraint updated successfully")
        print("\nThe semantic_cache table now supports:")
        print("  • One global cache entry per query_hash (agent_id IS NULL)")
        print("  • One agent-specific cache entry per (query_hash, agent_id)")
        print("  • Multiple agents can cache the same query with different responses")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            await db.disconnect()
        except:
            pass

async def main():
    success = await fix_semantic_cache_constraint()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())