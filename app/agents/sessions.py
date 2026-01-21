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
        config: Optional[SessionConfig] = None
    ) -> str:
        """
        Create a new session.

        Args:
            title: Session title
            primary_agent_id: Primary agent for the session
            config: Session configuration

        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        session_config = config or SessionConfig()

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
                session_config.metadata or {}
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
            return self.active_sessions[session_id]

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
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
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
            param_index = 1

            if title is not None:
                updates.append(f"title = ${param_index}")
                params.append(title)
                session["title"] = title
                param_index += 1

            if summary is not None:
                updates.append(f"summary = ${param_index}")
                params.append(summary)
                param_index += 1

            if status is not None:
                updates.append(f"status = ${param_index}")
                params.append(status.value)
                session["status"] = status.value
                param_index += 1

                if status == SessionStatus.COMPLETED:
                    session["ended_at"] = datetime.now()
                    updates.append(f"ended_at = NOW()")

            if metadata is not None:
                # Merge with existing metadata
                current_metadata = session.get("metadata", {})
                merged_metadata = {**current_metadata, **metadata}
                updates.append(f"metadata = ${param_index}")
                params.append(merged_metadata)
                session["metadata"] = merged_metadata
                param_index += 1

            if not updates:
                return True  # Nothing to update

            # Add session ID as last parameter
            params.append(session_id)

            # Update database
            try:
                set_clause = ", ".join(updates)
                await db.execute(
                    f"UPDATE sessions SET {set_clause}, updated_at = NOW() WHERE id = ${param_index}",
                    *params
                )

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
            query = """
                SELECT id, session_type, title, summary, primary_agent_id,
                       agents_involved, total_messages, total_tokens,
                       total_cost_usd, status, started_at, last_message_at,
                       ended_at, metadata
                FROM sessions
                WHERE 1=1
            """
            params = []
            param_index = 1

            if status:
                query += f" AND status = ${param_index}"
                params.append(status.value)
                param_index += 1

            if session_type:
                query += f" AND session_type = ${param_index}"
                params.append(session_type.value)
                param_index += 1

            if agent_id:
                query += f" AND $${param_index} = ANY(agents_involved)"
                params.append(agent_id)
                param_index += 1

            query += f" ORDER BY last_message_at DESC LIMIT ${param_index} OFFSET $${param_index + 1}"
            params.extend([limit, offset])

            rows = await db.fetch_all(query, *params)

            sessions = []
            for row in rows:
                session = {
                    "id": row["id"],
                    "type": row["session_type"],
                    "title": row["title"],
                    "summary": row["summary"],
                    "primary_agent_id": row["primary_agent_id"],
                    "agents_involved": row["agents_involved"],
                    "total_messages": row["total_messages"],
                    "total_tokens": row["total_tokens"],
                    "total_cost_usd": float(row["total_cost_usd"] or 0),
                    "status": row["status"],
                    "started_at": row["started_at"].isoformat() if row["started_at"] else None,
                    "last_message_at": row["last_message_at"].isoformat() if row["last_message_at"] else None,
                    "ended_at": row["ended_at"].isoformat() if row["ended_at"] else None,
                    "metadata": row["metadata"]
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

            # Create config from metadata
            metadata = row["metadata"] or {}
            config = SessionConfig(
                session_type=SessionType(row["session_type"]),
                metadata=metadata
            )

            return {
                "id": row["id"],
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
                "ended_at": row["ended_at"],
                "status": row["status"],
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
        # TODO: Implement AI-powered session summarization
        # For now, generate basic summary
        try:
            messages = await self.get_session_messages(session_id, limit=20)
            if not messages:
                return

            # Count messages by role
            role_counts = {}
            for msg in messages:
                role = msg["role"]
                role_counts[role] = role_counts.get(role, 0) + 1

            summary = f"Session with {len(messages)} messages "
            summary += f"({', '.join(f'{count} {role}' for role, count in role_counts.items())})"

            await self.update_session(session_id, summary=summary)

        except Exception as e:
            logger.error(f"Failed to generate session summary for {session_id}: {e}")


# Global session manager instance
session_manager = SessionManager()


async def get_session_manager() -> SessionManager:
    """Dependency for FastAPI routes."""
    return session_manager