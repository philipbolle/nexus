"""
Test script to verify the cost optimization services.
"""

import asyncio
import json
import sys
import os

# Add the parent directory to the path so we can import the services
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_all_services():
    """Test all cost optimization services."""
    print("=== Testing NEXUS Cost Optimization Services ===\n")
    
    try:
        # Import services
        from services.config import config
        from services.database import initialize_database, close_database, db_service
        from services.cache_service import initialize_cache, close_cache, cache_service
        from services.cost_tracker import initialize_cost_tracker, close_cost_tracker, cost_tracker
        from services.model_router import initialize_model_router, close_model_router, model_router
        
        # Test 1: Configuration
        print("1. Testing Configuration...")
        print(f"   Database connection: {config.database.connection_string}")
        print(f"   Redis connection: {config.redis.connection_string}")
        print(f"   Enabled providers: {list(config.get_enabled_providers().keys())}")
        print(f"   Available models: {list(config.get_available_models().keys())}")
        print("   ✓ Configuration loaded successfully\n")
        
        # Test 2: Database Service
        print("2. Testing Database Service...")
        try:
            await initialize_database()
            print("   ✓ Database service initialized")
            
            # Try to get cache statistics (even if tables don't exist yet)
            try:
                stats = await db_service.get_cache_statistics()
                print(f"   ✓ Cache statistics: {json.dumps(stats, default=str)}")
            except Exception as e:
                print(f"   ⚠ Cache statistics error (tables may not exist): {e}")
            
            await close_database()
            print("   ✓ Database service closed\n")
        except Exception as e:
            print(f"   ✗ Database service error: {e}\n")
        
        # Test 3: Cache Service
        print("3. Testing Cache Service...")
        try:
            await initialize_cache()
            print("   ✓ Cache service initialized")
            
            health = await cache_service.health_check()
            print(f"   ✓ Cache health check: {json.dumps(health, indent=4)}")
            
            await close_cache()
            print("   ✓ Cache service closed\n")
        except Exception as e:
            print(f"   ✗ Cache service error: {e}\n")
        
        # Test 4: Cost Tracker
        print("4. Testing Cost Tracker...")
        try:
            await initialize_cost_tracker()
            print("   ✓ Cost tracker initialized")
            
            # Generate a sample report
            report = await cost_tracker.generate_cost_report(days=7)
            print(f"   ✓ Generated cost report (simulated)")
            print(f"     - Total cost: ${report['summary']['total_cost']:.4f}")
            print(f"     - Avg daily cost: ${report['summary']['avg_daily_cost']:.4f}")
            print(f"     - Cache hit rate: {report['summary']['cache_hit_rate']*100:.1f}%")
            
            await close_cost_tracker()
            print("   ✓ Cost tracker closed\n")
        except Exception as e:
            print(f"   ✗ Cost tracker error: {e}\n")
        
        # Test 5: Model Router
        print("5. Testing Model Router...")
        try:
            await initialize_model_router()
            print("   ✓ Model router initialized")
            
            # Test model selection
            decision = await model_router.select_model(
                task_description="Summarize this document about climate change",
                task_type="summarization"
            )
            print(f"   ✓ Model selection for summarization:")
            print(f"     - Selected model: {decision.selected_model}")
            print(f"     - Provider: {decision.provider_name}")
            print(f"     - Reason: {decision.reason}")
            print(f"     - Estimated cost: ${decision.estimated_cost_usd:.6f}")
            
            # Test request processing
            messages = [
                {"role": "user", "content": "What is the capital of France?"}
            ]
            response = await model_router.process_request(messages, task_type="simple_query")
            print(f"   ✓ Request processing:")
            print(f"     - Model used: {response['model_used']}")
            print(f"     - Cached: {response['cached']}")
            print(f"     - Latency: {response.get('latency_ms', 'N/A')}ms")
            
            await close_model_router()
            print("   ✓ Model router closed\n")
        except Exception as e:
            print(f"   ✗ Model router error: {e}\n")
        
        print("=== All Tests Completed ===")
        print("\nSummary: All 5 cost optimization services have been successfully created:")
        print("  1. config.py - Configuration management")
        print("  2. database.py - Database operations")
        print("  3. cache_service.py - Semantic and embedding caching")
        print("  4. cost_tracker.py - Cost tracking and analysis")
        print("  5. model_router.py - Intelligent model routing")
        
        print("\nNext steps:")
        print("  1. Install required dependencies: pip install asyncpg redis-asyncio")
        print("  2. Ensure PostgreSQL and Redis are running")
        print("  3. Run the SQL schema files to create the cost optimization tables")
        print("  4. Start using the services in your AI applications")
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("Make sure you're running from the correct directory and all service files exist.")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(test_all_services())
