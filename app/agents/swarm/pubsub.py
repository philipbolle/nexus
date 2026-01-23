"""
NEXUS Swarm Communication Layer - Redis Pub/Sub Wrapper

Real-time messaging between agents for coordination using Redis Pub/Sub.
Provides asynchronous publish/subscribe with channel management and reconnection.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, AsyncGenerator
import uuid
from datetime import datetime

import redis.asyncio as redis
from app.config import settings

logger = logging.getLogger(__name__)


class SwarmPubSub:
    """
    Redis Pub/Sub wrapper for swarm communication.

    Features:
    - Channel-based publish/subscribe
    - Pattern subscriptions (glob patterns)
    - Automatic reconnection on failure
    - Message persistence to database (optional)
    - Connection pooling with existing Redis client
    """

    def __init__(self):
        """Initialize the Pub/Sub wrapper."""
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.subscribed_channels: set = set()
        self.subscribed_patterns: set = set()
        self._running = False
        self._listener_task: Optional[asyncio.Task] = None
        self._message_queue: Optional[asyncio.Queue] = None
        self._reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay_seconds = 1

    async def initialize(self) -> None:
        """
        Initialize Redis connection and Pub/Sub client.

        Reuses existing Redis connection pool if available from cache service,
        otherwise creates new connection.
        """
        # If already fully initialized, just return
        if self.redis_client and self.pubsub and self._message_queue is not None:
            logger.debug("SwarmPubSub already initialized")
            return

        try:
            # Create Redis connection if needed
            if not self.redis_client:
                self.redis_client = await redis.from_url(
                    settings.redis_url,
                    decode_responses=False,  # We'll handle serialization ourselves
                    max_connections=20,
                    socket_keepalive=True,
                    retry_on_timeout=True
                )
                logger.debug("Created new Redis connection")

            # Create PubSub client if needed
            if not self.pubsub and self.redis_client:
                self.pubsub = self.redis_client.pubsub()
                logger.debug("Created PubSub client")

            # Test connection if we have Redis client
            if self.redis_client:
                await self.redis_client.ping()
                logger.debug("Redis connection test successful")

            # Initialize message queue if needed
            if self._message_queue is None:
                self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
                logger.debug("Initialized message queue")

            self._running = True
            self._reconnect_attempts = 0

            logger.info("SwarmPubSub initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize SwarmPubSub: {e}")
            await self._cleanup()
            raise

    async def close(self) -> None:
        """Close Redis connection and cleanup."""
        self._running = False

        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

        await self._cleanup()
        logger.info("SwarmPubSub closed")

    async def _cleanup(self) -> None:
        """Clean up Redis connections."""
        if self.pubsub:
            try:
                await self.pubsub.close()
            except Exception as e:
                logger.debug(f"Error closing pubsub: {e}")
            self.pubsub = None

        if self.redis_client:
            try:
                await self.redis_client.close()
            except Exception as e:
                logger.debug(f"Error closing Redis client: {e}")
            self.redis_client = None

        self.subscribed_channels.clear()
        self.subscribed_patterns.clear()
        self._message_queue = None

    async def _ensure_connected(self) -> None:
        """Ensure Redis connection is active, reconnect if needed."""
        if not self.redis_client or not self.pubsub:
            await self.initialize()
            return

        try:
            await self.redis_client.ping()
            self._reconnect_attempts = 0
            return
        except Exception as e:
            logger.warning(f"Redis connection lost: {e}. Attempting reconnect...")
            await self._reconnect()

    async def _reconnect(self) -> None:
        """Attempt to reconnect to Redis with exponential backoff."""
        if self._reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            self._running = False
            raise ConnectionError("Failed to reconnect to Redis after multiple attempts")

        delay = self.reconnect_delay_seconds * (2 ** self._reconnect_attempts)
        logger.info(f"Reconnecting in {delay} seconds (attempt {self._reconnect_attempts + 1})")

        await asyncio.sleep(delay)

        try:
            await self._cleanup()
            await self.initialize()
            logger.info("Reconnected successfully")
        except Exception as e:
            self._reconnect_attempts += 1
            logger.error(f"Reconnection failed: {e}")
            await self._reconnect()

    # ===== Channel Management =====

    async def subscribe(self, channel: str) -> None:
        """
        Subscribe to a Redis Pub/Sub channel.

        Args:
            channel: Channel name to subscribe to
        """
        await self._ensure_connected()

        if channel in self.subscribed_channels:
            logger.debug(f"Already subscribed to channel: {channel}")
            return

        try:
            await self.pubsub.subscribe(channel)
            self.subscribed_channels.add(channel)
            logger.debug(f"Subscribed to channel: {channel}")
        except Exception as e:
            logger.error(f"Failed to subscribe to channel {channel}: {e}")
            raise

    async def unsubscribe(self, channel: str) -> None:
        """
        Unsubscribe from a Redis Pub/Sub channel.

        Args:
            channel: Channel name to unsubscribe from
        """
        if channel not in self.subscribed_channels:
            logger.debug(f"Not subscribed to channel: {channel}")
            return

        try:
            await self.pubsub.unsubscribe(channel)
            self.subscribed_channels.remove(channel)
            logger.debug(f"Unsubscribed from channel: {channel}")
        except Exception as e:
            logger.error(f"Failed to unsubscribe from channel {channel}: {e}")

    async def psubscribe(self, pattern: str) -> None:
        """
        Subscribe to Redis Pub/Sub pattern (glob pattern).

        Args:
            pattern: Glob pattern (e.g., "agent:*")
        """
        await self._ensure_connected()

        if pattern in self.subscribed_patterns:
            logger.debug(f"Already subscribed to pattern: {pattern}")
            return

        try:
            await self.pubsub.psubscribe(pattern)
            self.subscribed_patterns.add(pattern)
            logger.debug(f"Subscribed to pattern: {pattern}")
        except Exception as e:
            logger.error(f"Failed to subscribe to pattern {pattern}: {e}")
            raise

    async def punsubscribe(self, pattern: str) -> None:
        """
        Unsubscribe from Redis Pub/Sub pattern.

        Args:
            pattern: Glob pattern to unsubscribe from
        """
        if pattern not in self.subscribed_patterns:
            logger.debug(f"Not subscribed to pattern: {pattern}")
            return

        try:
            await self.pubsub.punsubscribe(pattern)
            self.subscribed_patterns.remove(pattern)
            logger.debug(f"Unsubscribed from pattern: {pattern}")
        except Exception as e:
            logger.error(f"Failed to unsubscribe from pattern {pattern}: {e}")

    async def get_subscribed_channels(self) -> List[str]:
        """Get list of currently subscribed channels."""
        return list(self.subscribed_channels)

    async def get_subscribed_patterns(self) -> List[str]:
        """Get list of currently subscribed patterns."""
        return list(self.subscribed_patterns)

    # ===== Message Publishing =====

    async def publish(
        self,
        channel: str,
        message: Dict[str, Any],
        store_in_db: bool = False,
        ttl_seconds: Optional[int] = None
    ) -> int:
        """
        Publish a message to a Redis Pub/Sub channel.

        Args:
            channel: Channel name to publish to
            message: Message data (will be JSON serialized)
            store_in_db: Whether to persist message to database
            ttl_seconds: Optional TTL for Redis caching

        Returns:
            Number of clients that received the message
        """
        await self._ensure_connected()

        try:
            # Prepare message envelope
            envelope = {
                "id": str(uuid.uuid4()),
                "channel": channel,
                "timestamp": datetime.now().isoformat(),
                "data": message,
                "metadata": {
                    "store_in_db": store_in_db,
                    "ttl_seconds": ttl_seconds
                }
            }

            # Serialize to JSON
            message_json = json.dumps(envelope, default=str)

            # Publish to Redis
            result = await self.redis_client.publish(channel, message_json)

            logger.debug(f"Published message to channel {channel}: {result} recipients")

            # Optionally store in database
            if store_in_db:
                asyncio.create_task(self._store_message_in_db(envelope))

            # Optionally set in Redis cache with TTL
            if ttl_seconds and ttl_seconds > 0:
                cache_key = f"swarm:message:{envelope['id']}"
                await self.redis_client.setex(cache_key, ttl_seconds, message_json)

            return result

        except Exception as e:
            logger.error(f"Failed to publish to channel {channel}: {e}")
            raise

    async def _store_message_in_db(self, envelope: Dict[str, Any]) -> None:
        """Store message in database for persistence (background task)."""
        # TODO: Implement database storage using swarm_messages table
        # For now, just log
        logger.debug(f"Would store message in DB: {envelope['id']}")
        pass

    # ===== Message Listening =====

    async def listen(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Listen for messages on subscribed channels.

        Yields:
            Message envelope with id, channel, timestamp, data, metadata

        Usage:
            async for message in pubsub.listen():
                print(f"Received on {message['channel']}: {message['data']}")
        """
        if not self.pubsub or self._message_queue is None:
            await self.initialize()

        # Start listener task if not already running
        if not self._listener_task or self._listener_task.done():
            self._listener_task = asyncio.create_task(self._run_listener())

        # Yield messages from queue
        while self._running:
            try:
                # Get message from internal queue
                message = await self._message_queue.get()
                if message is None:  # Sentinel for shutdown
                    break
                yield message
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in listen generator: {e}")
                await asyncio.sleep(0.1)

    async def _run_listener(self) -> None:
        """Background task to listen for Redis Pub/Sub messages."""
        if not self.pubsub or self._message_queue is None:
            return

        # Message queue already initialized

        try:
            async for raw_message in self.pubsub.listen():
                if not self._running:
                    break

                # Skip subscription confirmation messages
                if raw_message["type"] == "subscribe" or raw_message["type"] == "psubscribe":
                    continue

                # Process message
                try:
                    message = await self._process_raw_message(raw_message)
                    if message:
                        await self._message_queue.put(message)
                except Exception as e:
                    logger.error(f"Error processing raw message: {e}")

        except asyncio.CancelledError:
            logger.debug("Pub/Sub listener cancelled")
        except Exception as e:
            logger.error(f"Pub/Sub listener error: {e}")
            if self._running:
                await self._reconnect()
                # Restart listener
                if self._running:
                    self._listener_task = asyncio.create_task(self._run_listener())
        finally:
            # Only signal listen generator to stop if we're shutting down
            if not self._running:
                await self._message_queue.put(None)

    async def _process_raw_message(self, raw_message: Dict) -> Optional[Dict[str, Any]]:
        """Process raw Redis Pub/Sub message."""
        try:
            # Decode message data
            if raw_message["type"] == "message":
                channel = raw_message["channel"].decode("utf-8")
                data = raw_message["data"]
            elif raw_message["type"] == "pmessage":
                channel = raw_message["channel"].decode("utf-8")
                pattern = raw_message["pattern"].decode("utf-8")
                data = raw_message["data"]
            else:
                return None

            # Parse JSON envelope
            envelope = json.loads(data)

            # Add Redis metadata
            envelope["redis_metadata"] = {
                "message_type": raw_message["type"],
                "pattern": pattern if raw_message["type"] == "pmessage" else None
            }

            return envelope

        except Exception as e:
            logger.error(f"Failed to process raw message: {e}")
            return None

    # ===== Utility Methods =====

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Pub/Sub service."""
        try:
            await self._ensure_connected()

            # Test publish/subscribe
            test_channel = f"swarm:health:{uuid.uuid4().hex[:8]}"
            test_message = {"test": True, "timestamp": datetime.now().isoformat()}

            # Create temporary subscription
            pubsub_temp = self.redis_client.pubsub()
            await pubsub_temp.subscribe(test_channel)

            # Publish test message
            recipients = await self.publish(test_channel, test_message)

            # Wait for message with timeout
            try:
                async with asyncio.timeout(2.0):
                    async for raw_message in pubsub_temp.listen():
                        if raw_message["type"] == "message":
                            await pubsub_temp.unsubscribe(test_channel)
                            await pubsub_temp.close()
                            break
            except asyncio.TimeoutError:
                await pubsub_temp.unsubscribe(test_channel)
                await pubsub_temp.close()
                return {
                    "status": "degraded",
                    "error": "Message delivery timeout",
                    "details": {
                        "subscribed_channels": len(self.subscribed_channels),
                        "subscribed_patterns": len(self.subscribed_patterns),
                        "redis_connected": True,
                        "message_delivery": False
                    }
                }

            return {
                "status": "healthy",
                "details": {
                    "subscribed_channels": len(self.subscribed_channels),
                    "subscribed_patterns": len(self.subscribed_patterns),
                    "redis_connected": True,
                    "message_delivery": True,
                    "recipients": recipients
                }
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "details": {
                    "subscribed_channels": len(self.subscribed_channels),
                    "subscribed_patterns": len(self.subscribed_patterns),
                    "redis_connected": False,
                    "message_delivery": False
                }
            }


# Global Pub/Sub instance
swarm_pubsub = SwarmPubSub()


async def initialize_swarm_pubsub() -> None:
    """Initialize the global swarm Pub/Sub instance."""
    await swarm_pubsub.initialize()


async def close_swarm_pubsub() -> None:
    """Close the global swarm Pub/Sub instance."""
    await swarm_pubsub.close()


if __name__ == "__main__":
    # Test the Pub/Sub wrapper
    async def test():
        await initialize_swarm_pubsub()

        # Test health check
        health = await swarm_pubsub.health_check()
        print("Health Check:", json.dumps(health, indent=2))

        # Test publish/subscribe
        test_channel = "swarm:test"

        async def listener():
            async for message in swarm_pubsub.listen():
                print(f"Received: {message}")
                break

        # Start listener in background
        listener_task = asyncio.create_task(listener())
        await asyncio.sleep(0.1)

        # Subscribe to test channel
        await swarm_pubsub.subscribe(test_channel)

        # Publish test message
        await swarm_pubsub.publish(test_channel, {"hello": "world"})

        # Wait for message
        await asyncio.sleep(1)

        # Cleanup
        listener_task.cancel()
        await close_swarm_pubsub()

    asyncio.run(test())