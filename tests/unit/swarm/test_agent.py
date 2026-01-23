"""
Unit tests for SwarmAgent class.

Tests swarm agent functionality for the simplified swarm communication layer.
Only tests ENABLED components in the simplified swarm architecture.
"""

import pytest
import uuid
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from app.agents.swarm.agent import SwarmAgent, create_swarm_agent
from app.agents.base import AgentType, AgentStatus


class TestSwarmAgent:
    """Test suite for SwarmAgent class."""

    @pytest.fixture
    def swarm_agent(self):
        """Create a SwarmAgent instance for testing."""
        return SwarmAgent(
            name="test_swarm_agent",
            agent_type=AgentType.DOMAIN,
            swarm_id="test_swarm",
            swarm_role="worker"
        )

    @pytest.fixture
    def mock_pubsub(self):
        """Create a mock PubSub instance."""
        mock_pubsub = AsyncMock()
        mock_pubsub.initialize = AsyncMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.publish = AsyncMock()
        mock_pubsub.get_message = AsyncMock()
        mock_pubsub.close = AsyncMock()
        return mock_pubsub

    @pytest.mark.asyncio
    async def test_initial_state(self, swarm_agent):
        """Test initial state of SwarmAgent."""
        assert swarm_agent.name == "test_swarm_agent"
        assert swarm_agent.agent_type == AgentType.DOMAIN
        assert swarm_agent.swarm_id == "test_swarm"
        assert swarm_agent.swarm_role == "worker"
        assert swarm_agent.status == AgentStatus.CREATED
        assert swarm_agent.swarm_channels == set()

    @pytest.mark.asyncio
    async def test_initialize_success(self, swarm_agent, mock_pubsub):
        """Test successful initialization."""
        # Setup mocks
        with patch('app.agents.swarm.agent.swarm_pubsub', mock_pubsub):
            # Execute
            await swarm_agent.initialize()

            # Verify
            assert swarm_agent.status == AgentStatus.IDLE
            mock_pubsub.initialize.assert_called_once()
            # Should subscribe to swarm channel
            expected_channel = f"swarm:{swarm_agent.swarm_id}"
            mock_pubsub.subscribe.assert_called_once_with(expected_channel)
            assert expected_channel in swarm_agent.swarm_channels

    @pytest.mark.asyncio
    async def test_initialize_without_swarm_id(self):
        """Test initialization without swarm_id."""
        # Create agent without swarm_id
        agent = SwarmAgent(name="test_agent", agent_type=AgentType.DOMAIN)

        # Execute
        await agent.initialize()

        # Verify - should still initialize but not subscribe to swarm channel
        assert agent.status == AgentStatus.IDLE
        assert agent.swarm_id is None
        assert len(agent.swarm_channels) == 0

    @pytest.mark.asyncio
    async def test_join_swarm(self, swarm_agent, mock_pubsub):
        """Test joining a swarm."""
        # Setup - initialize first
        with patch('app.agents.swarm.agent.swarm_pubsub', mock_pubsub):
            await swarm_agent.initialize()

        new_swarm_id = "new_swarm"

        # Execute
        await swarm_agent.join_swarm(new_swarm_id)

        # Verify
        assert swarm_agent.swarm_id == new_swarm_id
        expected_channel = f"swarm:{new_swarm_id}"
        mock_pubsub.subscribe.assert_called_with(expected_channel)
        assert expected_channel in swarm_agent.swarm_channels

    @pytest.mark.asyncio
    async def test_leave_swarm(self, swarm_agent, mock_pubsub):
        """Test leaving a swarm."""
        # Setup - initialize and join swarm
        with patch('app.agents.swarm.agent.swarm_pubsub', mock_pubsub):
            await swarm_agent.initialize()
            await swarm_agent.join_swarm("test_swarm")

        # Execute
        await swarm_agent.leave_swarm()

        # Verify
        assert swarm_agent.swarm_id is None
        # Should unsubscribe from swarm channel
        mock_pubsub.unsubscribe.assert_called()
        assert len(swarm_agent.swarm_channels) == 0

    @pytest.mark.asyncio
    async def test_send_swarm_message(self, swarm_agent, mock_pubsub):
        """Test sending a message to swarm."""
        # Setup - initialize
        with patch('app.agents.swarm.agent.swarm_pubsub', mock_pubsub):
            await swarm_agent.initialize()

        message_type = "task_assignment"
        message_data = {"task_id": "123", "description": "Test task"}
        metadata = {"priority": "high"}

        # Execute
        await swarm_agent.send_swarm_message(
            message_type=message_type,
            data=message_data,
            metadata=metadata
        )

        # Verify
        mock_pubsub.publish.assert_called_once()
        call_args = mock_pubsub.publish.call_args
        channel = call_args[0][0]
        message = call_args[0][1]

        assert channel == f"swarm:{swarm_agent.swarm_id}"
        assert message["type"] == message_type
        assert message["data"] == message_data
        assert message["metadata"] == metadata
        assert message["sender"] == swarm_agent.agent_id
        assert message["timestamp"] is not None

    @pytest.mark.asyncio
    async def test_send_swarm_message_no_swarm(self, swarm_agent, mock_pubsub):
        """Test sending message when not in a swarm."""
        # Setup - initialize without swarm
        swarm_agent.swarm_id = None
        with patch('app.agents.swarm.agent.swarm_pubsub', mock_pubsub):
            await swarm_agent.initialize()

        # Execute & Verify
        with pytest.raises(RuntimeError, match="Not a member of any swarm"):
            await swarm_agent.send_swarm_message("test", {})

    @pytest.mark.asyncio
    async def test_receive_swarm_message(self, swarm_agent, mock_pubsub):
        """Test receiving a swarm message."""
        # Setup - initialize
        with patch('app.agents.swarm.agent.swarm_pubsub', mock_pubsub):
            await swarm_agent.initialize()

        # Mock incoming message
        test_message = {
            "channel": f"swarm:{swarm_agent.swarm_id}",
            "data": {
                "type": "task_assignment",
                "data": {"task_id": "123"},
                "sender": "other_agent",
                "timestamp": "2024-01-01T00:00:00"
            }
        }
        mock_pubsub.get_message.return_value = test_message

        # Execute
        message = await swarm_agent.receive_swarm_message(timeout=1.0)

        # Verify
        assert message is not None
        assert message["type"] == "task_assignment"
        assert message["data"]["task_id"] == "123"
        assert message["sender"] == "other_agent"

    @pytest.mark.asyncio
    async def test_process_swarm_message(self, swarm_agent, mock_pubsub):
        """Test processing a swarm message."""
        # Setup - initialize
        with patch('app.agents.swarm.agent.swarm_pubsub', mock_pubsub):
            await swarm_agent.initialize()

        test_message = {
            "type": "task_assignment",
            "data": {"task_id": "123", "description": "Test task"},
            "sender": "coordinator",
            "timestamp": "2024-01-01T00:00:00"
        }

        # Mock message handler
        mock_handler = AsyncMock()
        swarm_agent.register_message_handler("task_assignment", mock_handler)

        # Execute
        await swarm_agent._process_swarm_message(test_message)

        # Verify
        mock_handler.assert_called_once_with(test_message)

    @pytest.mark.asyncio
    async def test_register_message_handler(self, swarm_agent):
        """Test registering a message handler."""
        message_type = "task_assignment"
        handler = AsyncMock()

        # Execute
        swarm_agent.register_message_handler(message_type, handler)

        # Verify
        assert message_type in swarm_agent._message_handlers
        assert swarm_agent._message_handlers[message_type] == handler

    @pytest.mark.asyncio
    async def test_unregister_message_handler(self, swarm_agent):
        """Test unregistering a message handler."""
        message_type = "task_assignment"
        handler = AsyncMock()

        # Register then unregister
        swarm_agent.register_message_handler(message_type, handler)
        swarm_agent.unregister_message_handler(message_type)

        # Verify
        assert message_type not in swarm_agent._message_handlers

    @pytest.mark.asyncio
    async def test_start_message_listener(self, swarm_agent, mock_pubsub):
        """Test starting message listener."""
        # Setup - initialize
        with patch('app.agents.swarm.agent.swarm_pubsub', mock_pubsub):
            await swarm_agent.initialize()

        # Mock message reception
        test_message = {
            "channel": f"swarm:{swarm_agent.swarm_id}",
            "data": {
                "type": "test_message",
                "data": {},
                "sender": "test",
                "timestamp": "2024-01-01T00:00:00"
            }
        }
        mock_pubsub.get_message.side_effect = [test_message, None]  # Stop after first message

        # Mock message handler
        mock_handler = AsyncMock()
        swarm_agent.register_message_handler("test_message", mock_handler)

        # Execute listener (will stop after None)
        await swarm_agent._listen_for_messages()

        # Verify
        mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_status(self, swarm_agent, mock_pubsub):
        """Test broadcasting agent status to swarm."""
        # Setup - initialize
        with patch('app.agents.swarm.agent.swarm_pubsub', mock_pubsub):
            await swarm_agent.initialize()

        # Execute
        await swarm_agent.broadcast_status()

        # Verify
        mock_pubsub.publish.assert_called_once()
        message = mock_pubsub.publish.call_args[0][1]
        assert message["type"] == "agent_status"
        assert message["data"]["agent_id"] == swarm_agent.agent_id
        assert message["data"]["status"] == swarm_agent.status.value
        assert "metrics" in message["data"]

    @pytest.mark.asyncio
    async def test_handle_task_assignment(self, swarm_agent):
        """Test handling task assignment message."""
        # Setup
        task_message = {
            "type": "task_assignment",
            "data": {
                "task_id": "123",
                "description": "Test task",
                "parameters": {"param1": "value1"}
            },
            "sender": "coordinator",
            "timestamp": "2024-01-01T00:00:00"
        }

        # Mock task execution
        mock_execute = AsyncMock(return_value={"result": "success"})
        swarm_agent.execute = mock_execute

        # Execute
        await swarm_agent._handle_task_assignment(task_message)

        # Verify
        mock_execute.assert_called_once_with(
            task_description="Test task",
            parameters={"param1": "value1"}
        )

    @pytest.mark.asyncio
    async def test_coordinate_with_other_agents(self, swarm_agent, mock_pubsub):
        """Test coordinating with other agents in swarm."""
        # Setup - initialize
        with patch('app.agents.swarm.agent.swarm_pubsub', mock_pubsub):
            await swarm_agent.initialize()

        target_agent_id = "other_agent"
        coordination_type = "resource_request"
        coordination_data = {"resource": "cpu", "amount": 50}

        # Execute
        await swarm_agent.coordinate_with_agent(
            target_agent_id=target_agent_id,
            coordination_type=coordination_type,
            data=coordination_data
        )

        # Verify
        mock_pubsub.publish.assert_called_once()
        message = mock_pubsub.publish.call_args[0][1]
        assert message["type"] == "agent_coordination"
        assert message["data"]["target_agent_id"] == target_agent_id
        assert message["data"]["coordination_type"] == coordination_type
        assert message["data"]["data"] == coordination_data

    @pytest.mark.asyncio
    async def test_cleanup(self, swarm_agent, mock_pubsub):
        """Test cleanup of swarm agent."""
        # Setup - initialize and join swarm
        with patch('app.agents.swarm.agent.swarm_pubsub', mock_pubsub):
            await swarm_agent.initialize()
            await swarm_agent.join_swarm("test_swarm")

        # Execute
        await swarm_agent.cleanup()

        # Verify
        assert swarm_agent.status == AgentStatus.STOPPED
        # Should unsubscribe from all channels
        mock_pubsub.unsubscribe.assert_called()
        assert len(swarm_agent.swarm_channels) == 0

    @pytest.mark.asyncio
    async def test_create_swarm_agent_helper(self):
        """Test create_swarm_agent helper function."""
        # Setup mocks
        mock_registry = AsyncMock()
        mock_agent = AsyncMock()
        mock_registry.create_agent.return_value = mock_agent

        # Execute
        agent = await create_swarm_agent(
            registry=mock_registry,
            name="test_swarm_agent",
            swarm_id="test_swarm",
            swarm_role="worker"
        )

        # Verify
        assert agent == mock_agent
        mock_registry.create_agent.assert_called_once_with(
            agent_type="worker",  # SwarmAgent type for worker role
            name="test_swarm_agent",
            swarm_id="test_swarm",
            swarm_role="worker"
        )

    @pytest.mark.asyncio
    async def test_swarm_agent_metrics(self, swarm_agent, mock_pubsub):
        """Test swarm agent metrics collection."""
        # Setup - initialize
        with patch('app.agents.swarm.agent.swarm_pubsub', mock_pubsub):
            await swarm_agent.initialize()

        # Send some messages to generate metrics
        await swarm_agent.send_swarm_message("test", {"data": "test"})
        await swarm_agent.send_swarm_message("test", {"data": "test2"})

        # Check metrics
        metrics = swarm_agent.metrics
        assert "messages_sent" in metrics
        assert metrics["messages_sent"] == 2
        assert "swarm_id" in metrics
        assert metrics["swarm_id"] == swarm_agent.swarm_id