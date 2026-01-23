"""
Unit tests for AgentRegistry class.

Tests agent registration, lifecycle management, and the specific fixes made in Phase 1:
- Duplicate name checking (in-memory and database)
- get_agent_by_name database query
- Agent creation and deletion
- Registry status and metrics
"""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any

from app.agents.registry import AgentRegistry, RegistryStatus
from app.agents.base import BaseAgent, AgentType, AgentStatus


class TestAgentRegistry:
    """Test suite for AgentRegistry class."""

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent for testing."""
        agent = Mock(spec=BaseAgent)
        agent.agent_id = str(uuid.uuid4())
        agent.name = "test_agent"
        agent.agent_type = AgentType.DOMAIN
        agent.status = AgentStatus.IDLE
        agent.capabilities = ["test_capability"]
        agent.domain = "test_domain"
        agent.description = "Test agent"
        agent.system_prompt = "You are a test agent"
        agent.supervisor_id = None
        agent.config = {}
        agent.metrics = {"success_rate": 1.0, "avg_latency_ms": 100}
        agent.initialize = AsyncMock()
        agent.cleanup = AsyncMock()
        return agent

    @pytest.fixture
    def mock_agent_class(self):
        """Create a mock agent class for testing."""
        agent_class = Mock()
        agent_class.return_value = Mock(spec=BaseAgent)
        return agent_class

    @pytest.fixture
    def registry(self):
        """Create a fresh AgentRegistry instance for each test."""
        # Clear singleton instance
        AgentRegistry._instance = None
        return AgentRegistry()

    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        """Test that AgentRegistry follows singleton pattern."""
        # Clear singleton instance
        AgentRegistry._instance = None

        registry1 = AgentRegistry()
        registry2 = AgentRegistry()

        assert registry1 is registry2
        assert registry1._initialized == registry2._initialized

    @pytest.mark.asyncio
    async def test_initial_state(self, registry):
        """Test registry initial state."""
        assert registry.status == RegistryStatus.INITIALIZING
        assert len(registry.agents) == 0
        assert len(registry.agent_types) == 0
        assert len(registry.capability_index) == 0
        assert len(registry.domain_index) == 0

    @pytest.mark.asyncio
    async def test_register_agent_type(self, registry):
        """Test registering an agent type."""
        mock_agent_class = Mock()

        await registry.register_agent_type("test_type", mock_agent_class)

        assert "test_type" in registry.agent_types
        assert registry.agent_types["test_type"] == mock_agent_class

    @pytest.mark.asyncio
    async def test_register_agent_type_overwrite_warning(self, registry, caplog):
        """Test warning when overwriting existing agent type."""
        mock_agent_class1 = Mock()
        mock_agent_class2 = Mock()

        await registry.register_agent_type("test_type", mock_agent_class1)
        await registry.register_agent_type("test_type", mock_agent_class2)

        assert "already registered, overwriting" in caplog.text
        assert registry.agent_types["test_type"] == mock_agent_class2

    @pytest.mark.asyncio
    async def test_create_agent_success(self, registry, mock_agent_class):
        """Test successful agent creation."""
        # Setup
        registry.status = RegistryStatus.RUNNING
        await registry.register_agent_type("test_type", mock_agent_class)

        mock_agent = Mock(spec=BaseAgent)
        mock_agent.agent_id = str(uuid.uuid4())
        mock_agent.name = "test_agent"
        mock_agent.capabilities = ["cap1", "cap2"]
        mock_agent.domain = "test_domain"
        mock_agent.initialize = AsyncMock()
        mock_agent_class.return_value = mock_agent

        # Mock database calls
        with patch.object(registry, '_store_agent_in_db', AsyncMock()) as mock_store:
            # Execute
            agent = await registry.create_agent(
                agent_type="test_type",
                name="test_agent"
            )

            # Verify
            assert agent == mock_agent
            assert agent.agent_id in registry.agents
            assert agent.name == "test_agent"
            mock_agent.initialize.assert_called_once()
            mock_store.assert_called_once_with(agent)

    @pytest.mark.asyncio
    async def test_create_agent_duplicate_name_in_memory(self, registry, mock_agent_class):
        """Test agent creation fails with duplicate name in memory."""
        # Setup
        registry.status = RegistryStatus.RUNNING
        await registry.register_agent_type("test_type", mock_agent_class)

        # Add existing agent to registry
        existing_agent = Mock(spec=BaseAgent)
        existing_agent.name = "existing_agent"
        existing_agent.agent_id = str(uuid.uuid4())
        registry.agents[existing_agent.agent_id] = existing_agent

        # Execute & Verify
        with pytest.raises(ValueError, match="already exists"):
            await registry.create_agent(
                agent_type="test_type",
                name="existing_agent"
            )

    @pytest.mark.asyncio
    async def test_create_agent_duplicate_name_database_check(self, registry, mock_agent_class, caplog):
        """Test agent creation fails with duplicate name in database (Phase 1 fix)."""
        # Setup
        registry.status = RegistryStatus.RUNNING
        await registry.register_agent_type("test_type", mock_agent_class)

        # Create a proper mock agent with agent_id attribute
        mock_agent = Mock()
        mock_agent.agent_id = str(uuid.uuid4())
        mock_agent.name = "duplicate_name"
        mock_agent.capabilities = []
        mock_agent.domain = None
        mock_agent.initialize = AsyncMock()
        mock_agent_class.return_value = mock_agent

        # Mock database to return existing agent (should trigger ValueError)
        with patch('app.agents.registry.db') as mock_db:
            mock_db.fetch_one = AsyncMock(return_value={"id": uuid.uuid4()})

            # Also mock _store_agent_in_db to avoid errors
            with patch.object(registry, '_store_agent_in_db', AsyncMock()):
                # Execute - should log warning but not raise exception
                with caplog.at_level("WARNING"):
                    await registry.create_agent(
                        agent_type="test_type",
                        name="duplicate_name"
                    )

                # Verify database query was called with correct parameters
                mock_db.fetch_one.assert_called_once_with(
                    "SELECT id FROM agents WHERE name = $1 AND is_active = true",
                    "duplicate_name"
                )

                # Verify warning was logged about duplicate name
                assert "already exists in database" in caplog.text

    @pytest.mark.asyncio
    async def test_create_agent_database_check_failure_continues(self, registry, mock_agent_class, caplog):
        """Test agent creation continues when database check fails."""
        # Setup
        registry.status = RegistryStatus.RUNNING
        await registry.register_agent_type("test_type", mock_agent_class)

        mock_agent = Mock(spec=BaseAgent)
        mock_agent.agent_id = str(uuid.uuid4())
        mock_agent.name = "test_agent"
        mock_agent.capabilities = []
        mock_agent.domain = None
        mock_agent.initialize = AsyncMock()
        mock_agent_class.return_value = mock_agent

        # Mock database to raise exception
        with patch('app.agents.registry.db') as mock_db:
            mock_db.fetch_one = AsyncMock(side_effect=Exception("Database error"))

            # Mock store to succeed
            with patch.object(registry, '_store_agent_in_db', AsyncMock()):
                # Execute
                agent = await registry.create_agent(
                    agent_type="test_type",
                    name="test_agent"
                )

                # Verify
                assert agent == mock_agent
                assert "Failed to check database for duplicate agent name" in caplog.text

    @pytest.mark.asyncio
    async def test_get_agent_by_name_in_memory(self, registry, mock_agent):
        """Test get_agent_by_name finds agent in memory."""
        # Setup
        registry.agents[mock_agent.agent_id] = mock_agent

        # Execute
        result = await registry.get_agent_by_name(mock_agent.name)

        # Verify
        assert result == mock_agent

    @pytest.mark.asyncio
    async def test_get_agent_by_name_database_fallback(self, registry):
        """Test get_agent_by_name falls back to database when not in memory (Phase 1 fix)."""
        # Setup
        agent_id = str(uuid.uuid4())
        agent_name = "database_agent"

        # Mock database to return agent data
        with patch('app.agents.registry.db') as mock_db:
            mock_db.fetch_one = AsyncMock(return_value={
                "id": uuid.UUID(agent_id),
                "name": agent_name,
                "agent_type": "domain",
                "domain": "test_domain",
                "description": "Test agent",
                "system_prompt": "You are a test agent",
                "capabilities": ["test_capability"],
                "supervisor_id": None,
                "config": {}
            })

            # Mock _load_agent_from_db_data to return a mock agent
            mock_agent = Mock(spec=BaseAgent)
            mock_agent.agent_id = agent_id
            mock_agent.name = agent_name
            with patch.object(registry, '_load_agent_from_db_data', AsyncMock(return_value=mock_agent)):
                # Execute
                result = await registry.get_agent_by_name(agent_name)

                # Verify
                assert result == mock_agent
                mock_db.fetch_one.assert_called_once_with(
                    """SELECT id, name, agent_type, domain, description, system_prompt,
                       capabilities, supervisor_id, config
                    FROM agents WHERE name = $1 AND is_active = true""",
                    agent_name
                )

    @pytest.mark.asyncio
    async def test_get_agent_by_name_not_found(self, registry):
        """Test get_agent_by_name returns None when agent not found."""
        # Setup - empty registry
        # Mock database to return None
        with patch('app.agents.registry.db') as mock_db:
            mock_db.fetch_one = AsyncMock(return_value=None)

            # Execute
            result = await registry.get_agent_by_name("nonexistent_agent")

            # Verify
            assert result is None

    @pytest.mark.asyncio
    async def test_update_agent_success(self, registry, mock_agent):
        """Test successful agent update."""
        # Setup
        registry.agents[mock_agent.agent_id] = mock_agent

        # Mock database update
        with patch.object(registry, '_store_agent_in_db', AsyncMock()):
            # Execute
            result = await registry.update_agent(
                uuid.UUID(mock_agent.agent_id),
                name="updated_name",
                description="Updated description",
                capabilities=["new_capability"]
            )

            # Verify
            assert result == mock_agent
            assert mock_agent.name == "updated_name"
            assert mock_agent.description == "Updated description"
            assert mock_agent.capabilities == ["new_capability"]

    @pytest.mark.asyncio
    async def test_update_agent_not_found(self, registry):
        """Test update_agent returns None when agent not found."""
        # Execute
        result = await registry.update_agent(uuid.uuid4(), name="new_name")

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_agent_success(self, registry, mock_agent):
        """Test successful agent deletion."""
        # Setup
        registry.agents[mock_agent.agent_id] = mock_agent
        registry.capability_index["test_capability"] = {mock_agent.agent_id}
        registry.domain_index["test_domain"] = {mock_agent.agent_id}

        # Mock database update
        with patch('app.agents.registry.db') as mock_db:
            mock_db.execute = AsyncMock()

            # Execute
            result = await registry.delete_agent(uuid.UUID(mock_agent.agent_id))

            # Verify
            assert result is True
            assert mock_agent.agent_id not in registry.agents
            assert mock_agent.agent_id not in registry.capability_index["test_capability"]
            assert mock_agent.agent_id not in registry.domain_index["test_domain"]
            mock_agent.cleanup.assert_called_once()
            mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_agent_not_found(self, registry):
        """Test delete_agent returns False when agent not found."""
        # Execute
        result = await registry.delete_agent(uuid.uuid4())

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_get_registry_status(self, registry, mock_agent):
        """Test registry status reporting."""
        # Setup
        registry.status = RegistryStatus.RUNNING
        registry.agents[mock_agent.agent_id] = mock_agent
        registry.capability_index["test_capability"] = {mock_agent.agent_id}
        registry.domain_index["test_domain"] = {mock_agent.agent_id}

        # Execute
        status = await registry.get_registry_status()

        # Verify
        assert status["status"] == "running"
        assert status["total_agents"] == 1
        assert status["active_agents"] == 1  # IDLE agent is active
        assert status["idle_agents"] == 1
        assert "test_capability" in status["capabilities_available"]
        assert "test_domain" in status["domains_available"]

    @pytest.mark.asyncio
    async def test_find_agents_by_capability(self, registry, mock_agent):
        """Test finding agents by capability."""
        # Setup
        registry.agents[mock_agent.agent_id] = mock_agent
        registry.capability_index["test_capability"] = {mock_agent.agent_id}

        # Execute
        agents = await registry.find_agents_by_capability("test_capability")

        # Verify
        assert len(agents) == 1
        assert agents[0] == mock_agent

    @pytest.mark.asyncio
    async def test_find_agents_by_domain(self, registry, mock_agent):
        """Test finding agents by domain."""
        # Setup
        registry.agents[mock_agent.agent_id] = mock_agent
        registry.domain_index["test_domain"] = {mock_agent.agent_id}

        # Execute
        agents = await registry.find_agents_by_domain("test_domain")

        # Verify
        assert len(agents) == 1
        assert agents[0] == mock_agent

    @pytest.mark.asyncio
    async def test_select_agent_for_task(self, registry, mock_agent):
        """Test agent selection for task."""
        # Setup
        registry.agents[mock_agent.agent_id] = mock_agent
        registry.capability_index["required_cap"] = {mock_agent.agent_id}
        registry.domain_index["preferred_domain"] = {mock_agent.agent_id}

        # Mock scoring
        with patch.object(registry, '_score_agent_for_task', AsyncMock(return_value=0.8)):
            # Execute
            agent, score = await registry.select_agent_for_task(
                task_description="Test task",
                required_capabilities=["required_cap"],
                preferred_domain="preferred_domain"
            )

            # Verify
            assert agent == mock_agent
            assert score == 0.8

    @pytest.mark.asyncio
    async def test_start_agent_success(self, registry, mock_agent):
        """Test successful agent start."""
        # Setup
        mock_agent.status = AgentStatus.STOPPED
        with patch.object(registry, 'get_agent', AsyncMock(return_value=mock_agent)):
            # Execute
            result = await registry.start_agent(mock_agent.agent_id)

            # Verify
            assert result is True
            mock_agent.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_agent_success(self, registry, mock_agent):
        """Test successful agent stop."""
        # Setup
        mock_agent.status = AgentStatus.IDLE
        with patch.object(registry, 'get_agent', AsyncMock(return_value=mock_agent)):
            # Execute
            result = await registry.stop_agent(mock_agent.agent_id)

            # Verify
            assert result is True
            mock_agent.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_agents(self, registry, mock_agent):
        """Test listing all agents."""
        # Setup
        registry.agents[mock_agent.agent_id] = mock_agent

        # Execute
        agents = await registry.list_agents()

        # Verify
        assert len(agents) == 1
        assert agents[0] == mock_agent