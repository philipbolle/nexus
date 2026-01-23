#!/usr/bin/env python3
"""
Simple test script for NEXUS Swarm Communication Layer.

Verifies that swarm components can be imported and initialized without errors.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def test_imports():
    """Test that all swarm modules can be imported."""
    print("🔍 Testing module imports...")

    modules = [
        "app.agents.swarm.pubsub",
        "app.agents.swarm.event_bus",
        "app.agents.swarm.raft",
        "app.agents.swarm.voting",
        "app.agents.swarm.agent",
        "app.agents.swarm.swarm_orchestrator",
        "app.routers.swarm"
    ]

    for module_name in modules:
        try:
            __import__(module_name)
            print(f"  ✅ {module_name}")
        except ImportError as e:
            print(f"  ❌ {module_name}: {e}")
            return False

    print("✅ All modules imported successfully")
    return True


async def test_database_connection():
    """Test database connection and swarm tables."""
    print("\n🔍 Testing database connection...")

    try:
        from app.database import db

        # Connect to database
        await db.connect()
        print("  ✅ Database connection established")

        # Check for swarm tables
        swarm_tables = [
            "swarms",
            "swarm_memberships",
            "consensus_groups",
            "votes",
            "vote_responses",
            "swarm_messages",
            "swarm_events",
            "swarm_performance"
        ]

        for table in swarm_tables:
            result = await db.fetch_one(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                table
            )
            if result and result["exists"]:
                print(f"  ✅ Table '{table}' exists")
            else:
                print(f"  ❌ Table '{table}' not found")
                return False

        print("✅ All swarm tables exist")
        return True

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False


async def test_redis_pubsub():
    """Test Redis Pub/Sub initialization."""
    print("\n🔍 Testing Redis Pub/Sub...")

    try:
        from app.agents.swarm.pubsub import SwarmPubSub

        pubsub = SwarmPubSub()
        await pubsub.initialize()
        print("  ✅ SwarmPubSub initialized")

        # Test basic functionality
        test_channel = "test:swarm"
        messages_received = []

        # Start listening in background
        async def listen_for_messages():
            try:
                async for message in pubsub.listen():
                    if message and message.get("channel") == test_channel:
                        messages_received.append(message)
                        print(f"  📨 Received message on {test_channel}: {message.get('data')}")
                        break  # Just receive one message for test
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"  ⚠️  Listener error: {e}")

        # Subscribe to channel
        await pubsub.subscribe(test_channel)
        print(f"  ✅ Subscribed to channel: {test_channel}")

        # Start listener
        listener_task = asyncio.create_task(listen_for_messages())
        await asyncio.sleep(0.1)  # Let listener start

        # Publish test message
        test_message = {"test": "message", "timestamp": "now"}
        await pubsub.publish(test_channel, test_message)
        print(f"  ✅ Published test message to: {test_channel}")

        # Give time for message delivery
        await asyncio.sleep(0.5)

        # Cancel listener
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass

        # Unsubscribe and close
        await pubsub.unsubscribe(test_channel)
        await pubsub.close()

        # Check if message was received
        if messages_received:
            print("✅ Redis Pub/Sub test passed")
            return True
        else:
            print("❌ Redis Pub/Sub test failed: No messages received")
            return False

    except Exception as e:
        print(f"❌ Redis Pub/Sub test failed: {e}")
        return False


async def test_swarm_agent():
    """Test swarm agent initialization."""
    print("\n🔍 Testing SwarmAgent...")

    try:
        from app.agents.swarm.agent import SwarmAgent
        from app.agents.base import AgentType

        # Use unique name to avoid duplicate key errors
        import uuid
        unique_name = f"TestSwarmAgent_{uuid.uuid4().hex[:8]}"

        agent = SwarmAgent(
            name=unique_name,
            agent_type=AgentType.DOMAIN,
            capabilities=["test"]
        )

        await agent.initialize()
        print("  ✅ SwarmAgent initialized")

        # Verify swarm capabilities
        required_attrs = [
            'swarm_id',
            'swarm_role',
            'send_swarm_message',
            'receive_swarm_messages',
            'publish_swarm_event',
            'create_vote',
            'cast_vote'
        ]

        for attr in required_attrs:
            if hasattr(agent, attr):
                print(f"  ✅ Has {attr}")
            else:
                print(f"  ❌ Missing {attr}")
                return False

        await agent.cleanup()
        print("✅ SwarmAgent test passed")
        return True

    except Exception as e:
        print(f"❌ SwarmAgent test failed: {e}")
        return False


async def test_voting_system():
    """Test voting system initialization."""
    print("\n🔍 Testing VotingSystem...")

    try:
        from app.agents.swarm.voting import VotingSystem, VotingStrategy

        voting = VotingSystem(swarm_id="test_swarm")
        print("  ✅ VotingSystem initialized")

        # Test vote creation (would require database connection)
        # We'll just test that the class is properly set up
        assert voting.swarm_id == "test_swarm"

        print("✅ VotingSystem test passed")
        return True

    except Exception as e:
        print(f"❌ VotingSystem test failed: {e}")
        return False


async def test_event_bus():
    """Test event bus initialization."""
    print("\n🔍 Testing SwarmEventBus...")

    try:
        from app.agents.swarm.event_bus import SwarmEventBus

        event_bus = SwarmEventBus()
        await event_bus.initialize()
        print("  ✅ SwarmEventBus initialized")

        await event_bus.close()
        print("✅ SwarmEventBus test passed")
        return True

    except Exception as e:
        print(f"❌ SwarmEventBus test failed: {e}")
        return False


async def test_raft_node():
    """Test RAFT node initialization."""
    print("\n🔍 Testing RaftNode...")

    try:
        from app.agents.swarm.raft import RaftNode, RaftState
        import uuid

        # Generate valid UUIDs for testing
        test_group_id = str(uuid.uuid4())
        test_agent_id = str(uuid.uuid4())

        node = RaftNode(
            consensus_group_id=test_group_id,
            agent_id=test_agent_id,
            agent_name="Test Agent",
            swarm_id="test_swarm"
        )

        await node.initialize()
        print("  ✅ RaftNode initialized")

        # Check initial state
        assert node.state == RaftState.FOLLOWER

        await node.close()  # Use close() instead of cleanup()
        print("✅ RaftNode test passed")
        return True

    except Exception as e:
        print(f"❌ RaftNode test failed: {e}")
        return False


async def test_swarm_orchestrator():
    """Test swarm orchestrator initialization."""
    print("\n🔍 Testing SwarmOrchestratorAgent...")

    try:
        from app.agents.swarm.swarm_orchestrator import SwarmOrchestratorAgent
        import uuid

        # Use unique name to avoid duplicate key errors
        unique_name = f"TestOrchestrator_{uuid.uuid4().hex[:8]}"

        orchestrator = SwarmOrchestratorAgent(
            name=unique_name,
            # Don't pass swarm_id to avoid trying to join non-existent swarm
            swarm_role="leader"
        )

        await orchestrator.initialize()
        print("  ✅ SwarmOrchestratorAgent initialized")

        # Check orchestrator-specific attributes
        required_attrs = [
            'subordinate_agents',
            'task_registry',
            'coordinate_swarm'
        ]

        for attr in required_attrs:
            if hasattr(orchestrator, attr):
                print(f"  ✅ Has {attr}")
            else:
                print(f"  ❌ Missing {attr}")
                return False

        await orchestrator.cleanup()
        print("✅ SwarmOrchestratorAgent test passed")
        return True

    except Exception as e:
        print(f"❌ SwarmOrchestratorAgent test failed: {e}")
        return False


async def test_api_router():
    """Test that swarm API router can be imported."""
    print("\n🔍 Testing Swarm API Router...")

    try:
        from app.routers.swarm import router

        # Check router has expected attributes
        assert hasattr(router, 'prefix'), "Router missing prefix"
        assert router.prefix == "/swarm", f"Expected prefix '/swarm', got '{router.prefix}'"

        print(f"  ✅ Router prefix: {router.prefix}")
        print("✅ Swarm API router test passed")
        return True

    except Exception as e:
        print(f"❌ Swarm API router test failed: {e}")
        return False


async def run_all_tests():
    """Run all swarm tests."""
    print("🧪 NEXUS Swarm Communication Layer - Basic Tests")
    print("=" * 60)

    # Initialize database first
    try:
        from app.database import db
        await db.connect()
    except Exception as e:
        print(f"⚠️  Could not connect to database: {e}")
        print("  Some tests may fail...")

    tests = [
        ("Module Imports", test_imports),
        ("Database Connection", test_database_connection),
        ("Redis Pub/Sub", test_redis_pubsub),
        ("Swarm Agent", test_swarm_agent),
        ("Voting System", test_voting_system),
        ("Event Bus", test_event_bus),
        ("RAFT Node", test_raft_node),
        ("Swarm Orchestrator", test_swarm_orchestrator),
        ("API Router", test_api_router),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ Exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n🎯 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n✨ All swarm communication layer tests passed!")
    else:
        print(f"\n⚠️  {total - passed} tests failed")

    return passed == total


def main():
    """Main entry point."""
    # Check Docker containers
    print("🔍 Checking Docker containers...")

    try:
        import subprocess
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )

        running_containers = result.stdout.splitlines()
        required = ["nexus-redis", "nexus-postgres"]

        missing = [c for c in required if c not in running_containers]
        if missing:
            print(f"⚠️  Missing containers: {missing}")
            print("  Some tests may fail. Start NEXUS with: ./scripts/start_session.sh")
        else:
            print("✅ Required containers are running")
    except Exception as e:
        print(f"⚠️  Could not check Docker containers: {e}")

    # Run tests
    success = asyncio.run(run_all_tests())

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())