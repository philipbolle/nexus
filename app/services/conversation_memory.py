"""
NEXUS Conversation Memory Service
Bridge between chat system and memory system for long-term conversation memory.

Features:
1. Stores chat exchanges as episodic memories in vector database
2. Enables semantic search across all past conversations
3. Provides conversation context retrieval (20+ exchanges instead of 3)
4. Maintains cross-session conversation memory
"""

import logging
import asyncio
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..database import db
from ..agents.memory import (
    MemorySystem, MemoryType, MemoryQuery, MemoryResult,
    memory_system as global_memory_system,
    get_memory_system
)
from ..services.embeddings import get_embedding

logger = logging.getLogger(__name__)


@dataclass
class ConversationMemoryConfig:
    """Configuration for conversation memory service."""

    # Memory storage settings
    agent_id: str = "chat_agent"  # Default agent ID for chat memories
    memory_type: MemoryType = MemoryType.EPISODIC
    default_tags: List[str] = None  # Will be initialized

    # Context retrieval settings
    max_exchanges: int = 20  # Increased from 3 to 20
    min_similarity: float = 0.75  # Minimum similarity for semantic search
    max_memories_per_query: int = 5  # Max memories to retrieve per query

    # Memory consolidation settings
    enable_consolidation: bool = False  # Future feature

    def __post_init__(self):
        if self.default_tags is None:
            self.default_tags = ["conversation", "chat", "intelligent"]


class ConversationMemoryService:
    """Service for managing conversation memory using the memory system."""

    def __init__(self, config: Optional[ConversationMemoryConfig] = None):
        self.config = config or ConversationMemoryConfig()
        self._memory_system = None
        self._initialized = False
        self._init_lock = asyncio.Lock()

    def _string_to_uuid(self, id_string: str) -> str:
        """Convert any string to UUID v5 for database compatibility."""
        try:
            # Check if already a valid UUID
            uuid_obj = uuid.UUID(id_string)
            return str(uuid_obj)
        except ValueError:
            # Convert string to deterministic UUID v5 using DNS namespace
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, id_string))

    async def _ensure_initialized(self) -> None:
        """Lazy initialization of memory system."""
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return

            logger.info("Initializing conversation memory service...")
            self._memory_system = await get_memory_system()

            # Initialize memory system if needed
            if hasattr(self._memory_system, '_initialized') and not self._memory_system._initialized:
                await self._memory_system.initialize()

            self._initialized = True
            logger.info("Conversation memory service initialized")

    async def store_chat_exchange(
        self,
        session_id: str,
        user_message: str,
        ai_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a chat exchange as episodic memory.

        Returns memory ID if successful, empty string otherwise.
        """
        try:
            await self._ensure_initialized()

            # Combine user and AI messages
            content = f"User: {user_message}\nNEXUS: {ai_response}"

            # Extract basic topic from user message (simple keyword extraction)
            # TODO: Replace with AI-powered topic extraction in Phase 2
            topic_tags = self._extract_topic_tags(user_message)
            all_tags = self.config.default_tags + topic_tags

            # Prepare metadata
            memory_metadata = {
                "session_id": session_id,
                "user_message_preview": user_message[:100],
                "timestamp": datetime.utcnow().isoformat(),
                "source": "chat_exchange"
            }
            if metadata:
                memory_metadata.update(metadata)

            # Store as episodic memory
            memory_id = await self._memory_system.store_memory(
                agent_id=self._string_to_uuid(self.config.agent_id),
                content=content,
                memory_type=self.config.memory_type,
                importance_score=self._calculate_importance(user_message, ai_response),
                strength_score=1.0,
                tags=all_tags,
                metadata=memory_metadata,
                source_type="conversation",
                source_id=self._string_to_uuid(session_id)
            )

            logger.debug(f"Stored chat exchange as memory {memory_id[:8]}... for session {session_id[:8]}...")
            return memory_id

        except Exception as e:
            logger.error(f"Failed to store chat exchange as memory: {e}")
            return ""

    async def retrieve_relevant_memories(
        self,
        query: str,
        session_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[MemoryResult]:
        """
        Retrieve relevant past conversations using semantic search.

        Args:
            query: User query to find relevant memories
            session_id: Optional session ID to filter by session
            limit: Maximum number of memories to return

        Returns:
            List of memory results sorted by relevance
        """
        try:
            await self._ensure_initialized()

            if limit is None:
                limit = self.config.max_memories_per_query

            # Build tags filter
            tags = self.config.default_tags.copy()

            # Build metadata filter for session if provided
            metadata_filter = None
            if session_id:
                metadata_filter = {"session_id": session_id}

            # Create memory query
            memory_query = MemoryQuery(
                query_text=query,
                memory_types=[self.config.memory_type],
                agent_id=self._string_to_uuid(self.config.agent_id),
                limit=limit,
                min_similarity=self.config.min_similarity,
                tags=tags,
                recency_weight=0.5  # Weight recent memories more
            )

            # Search memories
            memories = await self._memory_system.search_memories(memory_query)

            # Apply additional filtering if needed
            if metadata_filter and memories:
                filtered_memories = []
                for memory in memories:
                    memory_metadata = memory.metadata or {}
                    matches = True
                    for key, value in metadata_filter.items():
                        if memory_metadata.get(key) != value:
                            matches = False
                            break
                    if matches:
                        filtered_memories.append(memory)
                memories = filtered_memories

            logger.debug(f"Retrieved {len(memories)} relevant memories for query: {query[:100]}...")
            return memories

        except Exception as e:
            logger.error(f"Failed to retrieve relevant memories: {e}")
            return []

    async def get_conversation_context(
        self,
        session_id: str,
        max_exchanges: Optional[int] = None
    ) -> str:
        """
        Get conversation context for a session.

        Returns formatted conversation history including recent exchanges
        and semantically relevant past conversations.
        """
        try:
            await self._ensure_initialized()

            if max_exchanges is None:
                max_exchanges = self.config.max_exchanges

            # Get recent messages from database (existing system)
            recent_messages = await self._get_recent_messages(session_id, max_exchanges)

            # Format conversation context
            context_parts = []

            if recent_messages:
                context_parts.append("RECENT CONVERSATION:")
                for i, (role, content) in enumerate(recent_messages, 1):
                    speaker = "USER" if role == "user" else "NEXUS"
                    context_parts.append(f"{i}. {speaker}: {content}")
                context_parts.append("")  # Empty line for separation

            # Get semantically relevant memories from this session
            if recent_messages and len(recent_messages) > 0:
                # Use the last user message as query for relevant memories
                last_user_message = None
                for role, content in reversed(recent_messages):
                    if role == "user":
                        last_user_message = content
                        break

                if last_user_message:
                    relevant_memories = await self.retrieve_relevant_memories(
                        query=last_user_message,
                        session_id=session_id,
                        limit=3  # Get top 3 relevant memories from this session
                    )

                    if relevant_memories:
                        context_parts.append("RELEVANT PAST EXCHANGES FROM THIS CONVERSATION:")
                        for i, memory in enumerate(relevant_memories[:3], 1):
                            # Extract just the content (already formatted as "User: ...\nNEXUS: ...")
                            context_parts.append(f"{i}. {memory.content}")
                        context_parts.append("")

            if context_parts:
                return "\n".join(context_parts)
            return ""

        except Exception as e:
            logger.error(f"Failed to get conversation context: {e}")
            return ""

    async def format_memories_for_context(self, memories: List[MemoryResult]) -> str:
        """
        Format memory results for AI context.

        Returns formatted string suitable for inclusion in AI prompts.
        """
        if not memories:
            return ""

        formatted = ["RELEVANT PAST CONVERSATIONS:"]
        for i, memory in enumerate(memories, 1):
            # Extract metadata for context
            metadata = memory.metadata or {}
            session_preview = metadata.get("session_id", "unknown")[:8]
            timestamp = metadata.get("timestamp", "")

            # Format timestamp if available
            time_str = ""
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = f" ({dt.strftime('%Y-%m-%d %H:%M')})"
                except:
                    pass

            formatted.append(f"{i}. [Session {session_preview}...{time_str}]")
            formatted.append(f"   {memory.content}")
            formatted.append("")  # Empty line between memories

        return "\n".join(formatted)

    # ============================================================================
    # Helper Methods
    # ============================================================================

    async def _get_recent_messages(
        self,
        session_id: str,
        limit: int
    ) -> List[Tuple[str, str]]:
        """Get recent messages from database for a session."""
        try:
            rows = await db.fetch_all(
                """
                SELECT role, content
                FROM messages
                WHERE session_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                session_id, limit * 2  # Get extra because we filter pairs
            )

            # Convert to list of (role, content) in chronological order
            messages = [(row["role"], row["content"]) for row in rows]
            messages.reverse()  # Oldest first

            return messages

        except Exception as e:
            logger.error(f"Failed to get recent messages: {e}")
            return []

    def _extract_topic_tags(self, message: str) -> List[str]:
        """Extract simple topic tags from message (keyword-based)."""
        message_lower = message.lower()
        tags = []

        # Simple keyword matching (to be replaced with AI in Phase 2)
        topic_keywords = {
            "finance": ["money", "budget", "debt", "spent", "expense", "finance", "cost"],
            "email": ["email", "inbox", "message", "sender", "gmail", "icloud"],
            "programming": ["code", "python", "program", "function", "bug", "error"],
            "system": ["status", "health", "service", "container", "docker"],
            "personal": ["how are you", "hello", "hi", "thanks", "thank you"],
            "automation": ["workflow", "n8n", "automate", "script", "task"],
            "home": ["home assistant", "light", "device", "temperature", "thermostat"],
        }

        for topic, keywords in topic_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                tags.append(topic)

        # Add a general tag if no specific topics found
        if not tags:
            tags.append("general")

        return tags

    def _calculate_importance(self, user_message: str, ai_response: str) -> float:
        """
        Calculate importance score for a conversation exchange.

        Simple heuristic based on message length and content.
        TODO: Replace with AI-powered importance scoring in Phase 2.
        """
        # Longer messages might be more important
        length_score = min(len(user_message) / 500, 1.0)  # Cap at 1.0

        # Check for question marks (questions might be important)
        question_score = 0.3 if "?" in user_message else 0.0

        # Check for financial keywords (financial conversations are important)
        financial_keywords = ["budget", "debt", "money", "spent", "expense", "cost"]
        financial_score = 0.4 if any(keyword in user_message.lower() for keyword in financial_keywords) else 0.0

        # Base importance
        base_importance = 0.5

        # Combine scores (weighted)
        importance = base_importance + (length_score * 0.2) + question_score + financial_score

        # Cap at 0.95 (leave room for truly important memories)
        return min(importance, 0.95)


# Global instance for easy access
_conversation_memory_service = ConversationMemoryService()


async def get_conversation_memory_service() -> ConversationMemoryService:
    """Dependency injection function for FastAPI routes."""
    return _conversation_memory_service