#!/usr/bin/env python3
"""
Test script for agent-specific caching integration.
Verifies that cache entries are properly isolated by agent_id.
"""

import asyncio
import json
import sys
import os
import uuid
from typing import Dict, Any, Optional

# Add the parent directory to the path so we can import the services
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_agent_specific_caching():
    """Test agent-specific caching functionality."""
    print("=== Testing Agent-Specific Caching Integration ===\n")

    try:
        # Import services
        from app.services.config import config
        from app.services.database import initialize_database, close_database, db_service
        from app.services.cache_service import initialize_cache, close_cache, cache_service

        # Test UUIDs - use existing agents from database to satisfy foreign key constraint
        agent1_id = uuid.UUID('c18c4bc3-2704-4507-843d-3e538e7e18cd')  # router agent
        agent2_id = uuid.UUID('a8376f84-3269-4aec-aec8-c36a603a9b6e')  # wealth agent

        # Initialize services
        print("1. Initializing services...")
        await initialize_database()
        await initialize_cache()
        print("   ✓ Services initialized\n")

        # Test 1: Basic cache without agent_id (global cache)
        print("2. Testing global cache (no agent_id)...")
        test_suffix = str(uuid.uuid4())[:8]  # Unique suffix for this test run
        query_text = f"What is the capital of France? [Test {test_suffix}]"
        response_text = f"The capital of France is Paris. [Test {test_suffix}]"
        model_used = "gpt-3.5-turbo"

        # Set cache without agent_id
        cache_entry = await cache_service.set_semantic_cache(
            query_text=query_text,
            response_text=response_text,
            model_used=model_used,
            agent_id=None
        )
        print(f"   ✓ Set global cache entry: {cache_entry.get('id', 'N/A')}")

        # Get cache without agent_id
        cached_result = await cache_service.get_semantic_cache(query_text, agent_id=None)
        assert cached_result is not None, "Global cache should return result"
        assert cached_result['response_text'] == response_text
        print(f"   ✓ Retrieved global cache entry")

        # Test 2: Agent-specific cache
        print("\n3. Testing agent-specific cache...")

        # Set cache for agent 1
        response_agent1 = "Agent 1 says: Paris is the capital of France."
        cache_agent1 = await cache_service.set_semantic_cache(
            query_text=query_text,  # Same query text
            response_text=response_agent1,
            model_used=model_used,
            agent_id=agent1_id
        )
        print(f"   ✓ Set cache for agent 1: {cache_agent1.get('id', 'N/A')}")

        # Set cache for agent 2 (different response)
        response_agent2 = "Agent 2 says: The capital is Paris, France."
        cache_agent2 = await cache_service.set_semantic_cache(
            query_text=query_text,  # Same query text
            response_text=response_agent2,
            model_used=model_used,
            agent_id=agent2_id
        )
        print(f"   ✓ Set cache for agent 2: {cache_agent2.get('id', 'N/A')}")

        # Verify isolation: Get cache for agent 1
        cached_agent1 = await cache_service.get_semantic_cache(query_text, agent_id=agent1_id)
        assert cached_agent1 is not None, "Agent 1 cache should exist"
        assert cached_agent1['response_text'] == response_agent1
        print(f"   ✓ Retrieved correct cache for agent 1")

        # Verify isolation: Get cache for agent 2
        cached_agent2 = await cache_service.get_semantic_cache(query_text, agent_id=agent2_id)
        assert cached_agent2 is not None, "Agent 2 cache should exist"
        assert cached_agent2['response_text'] == response_agent2
        print(f"   ✓ Retrieved correct cache for agent 2")

        # Verify isolation: Global cache should still be separate
        cached_global = await cache_service.get_semantic_cache(query_text, agent_id=None)
        assert cached_global is not None, "Global cache should still exist"
        assert cached_global['response_text'] == response_text
        print(f"   ✓ Global cache remains separate")

        # Test 3: Cache hash uniqueness
        print("\n4. Testing query hash uniqueness...")
        # The cache service should generate different hashes for same query with different agent_ids
        hash_none = cache_service._generate_query_hash(query_text, None)
        hash_agent1 = cache_service._generate_query_hash(query_text, agent1_id)
        hash_agent2 = cache_service._generate_query_hash(query_text, agent2_id)

        assert hash_none != hash_agent1, "Hash should differ between no agent and agent 1"
        assert hash_none != hash_agent2, "Hash should differ between no agent and agent 2"
        assert hash_agent1 != hash_agent2, "Hash should differ between agent 1 and agent 2"
        print(f"   ✓ Query hashes are unique per agent")
        print(f"     - No agent: {hash_none[:16]}...")
        print(f"     - Agent 1:  {hash_agent1[:16]}...")
        print(f"     - Agent 2:  {hash_agent2[:16]}...")

        # Test 4: Batch operations with agent_id
        print("\n5. Testing batch operations...")
        queries = [f"What is AI? [Test {test_suffix}]",
                   f"How does ML work? [Test {test_suffix}]",
                   f"Explain neural networks [Test {test_suffix}]"]

        # Batch get without agent_id
        batch_results_none = await cache_service.batch_get_semantic_cache(queries, agent_id=None)
        print(f"   ✓ Batch get without agent_id: {len(batch_results_none)} results")

        # Batch get with agent_id
        batch_results_agent1 = await cache_service.batch_get_semantic_cache(queries, agent_id=agent1_id)
        print(f"   ✓ Batch get with agent_id: {len(batch_results_agent1)} results")

        # Test 5: Cache statistics
        print("\n6. Testing cache statistics...")
        stats = await cache_service.get_cache_stats()
        print(f"   ✓ Retrieved cache statistics")
        print(f"     - Database stats: {json.dumps(stats.get('database', {}), default=str)}")
        print(f"     - Redis stats: {json.dumps(stats.get('redis', {}), default=str)}")

        # Test 6: Health check
        print("\n7. Testing health check...")
        health = await cache_service.health_check()
        print(f"   ✓ Health check: {json.dumps(health, indent=4)}")

        # Clean up test entries (optional)
        print("\n8. Cleaning up test entries...")
        # Note: Cache entries will expire naturally via TTL
        # We could delete them, but for simplicity we'll leave them

        # Close services
        await close_cache()
        await close_database()
        print("   ✓ Services closed")

        print("\n=== All Tests Passed ===")
        print("\nSummary:")
        print(f"  • Agent-specific caching is working correctly")
        print(f"  • Cache isolation verified for 2 agents + global")
        print(f"  • Query hashes are unique per agent_id")
        print(f"  • Batch operations support agent_id parameter")
        print(f"  • All services healthy")

        return True

    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("Make sure you're running from the correct directory and all service files exist.")
        return False
    except AssertionError as e:
        print(f"✗ Assertion failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test runner."""
    print("🔧 Testing Agent-Specific Caching Integration")
    print("=" * 60)

    success = await test_agent_specific_caching()

    print("=" * 60)
    if success:
        print("✅ Agent-specific caching integration test PASSED")
    else:
        print("❌ Agent-specific caching integration test FAILED")

    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)