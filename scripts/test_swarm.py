#!/usr/bin/env python3
"""
Test script for NEXUS Swarm Communication Layer.

Tests Redis Pub/Sub, event bus, RAFT consensus, voting system, and API endpoints.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Initialize database connection before imports that might use it
from app.database import db
from app.config import settings


async def test_redis_connection():
    """Test Redis connection via swarm pubsub."""
    try:
        from app.agents.swarm.pubsub import SwarmPubSub

        settings = Settings()
        pubsub = SwarmPubSub(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password
        )

        await pubsub.initialize()

        # Test basic publish/subscribe
        test_channel = "test:swarm:connection"
        messages = []

        async def handler(channel, message):
            messages.append((channel, message))

        await pubsub.subscribe(test_channel, handler)
        await pubsub.publish(test_channel, "test_message")

        # Give time for message delivery
        await asyncio.sleep(0.1)

        await pubsub.unsubscribe(test_channel, handler)
        await pubsub.close()

        print("✅ Redis Pub/Sub connection test passed")
        return True

    except Exception as e:
        print(f"❌ Redis Pub/Sub connection test failed: {e}")
        return False


async def test_database_tables():
    """Verify swarm communication tables exist in database."""
    try:
        from app.database import db

        # Check for key swarm tables
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
            if not result or not result["exists"]:
                print(f"❌ Swarm table '{table}' not found in database")
                return False

        print("✅ All swarm communication tables exist")
        return True

    except Exception as e:
        print(f"❌ Database table check failed: {e}")
        return False


async def test_swarm_agent_creation():
    """Test swarm agent initialization."""
    try:
        from app.agents.swarm.agent import SwarmAgent

        agent = SwarmAgent(
            name="TestSwarmAgent",
            agent_type="test",
            capabilities=["test"]
        )

        await agent.initialize()

        # Check swarm capabilities
        assert hasattr(agent, 'swarm_id'), "Agent missing swarm_id"
        assert hasattr(agent, 'swarm_role'), "Agent missing swarm_role"
        assert hasattr(agent, 'send_swarm_message'), "Agent missing send_swarm_message method"

        await agent.cleanup()

        print("✅ Swarm agent creation test passed")
        return True

    except Exception as e:
        print(f"❌ Swarm agent creation test failed: {e}")
        return False


async def test_event_bus():
    """Test event bus functionality."""
    try:
        from app.agents.swarm.event_bus import SwarmEventBus

        settings = Settings()
        event_bus = SwarmEventBus(
            redis_host=settings.redis_host,
            redis_port=settings.redis_port,
            redis_password=settings.redis_password
        )

        await event_bus.initialize()

        # Test event publishing
        test_event = {
            "event_type": "test_event",
            "event_data": {"test": "data"},
            "source_agent_id": "test_agent",
            "swarm_id": "test_swarm"
        }

        event_id = await event_bus.publish_event(**test_event)
        assert event_id, "Event ID not returned"

        await event_bus.close()

        print("✅ Event bus test passed")
        return True

    except Exception as e:
        print(f"❌ Event bus test failed: {e}")
        return False


async def test_voting_system():
    """Test voting system functionality."""
    try:
        from app.agents.swarm.voting import VotingSystem, VotingStrategy

        voting = VotingSystem()

        # Test vote creation
        vote_id = await voting.create_vote(
            swarm_id="test_swarm",
            subject="Test Vote",
            description="Testing voting system",
            options=["option_a", "option_b", "option_c"],
            voting_strategy=VotingStrategy.SIMPLE_MAJORITY,
            required_quorum=0.5,
            created_by_agent_id="test_agent"
        )

        assert vote_id, "Vote ID not returned"

        # Test vote casting
        await voting.cast_vote(
            vote_id=vote_id,
            agent_id="test_agent_1",
            option="option_a",
            confidence=0.8,
            rationale="Test vote"
        )

        # Test vote results
        results = await voting.get_vote_results(vote_id)
        assert results is not None, "Vote results not returned"

        print("✅ Voting system test passed")
        return True

    except Exception as e:
        print(f"❌ Voting system test failed: {e}")
        return False


async def test_raft_consensus():
    """Test RAFT consensus algorithm."""
    try:
        from app.agents.swarm.raft import RaftNode, RaftState

        # Create a test RAFT node
        node = RaftNode(
            node_id="test_node_1",
            swarm_id="test_swarm",
            peer_ids=["test_node_2", "test_node_3"]
        )

        await node.initialize()

        # Check initial state
        assert node.state == RaftState.FOLLOWER, f"Expected FOLLOWER state, got {node.state}"

        await node.cleanup()

        print("✅ RAFT consensus test passed")
        return True

    except Exception as e:
        print(f"❌ RAFT consensus test failed: {e}")
        return False


async def test_api_endpoints():
    """Test swarm API endpoints via FastAPI TestClient."""
    try:
        # Import TestClient
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)

        # Test swarm creation endpoint
        swarm_data = {
            "name": "Test Swarm",
            "description": "Test swarm for API testing",
            "purpose": "testing",
            "swarm_type": "collaborative",
            "consensus_protocol": "raft",
            "voting_threshold": 0.5,
            "max_members": 10,
            "auto_scaling": True,
            "health_check_interval_seconds": 60,
            "leader_election_timeout_ms": 5000,
            "heartbeat_interval_ms": 1000,
            "metadata": {"test": True}
        }

        response = client.post("/swarm/", json=swarm_data)
        assert response.status_code in [200, 201], f"Swarm creation failed: {response.status_code}"

        swarm = response.json()
        swarm_id = swarm.get("id")
        assert swarm_id, "Swarm ID not returned"

        # Test getting swarm
        response = client.get(f"/swarm/{swarm_id}")
        assert response.status_code == 200, f"Swarm retrieval failed: {response.status_code}"

        # Test listing swarms
        response = client.get("/swarm/")
        assert response.status_code == 200, f"Swarm listing failed: {response.status_code}"

        print("✅ API endpoints test passed")
        return True

    except Exception as e:
        print(f"❌ API endpoints test failed: {e}")
        return False


async def run_all_tests():
    """Run all swarm communication layer tests."""
    print("🧪 Starting NEXUS Swarm Communication Layer Tests")
    print("=" * 60)

    test_results = []

    # Run tests
    tests = [
        ("Redis Connection", test_redis_connection),
        ("Database Tables", test_database_tables),
        ("Swarm Agent Creation", test_swarm_agent_creation),
        ("Event Bus", test_event_bus),
        ("Voting System", test_voting_system),
        ("RAFT Consensus", test_raft_consensus),
        ("API Endpoints", test_api_endpoints),
    ]

    for test_name, test_func in tests:
        print(f"\n📋 Testing: {test_name}")
        try:
            result = await test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} raised exception: {e}")
            test_results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1

    print(f"\n🎯 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n✨ All swarm communication layer tests passed!")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed")
        return False


def main():
    """Main entry point."""
    # Check if Docker containers are running
    print("🔍 Checking Docker containers...")

    try:
        import subprocess
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )

        running_containers = result.stdout.splitlines()
        required_containers = ["nexus-redis", "nexus-postgres"]

        missing = [c for c in required_containers if c not in running_containers]
        if missing:
            print(f"❌ Missing required containers: {missing}")
            print("Please start NEXUS system with: ./scripts/start_session.sh")
            return 1
        else:
            print("✅ Required containers are running")
    except Exception as e:
        print(f"⚠️  Could not check Docker containers: {e}")
        print("Continuing with tests...")

    # Run async tests
    success = asyncio.run(run_all_tests())

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())