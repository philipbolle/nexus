"""
NEXUS Swarm Communication Layer - Event Bus System

Event bus for swarm-wide event propagation with persistence.
Built on Redis Pub/Sub with database storage for event history.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable, Set, AsyncGenerator
import uuid
from datetime import datetime

from .pubsub import swarm_pubsub
from ...database import db

logger = logging.getLogger(__name__)


class SwarmEventBus:
    """
    Event bus for swarm-wide event propagation.

    Features:
    - Redis Pub/Sub for real-time event delivery
    - PostgreSQL persistence for event history
    - Event filtering by type and source
    - Event replay and subscription management
    """

    def __init__(self):
        """Initialize event bus."""
        self._subscriptions: Dict[str, Set[str]] = {}  # event_type -> set of subscriber IDs
        self._handlers: Dict[str, List[Callable]] = {}  # event_type -> list of handler functions
        self._running = False
        self._listener_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize event bus and start listener."""
        logger.debug("EventBus.initialize() starting")
        # Ensure Pub/Sub is initialized
        await swarm_pubsub.initialize()

        self._running = True
        self._listener_task = asyncio.create_task(self._listen_for_events())
        logger.debug("EventBus.initialize() listener task created")

        logger.info("SwarmEventBus initialized")

    async def close(self) -> None:
        """Close event bus and cleanup."""
        self._running = False

        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

        # Clear subscriptions
        self._subscriptions.clear()
        self._handlers.clear()

        logger.info("SwarmEventBus closed")

    # ===== Event Publishing =====

    async def publish_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        source_agent_id: Optional[str] = None,
        swarm_id: Optional[str] = None,
        is_global: bool = False,
        store_in_db: bool = True
    ) -> str:
        """
        Publish an event to the swarm event bus.

        Args:
            event_type: Type of event (e.g., 'agent_joined', 'task_completed')
            event_data: Event payload
            source_agent_id: ID of agent that generated the event
            swarm_id: ID of swarm this event belongs to
            is_global: Whether event is swarm-wide
            store_in_db: Whether to persist event to database

        Returns:
            Event ID
        """
        event_id = str(uuid.uuid4())
        timestamp = datetime.now()

        # Create event envelope
        envelope = {
            "event_id": event_id,
            "event_type": event_type,
            "event_data": event_data,
            "source_agent_id": source_agent_id,
            "swarm_id": swarm_id,
            "is_global": is_global,
            "timestamp": timestamp.isoformat(),
            "metadata": {
                "store_in_db": store_in_db,
                "propagation_count": 0
            }
        }

        # Publish to Redis Pub/Sub
        channel = f"swarm:events:{event_type}"
        if swarm_id:
            channel = f"swarm:{swarm_id}:events:{event_type}"

        recipients = await swarm_pubsub.publish(
            channel=channel,
            message=envelope,
            store_in_db=store_in_db
        )

        logger.debug(f"Published event {event_id} ({event_type}) to {recipients} recipients")

        # Store in database if requested
        if store_in_db:
            asyncio.create_task(self._store_event_in_db(envelope))

        return event_id

    async def _store_event_in_db(self, envelope: Dict[str, Any]) -> None:
        """Store event in database for persistence."""
        try:
            # Convert ISO timestamp string back to datetime for PostgreSQL
            from datetime import datetime
            timestamp_str = envelope["timestamp"]
            timestamp_dt = datetime.fromisoformat(timestamp_str) if isinstance(timestamp_str, str) else timestamp_str

            await db.execute(
                """
                INSERT INTO swarm_events
                (id, swarm_id, event_type, event_data, source_agent_id, is_global, occurred_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                envelope["event_id"],
                envelope.get("swarm_id"),
                envelope["event_type"],
                json.dumps(envelope["event_data"]),
                envelope.get("source_agent_id"),
                envelope.get("is_global", False),
                timestamp_dt
            )
            logger.debug(f"Stored event {envelope['event_id']} in database")
        except Exception as e:
            logger.error(f"Failed to store event in database: {e}")

    # ===== Event Subscription & Handling =====

    async def subscribe(
        self,
        event_type: str,
        subscriber_id: str,
        handler: Optional[Callable] = None
    ) -> None:
        """
        Subscribe to events of a specific type.

        Args:
            event_type: Type of event to subscribe to
            subscriber_id: Unique identifier for subscriber
            handler: Optional async function to call when event is received
        """
        # Subscribe to Redis channel
        channel = f"swarm:events:{event_type}"
        try:
            logger.debug(f"EventBus.subscribe() calling swarm_pubsub.subscribe({channel})")
            await swarm_pubsub.subscribe(channel)
            logger.debug("EventBus.subscribe() subscribed successfully")
        except Exception as e:
            logger.warning(f"Failed to subscribe to channel {channel}: {e}")
            logger.debug(f"EventBus.subscribe() FAILED: {e}")

        # Track subscription
        if event_type not in self._subscriptions:
            self._subscriptions[event_type] = set()
        self._subscriptions[event_type].add(subscriber_id)

        # Register handler if provided
        if handler:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
            logger.debug(f"EventBus.subscribe() registered handler for {event_type}, total handlers: {len(self._handlers[event_type])}")

        logger.debug(f"Subscriber {subscriber_id} subscribed to {event_type}")

    async def unsubscribe(self, event_type: str, subscriber_id: str) -> None:
        """
        Unsubscribe from events of a specific type.

        Args:
            event_type: Type of event to unsubscribe from
            subscriber_id: Subscriber identifier
        """
        # Remove subscription tracking
        if event_type in self._subscriptions:
            self._subscriptions[event_type].discard(subscriber_id)
            if not self._subscriptions[event_type]:
                del self._subscriptions[event_type]

        # Remove handler
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type]
                # Note: We need a way to identify which handler belongs to which subscriber
                # For simplicity, we'll keep handler removal separate
            ]

        # Unsubscribe from Redis channel if no subscribers left
        if event_type not in self._subscriptions:
            channel = f"swarm:events:{event_type}"
            try:
                await swarm_pubsub.unsubscribe(channel)
            except Exception as e:
                logger.warning(f"Failed to unsubscribe from channel {channel}: {e}")

        logger.debug(f"Subscriber {subscriber_id} unsubscribed from {event_type}")

    def register_handler(self, event_type: str, handler: Callable) -> None:
        """
        Register a handler function for specific event type.

        Args:
            event_type: Event type to handle
            handler: Async function that takes event data as parameter
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Registered handler for event type: {event_type}")

    def unregister_handler(self, event_type: str, handler: Callable) -> None:
        """Unregister a handler function."""
        if event_type in self._handlers:
            self._handlers[event_type] = [h for h in self._handlers[event_type] if h != handler]
            logger.debug(f"Unregistered handler for event type: {event_type}")

    # ===== Event Listening =====

    async def _listen_for_events(self) -> None:
        """Background task to listen for events."""
        logger.debug(f"EventBus._listen_for_events() starting")
        try:
            async for message in swarm_pubsub.listen():
                if not self._running:
                    logger.debug(f"EventBus._listen_for_events() not running, breaking")
                    break

                logger.debug(f"EventBus._listen_for_events() got message: {message.get('id', 'no-id')}")
                # Check if message is an event
                # Message is a Pub/Sub envelope with "data" field containing the actual event
                event_data = message.get("data")
                if isinstance(event_data, dict) and "event_type" in event_data:
                    logger.debug(f"EventBus._listen_for_events() processing as event_data")
                    await self._process_event(event_data)
                # Also check if message itself has event_type (backward compatibility)
                elif "event_type" in message:
                    logger.debug(f"EventBus._listen_for_events() processing as message")
                    await self._process_event(message)
                else:
                    logger.debug(f"EventBus._listen_for_events() not an event: {message.keys() if isinstance(message, dict) else type(message)}")

        except asyncio.CancelledError:
            logger.debug("Event bus listener cancelled")
            logger.debug(f"EventBus._listen_for_events() cancelled")
        except Exception as e:
            logger.error(f"Error in event bus listener: {e}")
            logger.debug(f"EventBus._listen_for_events() error: {e}")
            # Restart listener after delay
            await asyncio.sleep(1)
            if self._running:
                self._listener_task = asyncio.create_task(self._listen_for_events())

    async def _process_event(self, event: Dict[str, Any]) -> None:
        """Process incoming event."""
        logger.debug(f"EventBus._process_event() called: {event.get('event_id', 'no-id')} type: {event.get('event_type', 'no-type')}")
        try:
            event_type = event["event_type"]
            event_data = event["event_data"]

            # Call registered handlers
            handlers = self._handlers.get(event_type, [])
            logger.debug(f"EventBus._process_event() has {len(handlers)} handlers for {event_type}")
            for handler in handlers:
                try:
                    logger.debug(f"EventBus._process_event() calling handler")
                    await handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")
                    logger.debug(f"EventBus._process_event() handler error: {e}")

            logger.debug(f"Processed event {event['event_id']} ({event_type})")
            logger.debug(f"EventBus._process_event() completed")

        except Exception as e:
            logger.error(f"Failed to process event: {e}")
            logger.debug(f"EventBus._process_event() error: {e}")

    # ===== Event Querying =====

    async def get_events(
        self,
        event_type: Optional[str] = None,
        swarm_id: Optional[str] = None,
        source_agent_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve events from database.

        Args:
            event_type: Filter by event type
            swarm_id: Filter by swarm ID
            source_agent_id: Filter by source agent
            limit: Maximum number of events to return
            offset: Offset for pagination

        Returns:
            List of event records
        """
        query = """
            SELECT id, swarm_id, event_type, event_data, source_agent_id,
                   is_global, occurred_at, created_at
            FROM swarm_events
            WHERE 1=1
        """
        params = []
        param_count = 0

        if event_type:
            param_count += 1
            query += f" AND event_type = ${param_count}"
            params.append(event_type)

        if swarm_id:
            param_count += 1
            query += f" AND swarm_id = ${param_count}"
            params.append(swarm_id)

        if source_agent_id:
            param_count += 1
            query += f" AND source_agent_id = ${param_count}"
            params.append(source_agent_id)

        query += f" ORDER BY occurred_at DESC LIMIT ${param_count + 1} OFFSET ${param_count + 2}"
        params.extend([limit, offset])

        rows = await db.fetch_all(query, *params)
        return [dict(row) for row in rows]

    async def get_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific event by ID."""
        row = await db.fetch_one(
            """
            SELECT id, swarm_id, event_type, event_data, source_agent_id,
                   is_global, occurred_at, created_at
            FROM swarm_events
            WHERE id = $1
            """,
            event_id
        )
        return dict(row) if row else None

    async def replay_events(
        self,
        event_type: Optional[str] = None,
        swarm_id: Optional[str] = None,
        since: Optional[datetime] = None,
        handlers: Optional[List[Callable]] = None
    ) -> None:
        """
        Replay historical events to handlers.

        Args:
            event_type: Filter by event type
            swarm_id: Filter by swarm ID
            since: Replay events since this timestamp
            handlers: Optional list of handlers to use (defaults to registered handlers)
        """
        query = """
            SELECT id, swarm_id, event_type, event_data, source_agent_id,
                   is_global, occurred_at
            FROM swarm_events
            WHERE 1=1
        """
        params = []
        param_count = 0

        if event_type:
            param_count += 1
            query += f" AND event_type = ${param_count}"
            params.append(event_type)

        if swarm_id:
            param_count += 1
            query += f" AND swarm_id = ${param_count}"
            params.append(swarm_id)

        if since:
            param_count += 1
            query += f" AND occurred_at >= ${param_count}"
            params.append(since)

        query += " ORDER BY occurred_at ASC"

        rows = await db.fetch_all(query, *params)

        # Use provided handlers or default to registered handlers
        target_handlers = handlers
        if target_handlers is None:
            target_handlers = self._handlers.get(event_type, []) if event_type else []

        for row in rows:
            event = dict(row)
            for handler in target_handlers:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Error replaying event {event['id']}: {e}")

        logger.info(f"Replayed {len(rows)} events")

    # ===== Health & Monitoring =====

    async def health_check(self) -> Dict[str, Any]:
        """Check event bus health."""
        try:
            # Check Redis connection
            pubsub_health = await swarm_pubsub.health_check()

            # Check database connection
            try:
                await db.fetch_one("SELECT COUNT(*) FROM swarm_events LIMIT 1")
                db_connected = True
            except Exception:
                db_connected = False

            # Check subscriptions
            total_subscriptions = sum(len(subs) for subs in self._subscriptions.values())

            return {
                "status": "healthy" if pubsub_health.get("status") == "healthy" and db_connected else "degraded",
                "details": {
                    "pubsub": pubsub_health,
                    "database_connected": db_connected,
                    "total_subscriptions": total_subscriptions,
                    "event_types_subscribed": list(self._subscriptions.keys()),
                    "handler_counts": {et: len(h) for et, h in self._handlers.items()}
                }
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "details": {
                    "pubsub": {"status": "unknown"},
                    "database_connected": False,
                    "total_subscriptions": 0,
                    "event_types_subscribed": [],
                    "handler_counts": {}
                }
            }


# Global event bus instance
swarm_event_bus = SwarmEventBus()


async def initialize_event_bus() -> None:
    """Initialize the global event bus instance."""
    await swarm_event_bus.initialize()


async def close_event_bus() -> None:
    """Close the global event bus instance."""
    await swarm_event_bus.close()