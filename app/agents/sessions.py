"""
NEXUS Multi-Agent Framework - Session Management

Session creation, message tracking, cost attribution, and conversation management.
Provides persistent conversation context across agent interactions.
"""

import asyncio
import logging
import uuid
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from ..database import db
from ..agents.base import BaseAgent
from ..services.ai_providers import ai_request, TaskType

logger = logging.getLogger(__name__)


class SessionType(Enum):
    """Types of sessions."""
    CHAT = "chat"              # Interactive conversation
    TASK = "task"              # Task execution
    AUTOMATION = "automation"  # Automated workflow
    COLLABORATION = "collaboration"  # Multi-agent collaboration
    ANALYSIS = "analysis"      # Data analysis session


class SessionStatus(Enum):
    """Session lifecycle status."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    FAILED = "failed"


@dataclass
class SessionConfig:
    """Configuration for a session."""

    session_type: SessionType = SessionType.CHAT
    max_messages: int = 100
    max_tokens: int = 4000
    max_duration_hours: int = 24
    allow_agent_switching: bool = True
    enable_cost_tracking: bool = True
    enable_message_history: bool = True
    # Memory retention policies
    memory_retention_days: int = 30  # How long to keep session in memory system
    store_summary_in_memory: bool = True  # Whether to store AI summary in memory system
    enable_session_analytics: bool = True  # Whether to generate analytics
    auto_generate_summary: bool = True  # Whether to auto-generate AI summary on session end
    metadata: Optional[Dict[str, Any]] = None


class SessionManager:
    """
    Manages agent sessions and conversation history.

    Provides:
    - Session lifecycle management
    - Message history with tool call attribution
    - Cost tracking per session and per agent
    - Conversation context management
    """

    def __init__(self):
        """Initialize the session manager."""
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.session_locks: Dict[str, asyncio.Lock] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """
        Initialize the session manager.

        Starts background cleanup task.
        """
        logger.info("Initializing session manager...")

        # Load active sessions from database
        await self._load_active_sessions()

        # Start background cleanup
        self._cleanup_task = asyncio.create_task(self._run_cleanup())

        logger.info(f"Session manager initialized with {len(self.active_sessions)} active sessions")

    async def shutdown(self) -> None:
        """
        Shutdown the session manager.

        Stops background cleanup and saves session state.
        """
        logger.info("Shutting down session manager...")

        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Save session states
        await self._save_session_states()

        logger.info("Session manager shut down")

    async def create_session(
        self,
        title: str,
        primary_agent_id: Optional[str] = None,
        config: Optional[SessionConfig] = None,
        session_type: Optional[str] = None
    ) -> str:
        """
        Create a new session.

        Args:
            title: Session title
            primary_agent_id: Primary agent for the session
            config: Session configuration
            session_type: Override session type (string)

        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        session_config = config or SessionConfig()

        # Override session_type if provided
        if session_type:
            try:
                session_config.session_type = SessionType(session_type)
            except ValueError:
                logger.warning(f"Invalid session type '{session_type}', defaulting to CHAT")
                session_config.session_type = SessionType.CHAT

        logger.info(f"Creating session {session_id}: {title}")

        try:
            # Create session in database
            await db.execute(
                """
                INSERT INTO sessions
                (id, session_type, title, summary, primary_agent_id,
                 agents_involved, status, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                session_id,
                session_config.session_type.value,
                title,
                "",
                primary_agent_id,
                [primary_agent_id] if primary_agent_id else [],
                SessionStatus.ACTIVE.value,
                json.dumps(session_config.metadata or {})
            )

            # Create in-memory session record
            self.active_sessions[session_id] = {
                "id": session_id,
                "title": title,
                "type": session_config.session_type.value,
                "primary_agent_id": primary_agent_id,
                "agents_involved": [primary_agent_id] if primary_agent_id else [],
                "config": session_config,
                "message_count": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "created_at": datetime.now(),
                "last_message_at": datetime.now(),
                "status": SessionStatus.ACTIVE.value,
                "metadata": session_config.metadata or {}
            }

            # Create session lock
            self.session_locks[session_id] = asyncio.Lock()

            logger.info(f"Session created: {session_id}")
            return session_id

        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent_id: Optional[str] = None,
        parent_message_id: Optional[str] = None,
        tool_calls: Optional[Dict[str, Any]] = None,
        tool_results: Optional[Dict[str, Any]] = None,
        tokens_input: Optional[int] = None,
        tokens_output: Optional[int] = None,
        cost_usd: Optional[float] = None,
        model_used: Optional[str] = None,
        latency_ms: Optional[int] = None
    ) -> str:
        """
        Add a message to a session.

        Args:
            session_id: Session ID
            role: Message role (user, assistant, system, tool)
            content: Message content
            agent_id: Agent that generated the message
            parent_message_id: Parent message ID
            tool_calls: Tool calls made in this message
            tool_results: Tool execution results
            tokens_input: Input tokens used
            tokens_output: Output tokens used
            cost_usd: Cost of this message
            model_used: Model used
            latency_ms: Latency in milliseconds

        Returns:
            Message ID
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found or not active")

        message_id = str(uuid.uuid4())

        async with self.session_locks[session_id]:
            session = self.active_sessions[session_id]

            # Update session metrics
            session["message_count"] += 1
            session["last_message_at"] = datetime.now()

            if tokens_input:
                session["total_tokens"] += tokens_input
            if tokens_output:
                session["total_tokens"] += tokens_output
            if cost_usd:
                session["total_cost_usd"] += cost_usd

            # Add agent to involved agents if not already
            if agent_id and agent_id not in session["agents_involved"]:
                session["agents_involved"].append(agent_id)

            # Store message in database
            try:
                await db.execute(
                    """
                    INSERT INTO messages
                    (id, session_id, role, content, agent_id, parent_message_id,
                     tool_calls, tool_results, tokens_input, tokens_output,
                     cost_usd, model_used, latency_ms)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    """,
                    message_id,
                    session_id,
                    role,
                    content,
                    agent_id,
                    parent_message_id,
                    json.dumps(tool_calls) if tool_calls else None,
                    json.dumps(tool_results) if tool_results else None,
                    tokens_input,
                    tokens_output,
                    cost_usd,
                    model_used,
                    latency_ms
                )

                # Update session in database
                await db.execute(
                    """
                    UPDATE sessions SET
                        last_message_at = NOW(),
                        total_messages = total_messages + 1,
                        total_tokens = total_tokens + $2,
                        total_cost_usd = total_cost_usd + $3,
                        agents_involved = $4
                    WHERE id = $1
                    """,
                    session_id,
                    (tokens_input or 0) + (tokens_output or 0),
                    cost_usd or 0.0,
                    session["agents_involved"]
                )

                logger.debug(f"Message added to session {session_id}: {role} ({len(content)} chars)")

            except Exception as e:
                logger.error(f"Failed to store message for session {session_id}: {e}")
                raise

        return message_id

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session information.

        Args:
            session_id: Session ID

        Returns:
            Session information or None if not found
        """
        # Check active sessions first
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            # Convert active session format to match SessionResponse schema
            return {
                "id": session["id"],
                "session_type": session.get("type", session.get("session_type", "chat")),
                "title": session.get("title", ""),
                "summary": session.get("summary"),
                "primary_agent_id": session.get("primary_agent_id"),
                "agents_involved": session.get("agents_involved", []),
                "total_messages": session.get("message_count", session.get("total_messages", 0)),
                "total_tokens": session.get("total_tokens", 0),
                "total_cost_usd": session.get("total_cost_usd", 0.0),
                "status": session.get("status", "active"),
                "started_at": session.get("created_at", session.get("started_at", datetime.now())),
                "last_message_at": session.get("last_message_at"),
                "ended_at": session.get("ended_at"),
                "metadata": session.get("metadata", {})
            }

        # Try to load from database
        return await self._load_session_from_db(session_id)

    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0,
        include_tool_calls: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get messages for a session.

        Args:
            session_id: Session ID
            limit: Maximum number of messages
            offset: Offset for pagination
            include_tool_calls: Include tool call information

        Returns:
            List of messages
        """
        try:
            rows = await db.fetch_all(
                """
                SELECT id, role, content, agent_id, parent_message_id,
                       tool_calls, tool_results, tokens_input, tokens_output,
                       cost_usd, model_used, latency_ms, created_at
                FROM messages
                WHERE session_id = $1
                ORDER BY created_at
                LIMIT $2 OFFSET $3
                """,
                session_id,
                limit,
                offset
            )

            messages = []
            for row in rows:
                message = {
                    "id": row["id"],
                    "role": row["role"],
                    "content": row["content"],
                    "agent_id": row["agent_id"],
                    "parent_message_id": row["parent_message_id"],
                    "created_at": row["created_at"],
                    "tokens_input": row["tokens_input"],
                    "tokens_output": row["tokens_output"],
                    "cost_usd": float(row["cost_usd"]) if row["cost_usd"] else None,
                    "model_used": row["model_used"],
                    "latency_ms": row["latency_ms"]
                }

                if include_tool_calls:
                    message["tool_calls"] = row["tool_calls"]
                    message["tool_results"] = row["tool_results"]

                messages.append(message)

            return messages

        except Exception as e:
            logger.error(f"Failed to get messages for session {session_id}: {e}")
            return []

    async def get_messages(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all messages for a session (legacy API compatibility).

        Args:
            session_id: Session ID

        Returns:
            List of messages or empty list if session not found
        """
        # Use the existing get_session_messages with default parameters
        return await self.get_session_messages(session_id)

    async def update_session(
        self,
        session_id: str,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update session information.

        Args:
            session_id: Session ID
            title: New title
            summary: New summary
            status: New status
            metadata: Updated metadata

        Returns:
            True if successful
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Cannot update inactive session: {session_id}")
            return False

        async with self.session_locks[session_id]:
            session = self.active_sessions[session_id]
            updates = []
            params = []
            param_count = 0

            if title is not None:
                param_count += 1
                updates.append("title = $" + str(param_count))
                params.append(title)
                session["title"] = title

            if summary is not None:
                param_count += 1
                updates.append("summary = $" + str(param_count))
                params.append(summary)

            if status is not None:
                param_count += 1
                updates.append("status = $" + str(param_count))
                params.append(status.value)
                session["status"] = status.value

                if status == SessionStatus.COMPLETED:
                    session["ended_at"] = datetime.now()
                    updates.append("ended_at = NOW()")

            if metadata is not None:
                # Merge with existing metadata
                current_metadata = session.get("metadata", {})
                merged_metadata = {**current_metadata, **metadata}
                param_count += 1
                updates.append("metadata = $" + str(param_count))
                params.append(merged_metadata)
                session["metadata"] = merged_metadata

            if not updates:
                return True  # Nothing to update

            # Add session ID as last parameter
            param_count += 1
            session_id_param = "$" + str(param_count)
            params.append(session_id)

            # Update database
            try:
                set_clause = ", ".join(updates)
                query = "UPDATE sessions SET " + set_clause + ", updated_at = NOW() WHERE id = " + session_id_param
                logger.debug(f"update_session SQL: {query}")
                logger.debug(f"update_session params: {params}")
                await db.execute(query, *params)

                logger.info(f"Updated session {session_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to update session {session_id}: {e}")
                return False

    async def end_session(
        self,
        session_id: str,
        status: SessionStatus = SessionStatus.COMPLETED,
        summary: Optional[str] = None
    ) -> bool:
        """
        End a session.

        Args:
            session_id: Session ID
            status: Final status
            summary: Session summary

        Returns:
            True if successful
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Cannot end inactive session: {session_id}")
            return False

        logger.info(f"Ending session {session_id} with status {status.value}")

        async with self.session_locks[session_id]:
            try:
                # Update session
                await self.update_session(
                    session_id,
                    status=status,
                    summary=summary
                )

                # Generate final summary if not provided
                if not summary and status == SessionStatus.COMPLETED:
                    await self._generate_session_summary(session_id)

                # Remove from active sessions
                session = self.active_sessions.pop(session_id, None)
                if session:
                    session["ended_at"] = datetime.now()

                # Remove lock
                self.session_locks.pop(session_id, None)

                logger.info(f"Session {session_id} ended")
                return True

            except Exception as e:
                logger.error(f"Failed to end session {session_id}: {e}")
                return False

    async def add_agent_to_session(self, session_id: str, agent_id: str) -> bool:
        """
        Add an agent to a session.

        Args:
            session_id: Session ID
            agent_id: Agent ID

        Returns:
            True if successful
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Cannot add agent to inactive session: {session_id}")
            return False

        async with self.session_locks[session_id]:
            session = self.active_sessions[session_id]

            if agent_id in session["agents_involved"]:
                logger.debug(f"Agent {agent_id} already in session {session_id}")
                return True

            # Add agent to session
            session["agents_involved"].append(agent_id)

            try:
                await db.execute(
                    """
                    UPDATE sessions SET
                        agents_involved = array_append(agents_involved, $2),
                        updated_at = NOW()
                    WHERE id = $1
                    """,
                    session_id,
                    agent_id
                )

                logger.info(f"Added agent {agent_id} to session {session_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to add agent {agent_id} to session {session_id}: {e}")
                # Rollback
                session["agents_involved"].remove(agent_id)
                return False

    async def get_session_cost_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get cost summary for a session.

        Args:
            session_id: Session ID

        Returns:
            Cost summary
        """
        try:
            # Get session info
            session_info = await db.fetch_one(
                """
                SELECT total_cost_usd, total_tokens, total_messages
                FROM sessions
                WHERE id = $1
                """,
                session_id
            )

            if not session_info:
                return {"error": "Session not found"}

            # Get cost breakdown by agent
            agent_costs = await db.fetch_all(
                """
                SELECT agent_id, SUM(cost_usd) as total_cost, SUM(tokens_input + tokens_output) as total_tokens
                FROM messages
                WHERE session_id = $1 AND agent_id IS NOT NULL
                GROUP BY agent_id
                """,
                session_id
            )

            # Get cost breakdown by model
            model_costs = await db.fetch_all(
                """
                SELECT model_used, SUM(cost_usd) as total_cost, COUNT(*) as message_count
                FROM messages
                WHERE session_id = $1 AND model_used IS NOT NULL
                GROUP BY model_used
                """,
                session_id
            )

            return {
                "session_id": session_id,
                "total_cost_usd": float(session_info["total_cost_usd"] or 0),
                "total_tokens": session_info["total_tokens"] or 0,
                "total_messages": session_info["total_messages"] or 0,
                "cost_per_message": (
                    float(session_info["total_cost_usd"] or 0) / session_info["total_messages"]
                    if session_info["total_messages"] > 0 else 0
                ),
                "cost_per_token": (
                    float(session_info["total_cost_usd"] or 0) / session_info["total_tokens"]
                    if session_info["total_tokens"] > 0 else 0
                ),
                "agent_breakdown": [
                    {
                        "agent_id": row["agent_id"],
                        "total_cost_usd": float(row["total_cost"] or 0),
                        "total_tokens": row["total_tokens"] or 0
                    }
                    for row in agent_costs
                ],
                "model_breakdown": [
                    {
                        "model": row["model_used"],
                        "total_cost_usd": float(row["total_cost"] or 0),
                        "message_count": row["message_count"]
                    }
                    for row in model_costs
                ]
            }

        except Exception as e:
            logger.error(f"Failed to get cost summary for session {session_id}: {e}")
            return {"error": str(e)}

    async def list_sessions(
        self,
        status: Optional[SessionStatus] = None,
        session_type: Optional[SessionType] = None,
        agent_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List sessions with optional filters.

        Args:
            status: Filter by status
            session_type: Filter by type
            agent_id: Filter by agent involvement
            limit: Maximum sessions
            offset: Offset for pagination

        Returns:
            List of session summaries
        """
        try:
            # Build query parts - use explicit string concatenation to avoid f-string issues
            where_parts = []
            params = []
            param_count = 0

            if status:
                param_count += 1
                where_parts.append("status = $" + str(param_count))
                params.append(status.value)

            if session_type:
                param_count += 1
                where_parts.append("session_type = $" + str(param_count))
                params.append(session_type.value)

            if agent_id:
                param_count += 1
                where_parts.append("$" + str(param_count) + " = ANY(agents_involved)")
                params.append(agent_id)

            # Build WHERE clause
            where_clause = ""
            if where_parts:
                where_clause = "WHERE " + " AND ".join(where_parts)

            # Add pagination parameters
            param_count += 1
            limit_param = "$" + str(param_count)
            param_count += 1
            offset_param = "$" + str(param_count)
            params.extend([limit, offset])

            # Construct final query using string concatenation
            query = """
                SELECT id, session_type, title, summary, primary_agent_id,
                       agents_involved, total_messages, total_tokens,
                       total_cost_usd, status, started_at, last_message_at,
                       ended_at, metadata
                FROM sessions
            """ + where_clause + """
                ORDER BY last_message_at DESC
                LIMIT """ + limit_param + """ OFFSET """ + offset_param

            # Debug logging to see the actual SQL
            logger.debug(f"list_sessions SQL: {query}")
            logger.debug(f"list_sessions params: {params}")

            rows = await db.fetch_all(query, *params)

            sessions = []
            for row in rows:
                # Convert metadata from string to dict if needed
                metadata = row["metadata"]
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata) if metadata else {}
                    except json.JSONDecodeError:
                        metadata = {}

                # Ensure agents_involved is a list
                agents_involved = row["agents_involved"] or []

                session = {
                    "id": row["id"],
                    "session_type": row["session_type"],
                    "title": row["title"] or "",
                    "summary": row["summary"],
                    "primary_agent_id": row["primary_agent_id"],
                    "agents_involved": agents_involved,
                    "total_messages": row["total_messages"],
                    "total_tokens": row["total_tokens"],
                    "total_cost_usd": float(row["total_cost_usd"] or 0),
                    "status": row["status"],
                    "started_at": row["started_at"],
                    "last_message_at": row["last_message_at"],
                    "ended_at": row["ended_at"],
                    "metadata": metadata
                }
                sessions.append(session)

            return sessions

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    # ============ Internal Methods ============

    async def _load_active_sessions(self) -> None:
        """Load active sessions from database."""
        try:
            rows = await db.fetch_all(
                """
                SELECT id, session_type, title, summary, primary_agent_id,
                       agents_involved, total_messages, total_tokens,
                       total_cost_usd, status, started_at, last_message_at,
                       metadata
                FROM sessions
                WHERE status = 'active'
                """
            )

            for row in rows:
                session_id = row["id"]

                # Create config from metadata
                metadata = row["metadata"] or {}
                config = SessionConfig(
                    session_type=SessionType(row["session_type"]),
                    metadata=metadata
                )

                self.active_sessions[session_id] = {
                    "id": session_id,
                    "title": row["title"],
                    "type": row["session_type"],
                    "primary_agent_id": row["primary_agent_id"],
                    "agents_involved": row["agents_involved"],
                    "config": config,
                    "message_count": row["total_messages"],
                    "total_tokens": row["total_tokens"],
                    "total_cost_usd": float(row["total_cost_usd"] or 0),
                    "created_at": row["started_at"],
                    "last_message_at": row["last_message_at"],
                    "status": row["status"],
                    "metadata": metadata
                }

                # Create lock for session
                self.session_locks[session_id] = asyncio.Lock()

            logger.info(f"Loaded {len(rows)} active sessions from database")

        except Exception as e:
            logger.error(f"Failed to load active sessions: {e}")

    async def _load_session_from_db(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session from database."""
        try:
            row = await db.fetch_one(
                """
                SELECT id, session_type, title, summary, primary_agent_id,
                       agents_involved, total_messages, total_tokens,
                       total_cost_usd, status, started_at, last_message_at,
                       ended_at, metadata
                FROM sessions
                WHERE id = $1
                """,
                session_id
            )

            if not row:
                return None

            # Convert metadata from string to dict if needed (same as list_sessions)
            metadata = row["metadata"]
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata) if metadata else {}
                except json.JSONDecodeError:
                    metadata = {}

            # Ensure metadata is a dict
            if not isinstance(metadata, dict):
                metadata = {}

            # Ensure agents_involved is a list
            agents_involved = row["agents_involved"] or []

            return {
                "id": row["id"],
                "session_type": row["session_type"],
                "title": row["title"] or "",
                "summary": row["summary"],
                "primary_agent_id": row["primary_agent_id"],
                "agents_involved": agents_involved,
                "total_messages": row["total_messages"],
                "total_tokens": row["total_tokens"],
                "total_cost_usd": float(row["total_cost_usd"] or 0),
                "status": row["status"],
                "started_at": row["started_at"],
                "last_message_at": row["last_message_at"],
                "ended_at": row["ended_at"],
                "metadata": metadata
            }

        except Exception as e:
            logger.error(f"Failed to load session {session_id} from database: {e}")
            return None

    async def _save_session_states(self) -> None:
        """Save session states to database."""
        for session_id, session in self.active_sessions.items():
            try:
                await db.execute(
                    """
                    UPDATE sessions SET
                        last_message_at = $2,
                        total_messages = $3,
                        total_tokens = $4,
                        total_cost_usd = $5,
                        agents_involved = $6,
                        updated_at = NOW()
                    WHERE id = $1
                    """,
                    session_id,
                    session["last_message_at"],
                    session["message_count"],
                    session["total_tokens"],
                    session["total_cost_usd"],
                    session["agents_involved"]
                )
            except Exception as e:
                logger.error(f"Failed to save session {session_id} state: {e}")

    async def _run_cleanup(self) -> None:
        """Run periodic session cleanup."""
        while True:
            try:
                # Wait before next cleanup
                await asyncio.sleep(300)  # Run every 5 minutes

                # Check for expired sessions
                await self._cleanup_expired_sessions()

                # Archive old completed sessions
                await self._archive_old_sessions()

            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def _cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions."""
        expired_sessions = []

        for session_id, session in self.active_sessions.items():
            config = session["config"]
            created_at = session["created_at"]

            if not isinstance(created_at, datetime):
                continue

            # Check if session has exceeded max duration
            max_duration = timedelta(hours=config.max_duration_hours)
            if datetime.now() - created_at > max_duration:
                expired_sessions.append(session_id)

            # Check if session has exceeded max messages
            if config.max_messages > 0 and session["message_count"] > config.max_messages:
                expired_sessions.append(session_id)

        # End expired sessions
        for session_id in expired_sessions:
            logger.info(f"Ending expired session: {session_id}")
            await self.end_session(
                session_id,
                status=SessionStatus.COMPLETED,
                summary="Session expired (max duration or messages exceeded)"
            )

    async def _archive_old_sessions(self) -> None:
        """Archive old completed sessions."""
        try:
            # Archive sessions completed more than 7 days ago
            result = await db.execute(
                """
                UPDATE sessions
                SET status = 'archived'
                WHERE status = 'completed'
                  AND ended_at < NOW() - INTERVAL '7 days'
                """
            )

            archived_count = int(result.split()[-1]) if "UPDATE" in result else 0
            if archived_count > 0:
                logger.info(f"Archived {archived_count} old sessions")

        except Exception as e:
            logger.error(f"Failed to archive old sessions: {e}")

    async def _generate_session_summary(self, session_id: str) -> None:
        """Generate AI summary for a completed session."""
        try:
            messages = await self.get_session_messages(session_id, limit=50)
            if not messages:
                return

            # Prepare conversation text for AI summarization
            conversation_text = ""
            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                # Truncate very long messages
                if len(content) > 500:
                    content = content[:500] + "..."
                conversation_text += f"{role}: {content}\n\n"

            # Get session metadata for context
            session = await self.get_session(session_id)
            if not session:
                return

            session_type = session.get("session_type", "chat")
            primary_agent = session.get("primary_agent_id", "unknown")

            # Create AI prompt for summarization
            prompt = f"""Please summarize the following {session_type} session with agent {primary_agent}.

Conversation:
{conversation_text}

Please provide a concise summary (2-3 sentences) that captures:
1. The main topic or purpose of the session
2. Key decisions or outcomes
3. Any important actions or next steps

Summary:"""

            # Use AI to generate summary
            ai_response = await ai_request(
                task_type=TaskType.SUMMARIZATION,
                prompt=prompt,
                max_tokens=200,
                temperature=0.3
            )

            summary = ai_response.get("content", "").strip()
            if not summary:
                # Fallback to basic summary if AI fails
                role_counts = {}
                for msg in messages:
                    role = msg["role"]
                    role_counts[role] = role_counts.get(role, 0) + 1
                summary = f"Session with {len(messages)} messages "
                summary += f"({', '.join(f'{count} {role}' for role, count in role_counts.items())})"

            # Store summary in session
            await self.update_session(session_id, summary=summary)

            # Also store summary in memory system for future reference
            try:
                from ..agents.memory import memory_system, MemoryType
                await memory_system.store_memory(
                    agent_id=primary_agent,
                    content=f"Session summary: {summary}",
                    memory_type=MemoryType.EPISODIC,
                    metadata={
                        "session_id": session_id,
                        "session_type": session_type,
                        "summary_source": "ai_generated"
                    }
                )
            except ImportError:
                logger.warning("Memory system not available for storing session summary")

            logger.info(f"Generated AI summary for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to generate session summary for {session_id}: {e}")
            # Fallback to basic summary on error
            try:
                messages = await self.get_session_messages(session_id, limit=20)
                if messages:
                    role_counts = {}
                    for msg in messages:
                        role = msg["role"]
                        role_counts[role] = role_counts.get(role, 0) + 1
                    summary = f"Session with {len(messages)} messages "
                    summary += f"({', '.join(f'{count} {role}' for role, count in role_counts.items())})"
                    await self.update_session(session_id, summary=summary)
            except Exception as fallback_error:
                logger.error(f"Fallback summary generation also failed: {fallback_error}")

    async def analyze_session_topics(self, session_id: str) -> List[str]:
        """Analyze session messages to extract key topics."""
        try:
            messages = await self.get_session_messages(session_id, limit=50)
            if not messages:
                return []

            # Combine message content for topic analysis
            conversation_text = "\n".join([
                f"{msg['role']}: {msg['content'][:200]}"
                for msg in messages if msg.get("content")
            ])

            prompt = f"""Analyze the following conversation and extract 3-5 key topics or themes.

Conversation:
{conversation_text}

Please list the key topics as a bulleted list. Focus on main subjects, tasks, or themes discussed.

Key topics:"""

            ai_response = await ai_request(
                task_type=TaskType.ANALYSIS,
                prompt=prompt,
                max_tokens=150,
                temperature=0.2
            )

            topics_text = ai_response.get("content", "").strip()
            # Parse bullet points or numbered lists
            topics = []
            for line in topics_text.split("\n"):
                line = line.strip()
                if line.startswith("- ") or line.startswith("* "):
                    topics.append(line[2:].strip())
                elif line.startswith("• "):
                    topics.append(line[2:].strip())
                elif line and not line.startswith("Key topics"):
                    topics.append(line)

            return topics[:5]  # Limit to top 5 topics

        except Exception as e:
            logger.error(f"Failed to analyze topics for session {session_id}: {e}")
            return []

    async def analyze_session_sentiment(self, session_id: str) -> Dict[str, Any]:
        """Analyze overall sentiment of a session."""
        try:
            messages = await self.get_session_messages(session_id, limit=50)
            if not messages:
                return {"sentiment": "neutral", "score": 0.0, "confidence": 0.0}

            # Combine message content for sentiment analysis
            conversation_text = "\n".join([
                msg["content"][:500] for msg in messages if msg.get("content")
            ])

            prompt = f"""Analyze the sentiment of the following conversation.

Conversation:
{conversation_text}

Please provide a sentiment analysis with:
1. Overall sentiment (positive, negative, neutral, mixed)
2. Sentiment score from -1.0 (very negative) to 1.0 (very positive)
3. Confidence score from 0.0 to 1.0

Respond in JSON format: {{"sentiment": "...", "score": 0.0, "confidence": 0.0}}"""

            ai_response = await ai_request(
                task_type=TaskType.ANALYSIS,
                prompt=prompt,
                max_tokens=200,
                temperature=0.1
            )

            sentiment_text = ai_response.get("content", "").strip()

            # Try to parse JSON response
            try:
                import json
                sentiment_data = json.loads(sentiment_text)
                return sentiment_data
            except json.JSONDecodeError:
                # Fallback: simple keyword detection
                text_lower = conversation_text.lower()
                positive_words = ["good", "great", "excellent", "thanks", "thank you", "helpful", "perfect"]
                negative_words = ["bad", "wrong", "error", "failed", "issue", "problem", "sorry"]

                positive_count = sum(1 for word in positive_words if word in text_lower)
                negative_count = sum(1 for word in negative_words if word in text_lower)

                if positive_count > negative_count:
                    return {"sentiment": "positive", "score": 0.5, "confidence": 0.7}
                elif negative_count > positive_count:
                    return {"sentiment": "negative", "score": -0.5, "confidence": 0.7}
                else:
                    return {"sentiment": "neutral", "score": 0.0, "confidence": 0.7}

        except Exception as e:
            logger.error(f"Failed to analyze sentiment for session {session_id}: {e}")
            return {"sentiment": "neutral", "score": 0.0, "confidence": 0.0}

    async def get_session_analytics(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive analytics for a session."""
        try:
            session = await self.get_session(session_id)
            if not session:
                return {}

            # Get basic session stats
            messages = await self.get_session_messages(session_id)
            total_messages = len(messages)

            # Count messages by role
            role_counts = {}
            for msg in messages:
                role = msg["role"]
                role_counts[role] = role_counts.get(role, 0) + 1

            # Get AI-powered analytics (async parallel)
            topics_task = self.analyze_session_topics(session_id)
            sentiment_task = self.analyze_session_sentiment(session_id)

            topics, sentiment = await asyncio.gather(
                topics_task,
                sentiment_task,
                return_exceptions=True
            )

            # Handle exceptions in parallel tasks
            if isinstance(topics, Exception):
                logger.error(f"Topic analysis failed: {topics}")
                topics = []
            if isinstance(sentiment, Exception):
                logger.error(f"Sentiment analysis failed: {sentiment}")
                sentiment = {"sentiment": "neutral", "score": 0.0, "confidence": 0.0}

            analytics = {
                "session_id": session_id,
                "total_messages": total_messages,
                "role_counts": role_counts,
                "duration_minutes": session.get("duration_minutes", 0),
                "total_cost_usd": session.get("total_cost_usd", 0.0),
                "total_tokens": session.get("total_tokens", 0),
                "topics": topics if not isinstance(topics, Exception) else [],
                "sentiment": sentiment if not isinstance(sentiment, Exception) else {"sentiment": "neutral", "score": 0.0, "confidence": 0.0},
                "agents_involved": session.get("agents_involved", []),
                "timestamp": datetime.now().isoformat()
            }

            return analytics

        except Exception as e:
            logger.error(f"Failed to get analytics for session {session_id}: {e}")
            return {}

    async def export_session(self, session_id: str, include_messages: bool = True, include_analytics: bool = True) -> Dict[str, Any]:
        """Export session data to JSON-serializable format."""
        try:
            session = await self.get_session(session_id)
            if not session:
                return {"error": f"Session {session_id} not found"}

            export_data = {
                "session_id": session_id,
                "metadata": {
                    "title": session.get("title", ""),
                    "session_type": session.get("session_type", ""),
                    "status": session.get("status", ""),
                    "primary_agent_id": session.get("primary_agent_id"),
                    "agents_involved": session.get("agents_involved", []),
                    "summary": session.get("summary", ""),
                    "started_at": session.get("started_at", ""),
                    "ended_at": session.get("ended_at"),
                    "duration_minutes": session.get("duration_minutes", 0),
                    "total_messages": session.get("total_messages", 0),
                    "total_tokens": session.get("total_tokens", 0),
                    "total_cost_usd": session.get("total_cost_usd", 0.0),
                    "metadata": session.get("metadata", {})
                }
            }

            if include_messages:
                messages = await self.get_session_messages(session_id, limit=1000)
                # Convert messages to serializable format
                serializable_messages = []
                for msg in messages:
                    serializable_msg = {
                        "id": msg.get("id"),
                        "role": msg.get("role"),
                        "content": msg.get("content", ""),
                        "agent_id": msg.get("agent_id"),
                        "parent_message_id": msg.get("parent_message_id"),
                        "tool_calls": msg.get("tool_calls"),
                        "tool_results": msg.get("tool_results"),
                        "tokens_input": msg.get("tokens_input"),
                        "tokens_output": msg.get("tokens_output"),
                        "cost_usd": msg.get("cost_usd"),
                        "model_used": msg.get("model_used"),
                        "latency_ms": msg.get("latency_ms"),
                        "created_at": msg.get("created_at")
                    }
                    serializable_messages.append(serializable_msg)
                export_data["messages"] = serializable_messages

            if include_analytics:
                analytics = await self.get_session_analytics(session_id)
                export_data["analytics"] = analytics

            export_data["export_timestamp"] = datetime.now().isoformat()
            export_data["export_version"] = "1.0"

            return export_data

        except Exception as e:
            logger.error(f"Failed to export session {session_id}: {e}")
            return {"error": str(e)}


# Global session manager instance
session_manager = SessionManager()


async def get_session_manager() -> SessionManager:
    """Dependency for FastAPI routes."""
    return session_manager