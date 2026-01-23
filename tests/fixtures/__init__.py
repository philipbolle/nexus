"""
Test fixtures for NEXUS test suite.

Shared fixtures for agent framework and swarm tests.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from app.agents.base import AgentType, AgentStatus


@pytest.fixture
def sample_agent_id():
    """Generate a sample agent ID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_swarm_id():
    """Generate a sample swarm ID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_user_id():
    """Generate a sample user ID."""
    return "test_user"


@pytest.fixture
def sample_task_id():
    """Generate a sample task ID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_session_id():
    """Generate a sample session ID."""
    return str(uuid.uuid4())


@pytest.fixture
def mock_agent_base():
    """Create a mock BaseAgent with common attributes."""
    agent = Mock()
    agent.agent_id = str(uuid.uuid4())
    agent.name = "test_agent"
    agent.agent_type = AgentType.DOMAIN
    agent.status = AgentStatus.IDLE
    agent.description = "Test agent"
    agent.system_prompt = "You are a test agent"
    agent.capabilities = ["test_capability"]
    agent.domain = "testing"
    agent.config = {}
    agent.metrics = {}
    agent.created_at = datetime.now()
    agent.updated_at = datetime.now()
    agent.initialize = AsyncMock()
    agent.cleanup = AsyncMock()
    agent.execute = AsyncMock(return_value={"result": "success"})
    return agent


@pytest.fixture
def mock_swarm_agent():
    """Create a mock SwarmAgent with swarm capabilities."""
    agent = Mock()
    agent.agent_id = str(uuid.uuid4())
    agent.name = "swarm_agent"
    agent.agent_type = AgentType.DOMAIN
    agent.status = AgentStatus.IDLE
    agent.swarm_id = "test_swarm"
    agent.swarm_role = "worker"
    agent.swarm_channels = set()
    agent.initialize = AsyncMock()
    agent.cleanup = AsyncMock()
    agent.join_swarm = AsyncMock()
    agent.leave_swarm = AsyncMock()
    agent.send_swarm_message = AsyncMock()
    agent.receive_swarm_message = AsyncMock(return_value=None)
    return agent


@pytest.fixture
def mock_registry():
    """Create a mock AgentRegistry."""
    registry = Mock()
    registry.agents = {}
    registry.agent_types = {}
    registry.capability_index = {}
    registry.domain_index = {}
    registry.status = "running"
    registry.initialize = AsyncMock()
    registry.shutdown = AsyncMock()
    registry.register_agent_type = AsyncMock()
    registry.create_agent = AsyncMock()
    registry.get_agent = AsyncMock()
    registry.get_agent_by_name = AsyncMock()
    registry.update_agent = AsyncMock()
    registry.delete_agent = AsyncMock()
    registry.list_agents = AsyncMock(return_value=[])
    registry.get_registry_status = AsyncMock(return_value={})
    registry.select_agent_for_task = AsyncMock(return_value=(None, 0.0))
    registry.start_agent = AsyncMock(return_value=True)
    registry.stop_agent = AsyncMock(return_value=True)
    return registry


@pytest.fixture
def mock_pubsub():
    """Create a mock SwarmPubSub."""
    pubsub = AsyncMock()
    pubsub.initialize = AsyncMock()
    pubsub.close = AsyncMock()
    pubsub.publish = AsyncMock()
    pubsub.subscribe = AsyncMock()
    pubsub.psubscribe = AsyncMock()
    pubsub.unsubscribe = AsyncMock()
    pubsub.punsubscribe = AsyncMock()
    pubsub.get_message = AsyncMock(return_value=None)
    pubsub.get_messages = AsyncMock()
    return pubsub


@pytest.fixture
def mock_database():
    """Create a mock database connection."""
    db = Mock()
    db.fetch_one = AsyncMock(return_value=None)
    db.fetch_all = AsyncMock(return_value=[])
    db.execute = AsyncMock()
    db.fetch_val = AsyncMock(return_value=None)
    return db


@pytest.fixture
def sample_agent_create_data():
    """Sample data for creating an agent."""
    return {
        "name": "test_agent",
        "agent_type": "domain",
        "description": "Test agent",
        "system_prompt": "You are a test agent",
        "capabilities": ["test_capability"],
        "domain": "testing",
        "config": {}
    }


@pytest.fixture
def sample_swarm_create_data():
    """Sample data for creating a swarm."""
    return {
        "name": "test_swarm",
        "description": "Test swarm",
        "config": {"max_members": 10},
        "metadata": {}
    }


@pytest.fixture
def sample_task_data():
    """Sample data for submitting a task."""
    return {
        "description": "Test task description",
        "parameters": {"param1": "value1"},
        "priority": "medium",
        "timeout_seconds": 300
    }


@pytest.fixture
def sample_session_data():
    """Sample data for creating a session."""
    return {
        "agent_id": str(uuid.uuid4()),
        "user_id": "test_user",
        "config": {
            "max_messages": 100,
            "timeout_minutes": 30,
            "context": {"topic": "testing"}
        }
    }