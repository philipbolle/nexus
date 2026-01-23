"""
Unit tests for SwarmPubSub class.

Tests Redis Pub/Sub wrapper functionality for the simplified swarm communication layer.
Only tests ENABLED components in the simplified swarm architecture.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime

from app.agents.swarm.pubsub import SwarmPubSub


class TestSwarmPubSub:
    """Test suite for SwarmPubSub class."""

    @pytest.fixture
    def swarm_pubsub(self):
        """Create a fresh SwarmPubSub instance for each test."""
        return SwarmPubSub()

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client."""
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock()
        mock_client.pubsub = Mock()
        return mock_client

    @pytest.fixture
    def mock_pubsub(self):
        """Create a mock PubSub client."""
        mock_pubsub = AsyncMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.psubscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.punsubscribe = AsyncMock()
        mock_pubsub.get_message = AsyncMock()
        mock_pubsub.close = AsyncMock()
        return mock_pubsub

    @pytest.mark.asyncio
    async def test_initial_state(self, swarm_pubsub):
        """Test initial state of SwarmPubSub."""
        assert swarm_pubsub.redis_client is None
        assert swarm_pubsub.pubsub is None
        assert swarm_pubsub.subscribed_channels == set()
        assert swarm_pubsub.subscribed_patterns == set()
        assert swarm_pubsub._running is False
        assert swarm_pubsub._listener_task is None
        assert swarm_pubsub._message_queue is None

    @pytest.mark.asyncio
    async def test_initialize_success(self, swarm_pubsub, mock_redis_client, mock_pubsub):
        """Test successful initialization."""
        # Setup mocks
        with patch('app.agents.swarm.pubsub.redis.from_url', AsyncMock(return_value=mock_redis_client)):
            mock_redis_client.pubsub.return_value = mock_pubsub

            # Execute
            await swarm_pubsub.initialize()

            # Verify
            assert swarm_pubsub.redis_client == mock_redis_client
            assert swarm_pubsub.pubsub == mock_pubsub
            assert swarm_pubsub._message_queue is not None
            assert swarm_pubsub._running is True
            mock_redis_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, swarm_pubsub, mock_redis_client, mock_pubsub):
        """Test initialization when already initialized."""
        # Setup - initialize first
        with patch('app.agents.swarm.pubsub.redis.from_url', AsyncMock(return_value=mock_redis_client)):
            mock_redis_client.pubsub.return_value = mock_pubsub
            await swarm_pubsub.initialize()

        # Execute again
        await swarm_pubsub.initialize()

        # Verify - should not recreate connections
        assert swarm_pubsub._running is True

    @pytest.mark.asyncio
    async def test_initialize_connection_failure(self, swarm_pubsub):
        """Test initialization with connection failure."""
        # Setup mock to raise exception
        with patch('app.agents.swarm.pubsub.redis.from_url', AsyncMock(side_effect=Exception("Connection failed"))):
            # Execute & Verify
            with pytest.raises(Exception, match="Connection failed"):
                await swarm_pubsub.initialize()

            # Verify cleanup was called
            assert swarm_pubsub.redis_client is None
            assert swarm_pubsub.pubsub is None
            assert swarm_pubsub._running is False

    @pytest.mark.asyncio
    async def test_close(self, swarm_pubsub, mock_redis_client, mock_pubsub):
        """Test closing the Pub/Sub connection."""
        # Setup - initialize first
        with patch('app.agents.swarm.pubsub.redis.from_url', AsyncMock(return_value=mock_redis_client)):
            mock_redis_client.pubsub.return_value = mock_pubsub
            await swarm_pubsub.initialize()

        # Create a mock listener task
        mock_task = AsyncMock()
        swarm_pubsub._listener_task = mock_task

        # Execute
        await swarm_pubsub.close()

        # Verify
        assert swarm_pubsub._running is False
        mock_task.cancel.assert_called_once()
        mock_pubsub.close.assert_called_once()
        mock_redis_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_message(self, swarm_pubsub, mock_redis_client):
        """Test publishing a message to a channel."""
        # Setup - initialize with mock
        with patch('app.agents.swarm.pubsub.redis.from_url', AsyncMock(return_value=mock_redis_client)):
            await swarm_pubsub.initialize()

        channel = "test_channel"
        message = {"type": "test", "data": "test data"}
        expected_serialized = json.dumps(message)

        # Execute
        await swarm_pubsub.publish(channel, message)

        # Verify
        mock_redis_client.publish.assert_called_once_with(channel, expected_serialized)

    @pytest.mark.asyncio
    async def test_publish_message_not_initialized(self, swarm_pubsub):
        """Test publishing when not initialized."""
        # Execute & Verify
        with pytest.raises(RuntimeError, match="SwarmPubSub not initialized"):
            await swarm_pubsub.publish("test_channel", {"test": "data"})

    @pytest.mark.asyncio
    async def test_subscribe_channel(self, swarm_pubsub, mock_redis_client, mock_pubsub):
        """Test subscribing to a channel."""
        # Setup - initialize with mock
        with patch('app.agents.swarm.pubsub.redis.from_url', AsyncMock(return_value=mock_redis_client)):
            mock_redis_client.pubsub.return_value = mock_pubsub
            await swarm_pubsub.initialize()

        channel = "test_channel"

        # Execute
        await swarm_pubsub.subscribe(channel)

        # Verify
        mock_pubsub.subscribe.assert_called_once_with(channel)
        assert channel in swarm_pubsub.subscribed_channels

    @pytest.mark.asyncio
    async def test_subscribe_pattern(self, swarm_pubsub, mock_redis_client, mock_pubsub):
        """Test subscribing to a pattern."""
        # Setup - initialize with mock
        with patch('app.agents.swarm.pubsub.redis.from_url', AsyncMock(return_value=mock_redis_client)):
            mock_redis_client.pubsub.return_value = mock_pubsub
            await swarm_pubsub.initialize()

        pattern = "test.*"

        # Execute
        await swarm_pubsub.psubscribe(pattern)

        # Verify
        mock_pubsub.psubscribe.assert_called_once_with(pattern)
        assert pattern in swarm_pubsub.subscribed_patterns

    @pytest.mark.asyncio
    async def test_unsubscribe_channel(self, swarm_pubsub, mock_redis_client, mock_pubsub):
        """Test unsubscribing from a channel."""
        # Setup - initialize and subscribe
        with patch('app.agents.swarm.pubsub.redis.from_url', AsyncMock(return_value=mock_redis_client)):
            mock_redis_client.pubsub.return_value = mock_pubsub
            await swarm_pubsub.initialize()

        channel = "test_channel"
        await swarm_pubsub.subscribe(channel)

        # Execute
        await swarm_pubsub.unsubscribe(channel)

        # Verify
        mock_pubsub.unsubscribe.assert_called_once_with(channel)
        assert channel not in swarm_pubsub.subscribed_channels

    @pytest.mark.asyncio
    async def test_unsubscribe_pattern(self, swarm_pubsub, mock_redis_client, mock_pubsub):
        """Test unsubscribing from a pattern."""
        # Setup - initialize and subscribe
        with patch('app.agents.swarm.pubsub.redis.from_url', AsyncMock(return_value=mock_redis_client)):
            mock_redis_client.pubsub.return_value = mock_pubsub
            await swarm_pubsub.initialize()

        pattern = "test.*"
        await swarm_pubsub.psubscribe(pattern)

        # Execute
        await swarm_pubsub.punsubscribe(pattern)

        # Verify
        mock_pubsub.punsubscribe.assert_called_once_with(pattern)
        assert pattern not in swarm_pubsub.subscribed_patterns

    @pytest.mark.asyncio
    async def test_listen_for_messages(self, swarm_pubsub, mock_redis_client, mock_pubsub):
        """Test listening for messages."""
        # Setup - initialize with mock
        with patch('app.agents.swarm.pubsub.redis.from_url', AsyncMock(return_value=mock_redis_client)):
            mock_redis_client.pubsub.return_value = mock_pubsub
            await swarm_pubsub.initialize()

        # Setup mock message
        test_message = {
            "type": "message",
            "channel": b"test_channel",
            "data": json.dumps({"type": "test", "data": "test data"}).encode()
        }
        mock_pubsub.get_message.side_effect = [test_message, None]  # Return message then None to stop

        # Execute listener (will stop after second call returns None)
        await swarm_pubsub._listen_for_messages()

        # Verify message was processed and added to queue
        assert not swarm_pubsub._message_queue.empty()
        queued_message = await swarm_pubsub._message_queue.get()
        assert queued_message["channel"] == "test_channel"
        assert queued_message["data"]["type"] == "test"

    @pytest.mark.asyncio
    async def test_get_message(self, swarm_pubsub, mock_redis_client, mock_pubsub):
        """Test getting a message from the queue."""
        # Setup - initialize
        with patch('app.agents.swarm.pubsub.redis.from_url', AsyncMock(return_value=mock_redis_client)):
            mock_redis_client.pubsub.return_value = mock_pubsub
            await swarm_pubsub.initialize()

        # Add a test message to the queue
        test_message = {
            "channel": "test_channel",
            "data": {"type": "test", "data": "test data"},
            "timestamp": datetime.now().isoformat()
        }
        await swarm_pubsub._message_queue.put(test_message)

        # Execute
        message = await swarm_pubsub.get_message(timeout=1.0)

        # Verify
        assert message == test_message

    @pytest.mark.asyncio
    async def test_get_message_timeout(self, swarm_pubsub, mock_redis_client, mock_pubsub):
        """Test getting a message with timeout."""
        # Setup - initialize
        with patch('app.agents.swarm.pubsub.redis.from_url', AsyncMock(return_value=mock_redis_client)):
            mock_redis_client.pubsub.return_value = mock_pubsub
            await swarm_pubsub.initialize()

        # Execute with empty queue and short timeout
        message = await swarm_pubsub.get_message(timeout=0.1)

        # Verify
        assert message is None

    @pytest.mark.asyncio
    async def test_get_messages_generator(self, swarm_pubsub, mock_redis_client, mock_pubsub):
        """Test getting messages as async generator."""
        # Setup - initialize
        with patch('app.agents.swarm.pubsub.redis.from_url', AsyncMock(return_value=mock_redis_client)):
            mock_redis_client.pubsub.return_value = mock_pubsub
            await swarm_pubsub.initialize()

        # Add test messages to queue
        test_messages = [
            {"channel": "test1", "data": {"id": 1}},
            {"channel": "test2", "data": {"id": 2}},
            {"channel": "test3", "data": {"id": 3}},
        ]
        for msg in test_messages:
            await swarm_pubsub._message_queue.put(msg)

        # Stop after 3 messages
        swarm_pubsub._message_queue.put_nowait(None)

        # Execute - collect messages from generator
        messages = []
        async for message in swarm_pubsub.get_messages():
            if message is None:
                break
            messages.append(message)

        # Verify
        assert len(messages) == 3
        assert messages[0]["channel"] == "test1"
        assert messages[1]["channel"] == "test2"
        assert messages[2]["channel"] == "test3"

    @pytest.mark.asyncio
    async def test_persist_message(self, swarm_pubsub, mock_redis_client):
        """Test persisting a message to database."""
        # Setup - initialize
        with patch('app.agents.swarm.pubsub.redis.from_url', AsyncMock(return_value=mock_redis_client)):
            await swarm_pubsub.initialize()

        channel = "test_channel"
        message = {"type": "test", "sender": "agent1", "data": "test data"}

        # Mock database call
        with patch('app.agents.swarm.pubsub.db') as mock_db:
            mock_db.execute = AsyncMock()

            # Execute
            await swarm_pubsub.publish(channel, message, persist=True)

            # Verify
            mock_redis_client.publish.assert_called_once()
            mock_db.execute.assert_called_once()
            # Check that insert query includes message data
            call_args = mock_db.execute.call_args[0][0]
            assert "INSERT INTO swarm_messages" in call_args

    @pytest.mark.asyncio
    async def test_get_channel_stats(self, swarm_pubsub, mock_redis_client):
        """Test getting channel statistics."""
        # Setup - initialize
        with patch('app.agents.swarm.pubsub.redis.from_url', AsyncMock(return_value=mock_redis_client)):
            await swarm_pubsub.initialize()

        channel = "test_channel"
        mock_redis_client.pubsub_numsub = AsyncMock(return_value=[(channel.encode(), 5)])

        # Execute
        stats = await swarm_pubsub.get_channel_stats(channel)

        # Verify
        assert "subscribers" in stats
        assert stats["subscribers"] == 5
        mock_redis_client.pubsub_numsub.assert_called_once_with(channel)

    @pytest.mark.asyncio
    async def test_reconnect_on_failure(self, swarm_pubsub, mock_redis_client, mock_pubsub):
        """Test reconnection on Redis failure."""
        # Setup - initialize
        with patch('app.agents.swarm.pubsub.redis.from_url', AsyncMock(return_value=mock_redis_client)):
            mock_redis_client.pubsub.return_value = mock_pubsub
            await swarm_pubsub.initialize()

        # Simulate connection failure during publish
        mock_redis_client.publish.side_effect = [Exception("Redis connection lost"), None]

        # Mock reconnection
        with patch.object(swarm_pubsub, 'initialize', AsyncMock()) as mock_reconnect:
            # Execute publish (should trigger reconnection)
            await swarm_pubsub.publish("test_channel", {"test": "data"})

            # Verify reconnection was attempted
            mock_reconnect.assert_called_once()
            # Verify publish was retried
            assert mock_redis_client.publish.call_count == 2