"""
NEXUS Swarm Communication Layer - Swarm Agent

Extends BaseAgent with swarm capabilities: Redis Pub/Sub communication,
event bus participation, consensus protocol (RAFT), and conflict resolution voting.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Set, AsyncGenerator, Callable, Union
from datetime import datetime
import uuid

from .pubsub import swarm_pubsub
from .event_bus import swarm_event_bus
from .voting import VotingSystem
from ..base import BaseAgent, AgentType, AgentStatus
from ..registry import registry
from ...database import db

logger = logging.getLogger(__name__)


class SwarmAgent(BaseAgent):
    """
    BaseAgent extended with swarm communication capabilities.

    Swarm agents can:
    - Join/leave swarms and consensus groups
    - Communicate via Redis Pub/Sub channels
    - Participate in swarm-wide event propagation
    - Vote in conflict resolution
    - Participate in RAFT consensus for distributed decision-making
    """

    def __init__(
        self,
        swarm_id: Optional[str] = None,
        swarm_role: str = "member",
        **kwargs
    ):
        """
        Initialize a swarm-capable agent.

        Args:
            swarm_id: ID of swarm to join automatically
            swarm_role: Role within swarm ('leader', 'follower', 'candidate', 'observer', 'member')
            **kwargs: Additional BaseAgent arguments
        """
        super().__init__(**kwargs)

        # Swarm attributes
        self.swarm_id = swarm_id
        self.swarm_role = swarm_role
        self.swarm_channels: Set[str] = set()
        self.consensus_group_id: Optional[str] = None
        self.vote_weight: float = 1.0
        self.last_heartbeat_received: Optional[datetime] = None
        self.heartbeat_interval_seconds: int = 5
        self.voting_system: Optional[VotingSystem] = None
        self._running: bool = False

        # Swarm communication state
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._listener_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

        # Swarm event handlers
        self._event_handlers: Dict[str, List[Callable]] = {}

        logger.debug(f"SwarmAgent created: {self.name}, swarm_id: {swarm_id}")

    async def _on_initialize(self) -> None:
        """Swarm-specific initialization."""
        await super()._on_initialize()

        # Set running flag for background tasks
        self._running = True

        # Initialize swarm Pub/Sub if not already initialized
        try:
            from .pubsub import swarm_pubsub
            await swarm_pubsub.initialize()
        except Exception as e:
            logger.warning(f"Failed to initialize swarm Pub/Sub: {e}")

        # Initialize event bus if not already initialized
        try:
            from .event_bus import swarm_event_bus
            await swarm_event_bus.initialize()
        except Exception as e:
            logger.warning(f"Failed to initialize swarm event bus: {e}")

        # Join swarm if specified
        if self.swarm_id:
            await self.join_swarm(self.swarm_id, self.swarm_role)

        # Register swarm-specific tools
        await self._register_swarm_tools()

        # Start background tasks
        self._listener_task = asyncio.create_task(self._listen_for_swarm_messages())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())

        logger.info(f"SwarmAgent initialized: {self.name}")

    async def _on_cleanup(self) -> None:
        """Swarm-specific cleanup."""
        # Stop running flag
        self._running = False

        # Stop background tasks
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Leave swarm
        if self.swarm_id:
            await self.leave_swarm()

        # Unsubscribe from all channels
        await self._unsubscribe_all_channels()

        await super()._on_cleanup()

        logger.info(f"SwarmAgent cleaned up: {self.name}")

    async def _process_task(self, task: Union[str, Dict[str, Any]], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a task using swarm capabilities.

        Default implementation uses AI with swarm context.
        """
        task_text = task if isinstance(task, str) else task.get("description", str(task))

        # Add swarm context to prompt
        swarm_context = ""
        if self.swarm_id:
            swarm_context = f"\n[Swarm Context]\nSwarm ID: {self.swarm_id}\nRole: {self.swarm_role}\n"

        # Use AI with swarm context
        response = await self._ai_request(
            prompt=f"{swarm_context}\n[Task]\n{task_text}",
            task_type="analysis",
            system_prompt=f"You are a swarm agent in the NEXUS system. {self.system_prompt}"
        )

        return {
            "response": response.get("content", ""),
            "swarm_id": self.swarm_id,
            "agent_name": self.name,
            "provider": response.get("provider", "unknown"),
            "tokens": response.get("tokens", 0)
        }

    async def _register_swarm_tools(self) -> None:
        """Register swarm-specific tools."""
        swarm_tools = {
            "join_swarm": self._tool_join_swarm,
            "leave_swarm": self._tool_leave_swarm,
            "send_swarm_message": self._tool_send_swarm_message,
            "list_swarm_members": self._tool_list_swarm_members,
            "create_vote": self._tool_create_vote,
            "cast_vote": self._tool_cast_vote,
            "swarm_health_check": self._tool_swarm_health_check,
        }

        for name, func in swarm_tools.items():
            await self.register_tool(name, func)

    # ===== Swarm Membership Management =====

    async def join_swarm(self, swarm_id: str, role: str = "member") -> Dict[str, Any]:
        """
        Join a swarm and register membership in database.

        Args:
            swarm_id: ID of swarm to join
            role: Role within swarm

        Returns:
            Membership information
        """
        # Check if swarm exists
        swarm = await db.fetch_one(
            "SELECT id, name, max_members FROM swarms WHERE id = $1 AND is_active = true",
            swarm_id
        )

        if not swarm:
            raise ValueError(f"Swarm {swarm_id} not found or inactive")

        # Check if already a member
        existing = await db.fetch_one(
            "SELECT id FROM swarm_memberships WHERE swarm_id = $1 AND agent_id = $2",
            swarm_id, self.agent_id
        )

        if existing:
            logger.info(f"Agent {self.name} already member of swarm {swarm_id}")
            # Update role if changed
            await db.execute(
                "UPDATE swarm_memberships SET role = $1, status = 'active', vote_weight = $2 WHERE id = $3",
                role, self.vote_weight, existing["id"]
            )
        else:
            # Create membership record
            await db.execute(
                """
                INSERT INTO swarm_memberships
                (swarm_id, agent_id, role, status, contribution_score, vote_weight)
                VALUES ($1, $2, $3, 'active', 0.0, $4)
                """,
                swarm_id, self.agent_id, role, self.vote_weight
            )

        # Update agent state
        self.swarm_id = swarm_id
        self.swarm_role = role

        # Initialize voting system for this swarm
        self.voting_system = VotingSystem(swarm_id)
        await self.voting_system.initialize()

        # Subscribe to swarm channels
        await self._subscribe_to_swarm_channels(swarm_id)

        # Send join event
        await self._publish_swarm_event(
            event_type="agent_joined",
            data={"agent_id": self.agent_id, "agent_name": self.name, "role": role}
        )

        logger.info(f"Agent {self.name} joined swarm {swarm_id} as {role}")

        return {
            "swarm_id": swarm_id,
            "swarm_name": swarm["name"],
            "role": role,
            "joined_at": datetime.now().isoformat()
        }

    async def leave_swarm(self) -> Dict[str, Any]:
        """
        Leave current swarm.

        Returns:
            Leave confirmation
        """
        if not self.swarm_id:
            raise ValueError("Agent not in a swarm")

        # Update membership status
        await db.execute(
            "UPDATE swarm_memberships SET status = 'inactive', last_seen_at = NOW() WHERE swarm_id = $1 AND agent_id = $2",
            self.swarm_id, self.agent_id
        )

        # Send leave event
        await self._publish_swarm_event(
            event_type="agent_left",
            data={"agent_id": self.agent_id, "agent_name": self.name}
        )

        # Unsubscribe from swarm channels
        await self._unsubscribe_all_channels()

        logger.info(f"Agent {self.name} left swarm {self.swarm_id}")

        # Close voting system
        if self.voting_system:
            await self.voting_system.close()
            self.voting_system = None

        # Clear swarm state
        left_swarm_id = self.swarm_id
        self.swarm_id = None
        self.swarm_role = "member"
        self.consensus_group_id = None

        return {
            "swarm_id": left_swarm_id,
            "left_at": datetime.now().isoformat()
        }

    async def _subscribe_to_swarm_channels(self, swarm_id: str) -> None:
        """Subscribe to standard swarm communication channels."""
        channels = [
            f"swarm:{swarm_id}:broadcast",      # Broadcast messages
            f"swarm:{swarm_id}:events",         # System events
            f"swarm:{swarm_id}:agent:{self.agent_id}",  # Direct messages
            f"swarm:{swarm_id}:consensus",      # Consensus messages
            f"swarm:{swarm_id}:votes",          # Voting messages
        ]

        for channel in channels:
            try:
                await swarm_pubsub.subscribe(channel)
                self.swarm_channels.add(channel)
                logger.debug(f"Subscribed to channel: {channel}")
            except Exception as e:
                logger.error(f"Failed to subscribe to channel {channel}: {e}")

    async def _unsubscribe_all_channels(self) -> None:
        """Unsubscribe from all swarm channels."""
        for channel in list(self.swarm_channels):
            try:
                await swarm_pubsub.unsubscribe(channel)
                self.swarm_channels.remove(channel)
                logger.debug(f"Unsubscribed from channel: {channel}")
            except Exception as e:
                logger.error(f"Failed to unsubscribe from channel {channel}: {e}")

    # ===== Swarm Communication =====

    async def send_swarm_message(
        self,
        message_type: str,
        data: Dict[str, Any],
        target_agent_id: Optional[str] = None,
        store_in_db: bool = False
    ) -> int:
        """
        Send a message to the swarm.

        Args:
            message_type: Type of message ('direct', 'broadcast', 'multicast', 'event')
            data: Message data
            target_agent_id: For direct messages, the recipient agent ID
            store_in_db: Whether to persist message to database

        Returns:
            Number of recipients that received the message
        """
        if not self.swarm_id:
            raise ValueError("Agent not in a swarm")

        # Determine channel based on message type
        if message_type == "direct" and target_agent_id:
            channel = f"swarm:{self.swarm_id}:agent:{target_agent_id}"
        elif message_type == "broadcast":
            channel = f"swarm:{self.swarm_id}:broadcast"
        elif message_type == "event":
            channel = f"swarm:{self.swarm_id}:events"
        else:
            raise ValueError(f"Unsupported message type: {message_type}")

        # Prepare message envelope
        envelope = {
            "message_type": message_type,
            "sender_agent_id": self.agent_id,
            "sender_name": self.name,
            "target_agent_id": target_agent_id,
            "swarm_id": self.swarm_id,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }

        # Publish message
        recipients = await swarm_pubsub.publish(
            channel=channel,
            message=envelope,
            store_in_db=store_in_db
        )

        logger.debug(f"Sent {message_type} message to {recipients} recipients via {channel}")

        return recipients

    async def _listen_for_swarm_messages(self) -> None:
        """Background task to listen for swarm messages."""
        try:
            async for message in swarm_pubsub.listen():
                if not self._running:
                    break

                # Filter messages for this swarm and agent
                if await self._should_process_message(message):
                    await self._process_swarm_message(message)

        except asyncio.CancelledError:
            logger.debug("Swarm message listener cancelled")
        except Exception as e:
            logger.error(f"Error in swarm message listener: {e}")
            # Restart listener after delay
            await asyncio.sleep(1)
            if self._running:
                self._listener_task = asyncio.create_task(self._listen_for_swarm_messages())

    async def _should_process_message(self, message: Dict[str, Any]) -> bool:
        """Determine if this agent should process a message."""
        # Check swarm ID matches
        if message.get("swarm_id") != self.swarm_id:
            return False

        # Check if message is for this specific agent
        target_id = message.get("target_agent_id")
        if target_id and target_id != self.agent_id:
            return False

        # Check if message is a broadcast or event
        message_type = message.get("message_type")
        if message_type in ["broadcast", "event"]:
            return True

        return True

    async def _process_swarm_message(self, message: Dict[str, Any]) -> None:
        """Process a received swarm message."""
        try:
            message_type = message.get("message_type")
            data = message.get("data", {})

            # Update last heartbeat if it's a heartbeat message
            if message_type == "heartbeat":
                self.last_heartbeat_received = datetime.now()
                return

            # Call registered event handlers
            handlers = self._event_handlers.get(message_type, [])
            for handler in handlers:
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(f"Error in message handler for {message_type}: {e}")

            # Store message in queue for external consumption
            await self._message_queue.put(message)

            logger.debug(f"Processed {message_type} message from {message.get('sender_name')}")

        except Exception as e:
            logger.error(f"Failed to process swarm message: {e}")

    async def receive_swarm_messages(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Receive swarm messages as an async generator.

        Yields:
            Received swarm messages

        Usage:
            async for message in agent.receive_swarm_messages():
                print(f"Received: {message}")
        """
        while self._running:
            try:
                message = await self._message_queue.get()
                yield message
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error receiving swarm messages: {e}")
                await asyncio.sleep(0.1)

    async def _publish_swarm_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish a swarm event."""
        if self.swarm_id:
            await self.send_swarm_message(
                message_type="event",
                data={"event_type": event_type, **data}
            )

    async def publish_swarm_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        is_global: bool = False,
        store_in_db: bool = True
    ) -> str:
        """
        Publish a swarm event using the event bus.

        Args:
            event_type: Type of event
            event_data: Event payload
            is_global: Whether event is swarm-wide
            store_in_db: Whether to persist to database

        Returns:
            Event ID
        """
        if not self.swarm_id:
            raise ValueError("Agent not in a swarm")

        event_id = await swarm_event_bus.publish_event(
            event_type=event_type,
            event_data=event_data,
            source_agent_id=self.agent_id,
            swarm_id=self.swarm_id,
            is_global=is_global,
            store_in_db=store_in_db
        )

        logger.debug(f"Published swarm event {event_id} ({event_type}) via event bus")
        return event_id

    # ===== Heartbeat Monitoring =====

    async def _heartbeat_monitor(self) -> None:
        """Monitor swarm heartbeat and detect failures."""
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval_seconds)

                if self.swarm_id and self.swarm_role == "leader":
                    # Send heartbeat if leader
                    await self._send_heartbeat()
                elif self.last_heartbeat_received:
                    # Check if heartbeat is stale
                    time_since = (datetime.now() - self.last_heartbeat_received).total_seconds()
                    if time_since > self.heartbeat_interval_seconds * 3:
                        logger.warning(f"No heartbeat received for {time_since:.1f} seconds")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")
                await asyncio.sleep(1)

    async def _send_heartbeat(self) -> None:
        """Send heartbeat to swarm."""
        if self.swarm_id:
            await self.send_swarm_message(
                message_type="heartbeat",
                data={
                    "leader_id": self.agent_id,
                    "leader_name": self.name,
                    "timestamp": datetime.now().isoformat(),
                    "swarm_health": "healthy"
                }
            )

    # ===== Voting & Conflict Resolution =====

    async def create_vote(
        self,
        subject: str,
        description: str,
        options: List[str],
        voting_strategy: str = "simple_majority",
        required_quorum: float = 0.51,
        expires_in_hours: int = 24,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new vote for swarm conflict resolution.

        Args:
            subject: What is being voted on
            description: Detailed description
            options: List of vote options
            voting_strategy: Voting strategy ('simple_majority', 'super_majority', 'weighted', 'consensus')
            required_quorum: Minimum participation (0.0-1.0)
            expires_in_hours: Hours until vote expires
            metadata: Additional metadata

        Returns:
            Vote ID
        """
        if not self.swarm_id or not self.voting_system:
            raise ValueError("Agent not in a swarm or voting system not initialized")

        vote_id = await self.voting_system.create_vote(
            vote_type="conflict_resolution",
            subject=subject,
            description=description,
            options=options,
            created_by_agent_id=self.agent_id,
            voting_strategy=voting_strategy,
            required_quorum=required_quorum,
            expires_in_hours=expires_in_hours,
            metadata=metadata
        )

        logger.info(f"Created vote {vote_id}: {subject}")

        return vote_id

    async def cast_vote(
        self,
        vote_id: str,
        option: str,
        confidence: float = 1.0,
        rationale: str = "",
        vote_weight: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Cast a vote in a swarm vote.

        Args:
            vote_id: ID of vote to participate in
            option: Selected option
            confidence: Confidence in vote (0.0-1.0)
            rationale: Explanation for vote
            vote_weight: Weight of agent's vote (defaults to agent's vote weight from membership)

        Returns:
            Vote confirmation
        """
        if not self.swarm_id or not self.voting_system:
            raise ValueError("Agent not in a swarm or voting system not initialized")

        # Get agent's vote weight from membership if not provided
        if vote_weight is None:
            membership = await db.fetch_one(
                "SELECT vote_weight FROM swarm_memberships WHERE swarm_id = $1 AND agent_id = $2",
                self.swarm_id, self.agent_id
            )
            vote_weight = membership["vote_weight"] if membership else 1.0

        result = await self.voting_system.cast_vote(
            vote_id=vote_id,
            agent_id=self.agent_id,
            option=option,
            confidence=confidence,
            rationale=rationale,
            vote_weight=vote_weight
        )

        logger.info(f"Agent {self.name} cast vote for option '{option}' in vote {vote_id}")

        return result

    # ===== Event Handlers =====

    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """
        Register a handler for specific swarm event types.

        Args:
            event_type: Event type to handle
            handler: Async function that takes event data as parameter
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
        logger.debug(f"Registered handler for event type: {event_type}")

    def unregister_event_handler(self, event_type: str, handler: Callable) -> None:
        """Unregister an event handler."""
        if event_type in self._event_handlers:
            self._event_handlers[event_type] = [h for h in self._event_handlers[event_type] if h != handler]
            logger.debug(f"Unregistered handler for event type: {event_type}")

    async def subscribe_to_event_bus(self, event_type: str, handler: Optional[Callable] = None) -> None:
        """
        Subscribe to events from the swarm event bus.

        Args:
            event_type: Type of event to subscribe to
            handler: Optional async handler function (defaults to using internal event handlers)
        """
        subscriber_id = f"agent:{self.agent_id}"
        target_handler = handler

        if not handler:
            # Use internal event handler registration
            async def event_bus_handler(event):
                # Convert event bus format to swarm message format
                swarm_message = {
                    "message_type": "event",
                    "event_type": event["event_type"],
                    "data": event["event_data"],
                    "swarm_id": event.get("swarm_id"),
                    "source_agent_id": event.get("source_agent_id"),
                    "timestamp": event.get("timestamp")
                }
                await self._process_swarm_message(swarm_message)

            target_handler = event_bus_handler

        await swarm_event_bus.subscribe(event_type, subscriber_id, target_handler)
        logger.debug(f"Agent {self.name} subscribed to event bus for {event_type}")

    async def unsubscribe_from_event_bus(self, event_type: str) -> None:
        """Unsubscribe from event bus events."""
        subscriber_id = f"agent:{self.agent_id}"
        await swarm_event_bus.unsubscribe(event_type, subscriber_id)
        logger.debug(f"Agent {self.name} unsubscribed from event bus for {event_type}")

    # ===== Tool Implementations =====

    async def _tool_join_swarm(self, swarm_id: str, role: str = "member") -> Dict[str, Any]:
        """Tool: Join a swarm."""
        return await self.join_swarm(swarm_id, role)

    async def _tool_leave_swarm(self) -> Dict[str, Any]:
        """Tool: Leave current swarm."""
        return await self.leave_swarm()

    async def _tool_send_swarm_message(
        self,
        message_type: str,
        data: Dict[str, Any],
        target_agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tool: Send a swarm message."""
        recipients = await self.send_swarm_message(message_type, data, target_agent_id)
        return {"recipients": recipients, "message_type": message_type}

    async def _tool_list_swarm_members(self) -> Dict[str, Any]:
        """Tool: List all members of current swarm."""
        if not self.swarm_id:
            return {"error": "Not in a swarm"}

        members = await db.fetch_all(
            """
            SELECT a.id, a.name, a.agent_type, sm.role, sm.status, sm.contribution_score, sm.vote_weight, sm.last_seen_at
            FROM swarm_memberships sm
            JOIN agents a ON sm.agent_id = a.id
            WHERE sm.swarm_id = $1 AND sm.status = 'active'
            ORDER BY sm.role, sm.contribution_score DESC
            """,
            self.swarm_id
        )

        return {
            "swarm_id": self.swarm_id,
            "members": members
        }

    async def _tool_create_vote(
        self,
        subject: str,
        description: str,
        options: List[str],
        voting_strategy: str = "simple_majority",
        required_quorum: float = 0.51,
        expires_in_hours: int = 24,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Tool: Create a new vote."""
        vote_id = await self.create_vote(
            subject=subject,
            description=description,
            options=options,
            voting_strategy=voting_strategy,
            required_quorum=required_quorum,
            expires_in_hours=expires_in_hours,
            metadata=metadata
        )
        return {"vote_id": vote_id, "subject": subject, "status": "open"}

    async def _tool_cast_vote(
        self,
        vote_id: str,
        option: str,
        confidence: float = 1.0,
        rationale: str = "",
        vote_weight: Optional[float] = None
    ) -> Dict[str, Any]:
        """Tool: Cast a vote."""
        return await self.cast_vote(vote_id, option, confidence, rationale, vote_weight)

    async def _tool_swarm_health_check(self) -> Dict[str, Any]:
        """Tool: Check swarm health."""
        if not self.swarm_id:
            return {"error": "Not in a swarm"}

        # Get swarm health from database
        swarm = await db.fetch_one(
            "SELECT name, purpose, swarm_type, max_members, is_active FROM swarms WHERE id = $1",
            self.swarm_id
        )

        # Get member count
        member_count = await db.fetch_one(
            "SELECT COUNT(*) as count FROM swarm_memberships WHERE swarm_id = $1 AND status = 'active'",
            self.swarm_id
        )

        # Get recent activity
        recent_messages = await db.fetch_one(
            "SELECT COUNT(*) as count FROM swarm_messages WHERE swarm_id = $1 AND created_at > NOW() - INTERVAL '1 hour'",
            self.swarm_id
        )

        # Check Pub/Sub health
        pubsub_health = await swarm_pubsub.health_check()

        return {
            "swarm": {
                "id": self.swarm_id,
                "name": swarm["name"],
                "purpose": swarm["purpose"],
                "type": swarm["swarm_type"],
                "active": swarm["is_active"],
                "member_count": member_count["count"],
                "max_members": swarm["max_members"]
            },
            "activity": {
                "recent_messages": recent_messages["count"]
            },
            "pubsub": pubsub_health
        }


# Convenience function to create a swarm agent
async def create_swarm_agent(
    name: str,
    swarm_id: Optional[str] = None,
    swarm_role: str = "member",
    agent_type: AgentType = AgentType.DOMAIN,
    **kwargs
) -> SwarmAgent:
    """
    Create and initialize a swarm agent.

    Args:
        name: Agent name
        swarm_id: Optional swarm to join
        swarm_role: Role in swarm
        agent_type: Agent type
        **kwargs: Additional agent configuration

    Returns:
        Initialized swarm agent
    """
    agent = SwarmAgent(
        name=name,
        swarm_id=swarm_id,
        swarm_role=swarm_role,
        agent_type=agent_type,
        **kwargs
    )

    await agent.initialize()
    return agent