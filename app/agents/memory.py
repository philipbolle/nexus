"""
NEXUS Multi-Agent Framework - Memory System

Shared vector memory system for agents with semantic search, memory consolidation,
and namespace isolation. Integrates with ChromaDB and PostgreSQL memory tables.
"""

import asyncio
import logging
import uuid
import json
from typing import Dict, Any, List, Optional, Tuple, Set
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..database import db
from ..services.embeddings import get_embedding, cosine_similarity
from ..config import settings

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types of memories stored in the system."""
    SEMANTIC = "semantic"    # Facts and knowledge
    EPISODIC = "episodic"    # Experiences and events
    PROCEDURAL = "procedural"  # Skills and how-to knowledge
    WORKING = "working"      # Short-term/context memory


class MemoryConsolidationJobType(Enum):
    """Types of memory consolidation jobs."""
    SUMMARIZE = "summarize"      # Summarize similar memories
    CLUSTER = "cluster"          # Cluster related memories
    PRUNE = "prune"              # Remove low-importance memories
    DECAY = "decay"              # Reduce strength of old memories
    INTEGRATE = "integrate"      # Integrate new with existing knowledge


@dataclass
class MemoryQuery:
    """Query for searching memories."""

    query_text: str
    memory_types: Optional[List[MemoryType]] = None
    agent_id: Optional[str] = None
    limit: int = 10
    min_similarity: float = 0.7
    tags: Optional[List[str]] = None
    recency_weight: float = 0.3  # How much to weight recent memories


@dataclass
class MemoryResult:
    """Result of a memory search."""

    memory_id: str
    content: str
    memory_type: MemoryType
    similarity: float
    importance_score: float
    strength_score: float
    last_accessed_at: Optional[datetime]
    tags: List[str]
    metadata: Dict[str, Any]


@dataclass
class MemoryBlock:
    """In-context memory block for agents."""

    block_label: str  # 'human', 'persona', 'task', 'context'
    content: str
    char_limit: int = 2000
    priority: int = 50  # Lower = more important
    version: int = 1


class MemorySystem:
    """
    Central memory system for the NEXUS multi-agent framework.

    Provides:
    - Vector-based semantic memory storage and retrieval
    - Memory consolidation and pruning
    - Agent-specific memory namespaces
    - Memory block management for in-context memory
    """

    def __init__(self):
        """Initialize the memory system."""
        self.agent_memory_blocks: Dict[str, Dict[str, MemoryBlock]] = {}  # agent_id -> {block_label: block}
        self.memory_cache: Dict[str, MemoryResult] = {}
        self._initialized = False
        self.chroma_client: Optional[chromadb.ClientAPI] = None
        self.chroma_collections: Dict[str, chromadb.Collection] = {}
        self.use_chromadb: bool = True  # Flag to enable/disable ChromaDB

    async def _init_chromadb_client(self) -> None:
        """Initialize ChromaDB client and create collections."""
        try:
            chroma_settings = settings.chromadb_settings
            host = chroma_settings["host"]
            auth_token = chroma_settings["auth_token"]
            collection_prefix = chroma_settings["collection_prefix"]

            # Configure ChromaDB client
            chroma_config = Settings(
                chroma_server_host=host,
                chroma_server_http_port=8000,
                chroma_server_ssl_enabled=False,
                chroma_server_auth_token=auth_token if auth_token else None,
            )

            self.chroma_client = chromadb.Client(chroma_config)

            # Create collections for each memory type
            for memory_type in MemoryType:
                collection_name = f"{collection_prefix}{memory_type.value}"
                # Get or create collection
                collection = self.chroma_client.get_or_create_collection(
                    name=collection_name,
                    metadata={"memory_type": memory_type.value}
                )
                self.chroma_collections[memory_type.value] = collection

            logger.info(f"Initialized ChromaDB client with {len(self.chroma_collections)} collections")

        except Exception as e:
            logger.warning(f"Failed to initialize ChromaDB client: {e}. Falling back to PostgreSQL-only mode.")
            self.use_chromadb = False
            self.chroma_client = None

    async def _store_memory_in_chromadb(
        self,
        memory_id: str,
        agent_id: str,
        content: str,
        memory_type: MemoryType,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store memory vector in ChromaDB."""
        if not self.use_chromadb or not self.chroma_client:
            return False

        try:
            collection = self.chroma_collections.get(memory_type.value)
            if not collection:
                logger.warning(f"No ChromaDB collection for memory type {memory_type.value}")
                return False

            # Prepare metadata for ChromaDB
            chroma_metadata = {
                "memory_id": memory_id,
                "agent_id": agent_id,
                "memory_type": memory_type.value,
                "timestamp": datetime.now().isoformat()
            }
            if metadata:
                # Filter metadata to avoid complex types
                for key, value in metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        chroma_metadata[key] = str(value)
                    elif isinstance(value, list) and all(isinstance(item, (str, int, float, bool)) for item in value):
                        chroma_metadata[key] = json.dumps(value)

            # Add to ChromaDB collection
            collection.add(
                ids=[memory_id],
                embeddings=[embedding],
                metadatas=[chroma_metadata],
                documents=[content[:1000]]  # Store truncated content
            )

            logger.debug(f"Stored memory {memory_id} in ChromaDB collection {memory_type.value}")
            return True

        except Exception as e:
            logger.warning(f"Failed to store memory {memory_id} in ChromaDB: {e}")
            return False

    async def _search_memories_in_chromadb(
        self,
        query_embedding: List[float],
        memory_types: Optional[List[MemoryType]] = None,
        agent_id: Optional[str] = None,
        limit: int = 10,
        min_similarity: float = 0.7
    ) -> List[Tuple[str, float]]:
        """Search memories in ChromaDB using vector similarity."""
        if not self.use_chromadb or not self.chroma_client:
            return []

        results = []
        try:
            # Determine which collections to search
            collections_to_search = []
            if memory_types:
                for mt in memory_types:
                    collection = self.chroma_collections.get(mt.value)
                    if collection:
                        collections_to_search.append(collection)
            else:
                # Search all collections
                collections_to_search = list(self.chroma_collections.values())

            for collection in collections_to_search:
                # Build ChromaDB query filters
                where = {}
                if agent_id:
                    where["agent_id"] = agent_id

                # Query collection
                query_results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit,
                    where=where if where else None,
                    include=["metadatas", "distances", "documents"]
                )

                # Process results
                if query_results and query_results.get("ids"):
                    for i, memory_id in enumerate(query_results["ids"][0]):
                        distance = query_results["distances"][0][i]
                        similarity = 1.0 - distance  # Convert distance to similarity

                        if similarity >= min_similarity:
                            results.append((memory_id, similarity))

            # Sort by similarity and limit
            results.sort(key=lambda x: x[1], reverse=True)
            results = results[:limit]

            logger.debug(f"ChromaDB search found {len(results)} results")
            return results

        except Exception as e:
            logger.warning(f"ChromaDB search failed: {e}")
            return []

    async def initialize(self) -> None:
        """
        Initialize the memory system.

        Loads memory blocks from database and warms up cache.
        """
        if self._initialized:
            return

        logger.info("Initializing memory system...")

        try:
            # Load memory blocks for active agents
            await self._load_memory_blocks()

            # Initialize ChromaDB client
            await self._init_chromadb_client()

            # Start background consolidation job
            asyncio.create_task(self._run_consolidation_jobs())

            self._initialized = True
            logger.info("Memory system initialized")

        except Exception as e:
            logger.error(f"Failed to initialize memory system: {e}")
            raise

    async def store_memory(
        self,
        agent_id: str,
        content: str,
        memory_type: MemoryType = MemoryType.SEMANTIC,
        importance_score: float = 0.5,
        strength_score: float = 1.0,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None
    ) -> str:
        """
        Store a memory for an agent.

        Args:
            agent_id: Agent ID
            content: Memory content
            memory_type: Type of memory
            importance_score: Importance score (0-1)
            strength_score: Strength score (0-1)
            tags: Memory tags for organization
            metadata: Additional metadata
            source_type: Source of memory (conversation, document, etc.)
            source_id: Source ID

        Returns:
            Memory ID
        """
        memory_id = str(uuid.uuid4())

        # Generate embedding for semantic search
        embedding = get_embedding(content)
        embedding_list = embedding.tolist() if hasattr(embedding, 'tolist') else embedding

        logger.debug(f"Storing {memory_type.value} memory for agent {agent_id}: {content[:100]}...")

        try:
            # Store in ChromaDB (if enabled)
            if self.use_chromadb:
                try:
                    await self._store_memory_in_chromadb(
                        memory_id=memory_id,
                        agent_id=agent_id,
                        content=content,
                        memory_type=memory_type,
                        embedding=embedding_list,
                        metadata=metadata
                    )
                except Exception as e:
                    logger.warning(f"ChromaDB storage failed for memory {memory_id}: {e}")
                    # Continue with PostgreSQL storage

            # Store in PostgreSQL with pgvector
            await db.execute(
                """
                INSERT INTO memories
                (id, agent_id, memory_type, content, content_embedding,
                 importance_score, strength_score, source_type, source_id,
                 tags, metadata, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                        CASE WHEN $7 < 0.3 THEN NOW() + INTERVAL '7 days'
                             ELSE NULL END)
                """,
                memory_id,
                agent_id,
                memory_type.value,
                content,
                embedding_list,
                importance_score,
                strength_score,
                source_type,
                source_id,
                tags or [],
                metadata or {}
            )

            # Create specific memory type record
            if memory_type == MemoryType.SEMANTIC:
                await self._store_semantic_memory(memory_id, content)
            elif memory_type == MemoryType.EPISODIC:
                await self._store_episodic_memory(memory_id, content, metadata)
            elif memory_type == MemoryType.PROCEDURAL:
                await self._store_procedural_memory(memory_id, content, metadata)

            # Update cache
            self.memory_cache[memory_id] = MemoryResult(
                memory_id=memory_id,
                content=content,
                memory_type=memory_type,
                similarity=1.0,
                importance_score=importance_score,
                strength_score=strength_score,
                last_accessed_at=datetime.now(),
                tags=tags or [],
                metadata=metadata or {}
            )

            logger.info(f"Stored memory {memory_id} for agent {agent_id}")
            return memory_id

        except Exception as e:
            logger.error(f"Failed to store memory for agent {agent_id}: {e}")
            raise

    async def get_memories(self, agent_id: str, memory_type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get memories for a specific agent.
        """
        try:
            # TODO: Implement proper memory retrieval
            logger.warning(f"get_memories called but not fully implemented for agent {agent_id}")
            return []
        except Exception as e:
            logger.error(f"Failed to get memories for agent {agent_id}: {e}")
            return []

    async def query_memory(self, agent_id: str, query_text: str, limit: int = 10, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Query agent memory with semantic search.
        """
        try:
            query = MemoryQuery(
                query_text=query_text,
                agent_id=agent_id,
                limit=limit,
                min_similarity=similarity_threshold
            )
            results = await self.search_memories(query)
            # Convert MemoryResult to dict
            memory_dicts = []
            for result in results:
                memory_dicts.append({
                    "id": result.memory_id,
                    "agent_id": agent_id,
                    "content": result.content,
                    "memory_type": result.memory_type.value,
                    "similarity": result.similarity,
                    "importance_score": result.importance_score,
                    "strength_score": result.strength_score,
                    "last_accessed_at": result.last_accessed_at,
                    "tags": result.tags,
                    "metadata": result.metadata
                })
            return memory_dicts
        except Exception as e:
            logger.error(f"Failed to query memory for agent {agent_id}: {e}")
            return []

    async def search_memories(self, query: MemoryQuery) -> List[MemoryResult]:
        """
        Search memories using semantic similarity.

        Args:
            query: Memory query parameters

        Returns:
            List of memory results sorted by relevance
        """
        logger.debug(f"Searching memories: {query.query_text[:100]}...")

        # Generate embedding for query
        query_embedding = get_embedding(query.query_text)
        query_embedding_list = query_embedding.tolist() if hasattr(query_embedding, 'tolist') else query_embedding

        memory_ids_from_chromadb = []
        chromadb_similarities = {}

        # Try ChromaDB search first if enabled
        if self.use_chromadb and self.chroma_client:
            try:
                chromadb_results = await self._search_memories_in_chromadb(
                    query_embedding=query_embedding_list,
                    memory_types=query.memory_types,
                    agent_id=query.agent_id,
                    limit=query.limit * 2,  # Get extra for filtering
                    min_similarity=query.min_similarity
                )

                for memory_id, similarity in chromadb_results:
                    memory_ids_from_chromadb.append(memory_id)
                    chromadb_similarities[memory_id] = similarity

                logger.debug(f"ChromaDB found {len(memory_ids_from_chromadb)} candidate memories")

            except Exception as e:
                logger.warning(f"ChromaDB search failed: {e}. Falling back to PostgreSQL.")

        # Fetch memory details from PostgreSQL
        results = []
        if memory_ids_from_chromadb:
            # Fetch details for memories found in ChromaDB
            rows = await db.fetch_all(
                """
                SELECT id, agent_id, memory_type, content, importance_score,
                       strength_score, last_accessed_at, tags, metadata
                FROM memories
                WHERE id = ANY($1)
                  AND (expires_at IS NULL OR expires_at > NOW())
                """,
                memory_ids_from_chromadb
            )

            # Convert to MemoryResult objects with ChromaDB similarity scores
            for row in rows:
                memory_id = row["id"]
                similarity = chromadb_similarities.get(memory_id, 0.5)

                # Apply recency weighting
                final_score = similarity
                if query.recency_weight > 0 and row["last_accessed_at"]:
                    hours_ago = (datetime.now() - row["last_accessed_at"]).total_seconds() / 3600
                    recency_factor = max(0, 1 - (hours_ago / 168))  # Decay over 1 week
                    final_score = (similarity * (1 - query.recency_weight) +
                                  recency_factor * query.recency_weight)

                # Apply additional filters (tags, etc.)
                if query.tags:
                    memory_tags = row["tags"] or []
                    if not any(tag in memory_tags for tag in query.tags):
                        continue  # Skip memories that don't match tag filter

                result = MemoryResult(
                    memory_id=memory_id,
                    content=row["content"],
                    memory_type=MemoryType(row["memory_type"]),
                    similarity=final_score,
                    importance_score=row["importance_score"],
                    strength_score=row["strength_score"],
                    last_accessed_at=row["last_accessed_at"],
                    tags=row["tags"],
                    metadata=row["metadata"]
                )
                results.append(result)

            # Sort by final score
            results.sort(key=lambda x: x.similarity, reverse=True)
            results = results[:query.limit]

        # Fallback to PostgreSQL-only search if ChromaDB didn't return enough results
        if len(results) < query.limit:
            logger.debug(f"ChromaDB returned insufficient results ({len(results)}), falling back to PostgreSQL")

            # Build SQL query for PostgreSQL fallback
            sql = """
                SELECT id, agent_id, memory_type, content, importance_score,
                       strength_score, last_accessed_at, tags, metadata,
                       content_embedding <=> $1 as similarity
                FROM memories
                WHERE 1=1
            """
            params = [query_embedding_list]
            param_index = 2

            # Apply filters
            if query.agent_id:
                sql += f" AND agent_id = ${param_index}"
                params.append(query.agent_id)
                param_index += 1

            if query.memory_types:
                type_values = [mt.value for mt in query.memory_types]
                sql += f" AND memory_type = ANY(${param_index})"
                params.append(type_values)
                param_index += 1

            if query.tags:
                sql += f" AND tags && ${param_index}"
                params.append(query.tags)
                param_index += 1

            # Add similarity threshold
            sql += f" AND (content_embedding <=> $1) <= (1 - ${param_index})"
            params.append(query.min_similarity)

            # Order by similarity and importance
            sql += f" ORDER BY similarity ASC, importance_score DESC LIMIT ${param_index}"
            params.append(query.limit)

            # Execute query
            rows = await db.fetch_all(sql, *params)

            # Convert to MemoryResult objects
            for row in rows:
                memory_id = row["id"]
                # Skip memories already included from ChromaDB
                if any(r.memory_id == memory_id for r in results):
                    continue

                similarity = 1.0 - float(row["similarity"])  # Convert distance to similarity

                # Apply recency weighting
                final_score = similarity
                if query.recency_weight > 0 and row["last_accessed_at"]:
                    hours_ago = (datetime.now() - row["last_accessed_at"]).total_seconds() / 3600
                    recency_factor = max(0, 1 - (hours_ago / 168))  # Decay over 1 week
                    final_score = (similarity * (1 - query.recency_weight) +
                                  recency_factor * query.recency_weight)

                result = MemoryResult(
                    memory_id=memory_id,
                    content=row["content"],
                    memory_type=MemoryType(row["memory_type"]),
                    similarity=final_score,
                    importance_score=row["importance_score"],
                    strength_score=row["strength_score"],
                    last_accessed_at=row["last_accessed_at"],
                    tags=row["tags"],
                    metadata=row["metadata"]
                )
                results.append(result)

            # Sort by final score
            results.sort(key=lambda x: x.similarity, reverse=True)
            results = results[:query.limit]

        # Update access times for retrieved memories
        if results:
            await self._update_access_times([r.memory_id for r in results])

        logger.info(f"Found {len(results)} memories for query")
        return results

    async def get_memory_block(
        self,
        agent_id: str,
        block_label: str
    ) -> Optional[MemoryBlock]:
        """
        Get an in-context memory block for an agent.

        Args:
            agent_id: Agent ID
            block_label: Block label ('human', 'persona', 'task', 'context')

        Returns:
            Memory block or None if not found
        """
        # Check cache first
        if agent_id in self.agent_memory_blocks:
            blocks = self.agent_memory_blocks[agent_id]
            if block_label in blocks:
                return blocks[block_label]

        # Load from database
        block = await self._load_memory_block_from_db(agent_id, block_label)
        if block:
            # Update cache
            if agent_id not in self.agent_memory_blocks:
                self.agent_memory_blocks[agent_id] = {}
            self.agent_memory_blocks[agent_id][block_label] = block

        return block

    async def update_memory_block(
        self,
        agent_id: str,
        block_label: str,
        content: str,
        char_limit: Optional[int] = None,
        priority: Optional[int] = None
    ) -> MemoryBlock:
        """
        Update or create a memory block for an agent.

        Args:
            agent_id: Agent ID
            block_label: Block label
            content: Block content
            char_limit: Character limit
            priority: Priority (lower = more important)

        Returns:
            Updated memory block
        """
        # Get existing block or create new
        existing = await self.get_memory_block(agent_id, block_label)

        if existing:
            # Update existing block
            updated = MemoryBlock(
                block_label=block_label,
                content=content[:char_limit or existing.char_limit],
                char_limit=char_limit or existing.char_limit,
                priority=priority or existing.priority,
                version=existing.version + 1
            )
        else:
            # Create new block
            updated = MemoryBlock(
                block_label=block_label,
                content=content[:char_limit or 2000],
                char_limit=char_limit or 2000,
                priority=priority or 50,
                version=1
            )

        # Store in database
        await self._store_memory_block_in_db(agent_id, updated)

        # Update cache
        if agent_id not in self.agent_memory_blocks:
            self.agent_memory_blocks[agent_id] = {}
        self.agent_memory_blocks[agent_id][block_label] = updated

        logger.debug(f"Updated memory block {block_label} for agent {agent_id}")
        return updated

    async def consolidate_memories(
        self,
        agent_id: Optional[str] = None,
        job_type: MemoryConsolidationJobType = MemoryConsolidationJobType.SUMMARIZE
    ) -> Dict[str, Any]:
        """
        Run memory consolidation job.

        Args:
            agent_id: Specific agent or None for all agents
            job_type: Type of consolidation job

        Returns:
            Job results
        """
        job_id = str(uuid.uuid4())
        logger.info(f"Starting memory consolidation job {job_id} ({job_type.value})")

        # Create job record
        await db.execute(
            """
            INSERT INTO memory_consolidation_jobs
            (id, agent_id, job_type, status, started_at)
            VALUES ($1, $2, $3, 'running', NOW())
            """,
            job_id,
            agent_id,
            job_type.value
        )

        try:
            # Execute consolidation based on job type
            if job_type == MemoryConsolidationJobType.SUMMARIZE:
                results = await self._consolidate_summarize(agent_id)
            elif job_type == MemoryConsolidationJobType.CLUSTER:
                results = await self._consolidate_cluster(agent_id)
            elif job_type == MemoryConsolidationJobType.PRUNE:
                results = await self._consolidate_prune(agent_id)
            elif job_type == MemoryConsolidationJobType.DECAY:
                results = await self._consolidate_decay(agent_id)
            elif job_type == MemoryConsolidationJobType.INTEGRATE:
                results = await self._consolidate_integrate(agent_id)
            else:
                raise ValueError(f"Unknown job type: {job_type}")

            # Update job record
            await db.execute(
                """
                UPDATE memory_consolidation_jobs SET
                    status = 'completed',
                    completed_at = NOW(),
                    memories_processed = $2,
                    memories_created = $3,
                    memories_archived = $4
                WHERE id = $1
                """,
                job_id,
                results.get("memories_processed", 0),
                results.get("memories_created", 0),
                results.get("memories_archived", 0)
            )

            logger.info(f"Memory consolidation job {job_id} completed: {results}")
            return {"job_id": job_id, **results}

        except Exception as e:
            logger.error(f"Memory consolidation job {job_id} failed: {e}")

            # Update job record with error
            await db.execute(
                """
                UPDATE memory_consolidation_jobs SET
                    status = 'error',
                    completed_at = NOW(),
                    error_message = $2
                WHERE id = $1
                """,
                job_id,
                str(e)
            )

            raise

    async def get_memory_stats(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get memory statistics.

        Args:
            agent_id: Specific agent or None for all agents

        Returns:
            Memory statistics
        """
        # Build query
        if agent_id:
            rows = await db.fetch_all(
                """
                SELECT memory_type, COUNT(*) as count,
                       AVG(importance_score) as avg_importance,
                       AVG(strength_score) as avg_strength
                FROM memories
                WHERE agent_id = $1 AND expires_at IS NULL
                GROUP BY memory_type
                """,
                agent_id
            )
        else:
            rows = await db.fetch_all(
                """
                SELECT memory_type, COUNT(*) as count,
                       AVG(importance_score) as avg_importance,
                       AVG(strength_score) as avg_strength
                FROM memories
                WHERE expires_at IS NULL
                GROUP BY memory_type
                """
            )

        stats = {
            "total_memories": 0,
            "by_type": {},
            "agent_id": agent_id
        }

        for row in rows:
            memory_type = row["memory_type"]
            count = row["count"]
            stats["by_type"][memory_type] = {
                "count": count,
                "avg_importance": float(row["avg_importance"] or 0),
                "avg_strength": float(row["avg_strength"] or 0)
            }
            stats["total_memories"] += count

        return stats

    async def forget_memory(self, memory_id: str, soft_delete: bool = True) -> bool:
        """
        Forget/delete a memory.

        Args:
            memory_id: Memory ID
            soft_delete: If True, mark as expired instead of deleting

        Returns:
            True if successful
        """
        try:
            if soft_delete:
                await db.execute(
                    """
                    UPDATE memories SET expires_at = NOW()
                    WHERE id = $1
                    """,
                    memory_id
                )
                logger.info(f"Soft-deleted memory {memory_id}")
            else:
                await db.execute(
                    "DELETE FROM memories WHERE id = $1",
                    memory_id
                )
                logger.info(f"Hard-deleted memory {memory_id}")

            # Remove from cache
            self.memory_cache.pop(memory_id, None)

            return True

        except Exception as e:
            logger.error(f"Failed to forget memory {memory_id}: {e}")
            return False

    # ============ Internal Methods ============

    async def _load_memory_blocks(self) -> None:
        """Load memory blocks from database."""
        try:
            rows = await db.fetch_all(
                """
                SELECT agent_id, block_label, content, char_limit, priority, version
                FROM memory_blocks
                WHERE is_active = true
                """
            )

            for row in rows:
                agent_id = row["agent_id"]
                block_label = row["block_label"]

                block = MemoryBlock(
                    block_label=block_label,
                    content=row["content"],
                    char_limit=row["char_limit"],
                    priority=row["priority"],
                    version=row["version"]
                )

                if agent_id not in self.agent_memory_blocks:
                    self.agent_memory_blocks[agent_id] = {}
                self.agent_memory_blocks[agent_id][block_label] = block

            logger.info(f"Loaded {len(rows)} memory blocks for {len(self.agent_memory_blocks)} agents")

        except Exception as e:
            logger.error(f"Failed to load memory blocks: {e}")

    async def _load_memory_block_from_db(
        self,
        agent_id: str,
        block_label: str
    ) -> Optional[MemoryBlock]:
        """Load memory block from database."""
        row = await db.fetch_one(
            """
            SELECT content, char_limit, priority, version
            FROM memory_blocks
            WHERE agent_id = $1 AND block_label = $2 AND is_active = true
            """,
            agent_id,
            block_label
        )

        if row:
            return MemoryBlock(
                block_label=block_label,
                content=row["content"],
                char_limit=row["char_limit"],
                priority=row["priority"],
                version=row["version"]
            )

        return None

    async def _store_memory_block_in_db(self, agent_id: str, block: MemoryBlock) -> None:
        """Store memory block in database."""
        await db.execute(
            """
            INSERT INTO memory_blocks
            (agent_id, block_label, content, char_limit, priority, version, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, true)
            ON CONFLICT (agent_id, block_label) DO UPDATE SET
                content = $3,
                char_limit = $4,
                priority = $5,
                version = $6,
                updated_at = NOW()
            """,
            agent_id,
            block.block_label,
            block.content,
            block.char_limit,
            block.priority,
            block.version
        )

    async def _store_semantic_memory(self, memory_id: str, content: str) -> None:
        """Store semantic memory details."""
        # TODO: Extract subject-predicate-object triples from content
        # For now, just create a simple record
        await db.execute(
            """
            INSERT INTO semantic_memories (memory_id, subject, predicate, object)
            VALUES ($1, 'unknown', 'contains', $2)
            """,
            memory_id,
            content[:500]
        )

    async def _store_episodic_memory(
        self,
        memory_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]]
    ) -> None:
        """Store episodic memory details."""
        session_id = metadata.get("session_id") if metadata else None

        await db.execute(
            """
            INSERT INTO episodic_memories
            (memory_id, session_id, event_summary, occurred_at)
            VALUES ($1, $2, $3, NOW())
            """,
            memory_id,
            session_id,
            content[:1000]
        )

    async def _store_procedural_memory(
        self,
        memory_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]]
    ) -> None:
        """Store procedural memory details."""
        skill_name = metadata.get("skill_name", "unknown") if metadata else "unknown"
        steps = metadata.get("steps", []) if metadata else []

        await db.execute(
            """
            INSERT INTO procedural_memories
            (memory_id, skill_name, steps)
            VALUES ($1, $2, $3)
            """,
            memory_id,
            skill_name,
            json.dumps(steps)
        )

    async def _update_access_times(self, memory_ids: List[str]) -> None:
        """Update last_accessed_at for memories."""
        if not memory_ids:
            return

        # Update in batches
        batch_size = 100
        for i in range(0, len(memory_ids), batch_size):
            batch = memory_ids[i:i + batch_size]

            await db.execute(
                """
                UPDATE memories SET last_accessed_at = NOW()
                WHERE id = ANY($1)
                """,
                batch
            )

    async def _run_consolidation_jobs(self) -> None:
        """Run periodic memory consolidation jobs."""
        while True:
            try:
                # Wait before next run
                await asyncio.sleep(3600)  # Run hourly

                # Check if consolidation is needed
                stats = await self.get_memory_stats()
                total_memories = stats.get("total_memories", 0)

                if total_memories > 1000:
                    logger.info(f"Running automatic memory consolidation ({total_memories} memories)")

                    # Run summarization job
                    await self.consolidate_memories(
                        job_type=MemoryConsolidationJobType.SUMMARIZE
                    )

                    # Run pruning job if memory count is high
                    if total_memories > 5000:
                        await self.consolidate_memories(
                            job_type=MemoryConsolidationJobType.PRUNE
                        )

            except Exception as e:
                logger.error(f"Error in memory consolidation job: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _consolidate_summarize(self, agent_id: Optional[str]) -> Dict[str, Any]:
        """Summarize similar memories."""
        # TODO: Implement AI-powered summarization of similar memories
        return {
            "memories_processed": 0,
            "memories_created": 0,
            "memories_archived": 0,
            "description": "Summarization not yet implemented"
        }

    async def _consolidate_cluster(self, agent_id: Optional[str]) -> Dict[str, Any]:
        """Cluster related memories."""
        # TODO: Implement clustering of related memories
        return {
            "memories_processed": 0,
            "memories_created": 0,
            "memories_archived": 0,
            "description": "Clustering not yet implemented"
        }

    async def _consolidate_prune(self, agent_id: Optional[str]) -> Dict[str, Any]:
        """Prune low-importance memories."""
        # Delete memories with low importance score that haven't been accessed recently
        result = await db.execute(
            """
            DELETE FROM memories
            WHERE importance_score < 0.2
              AND (last_accessed_at IS NULL OR last_accessed_at < NOW() - INTERVAL '30 days')
              AND (agent_id = $1 OR $1 IS NULL)
            RETURNING id
            """,
            agent_id
        )

        deleted_count = int(result.split()[-1]) if "DELETE" in result else 0

        return {
            "memories_processed": deleted_count,
            "memories_created": 0,
            "memories_archived": deleted_count,
            "description": f"Pruned {deleted_count} low-importance memories"
        }

    async def _consolidate_decay(self, agent_id: Optional[str]) -> Dict[str, Any]:
        """Decay strength of old memories."""
        # Reduce strength score of old memories
        result = await db.execute(
            """
            UPDATE memories
            SET strength_score = GREATEST(0.1, strength_score * 0.9)
            WHERE last_accessed_at < NOW() - INTERVAL '7 days'
              AND (agent_id = $1 OR $1 IS NULL)
            RETURNING id
            """,
            agent_id
        )

        updated_count = int(result.split()[-1]) if "UPDATE" in result else 0

        return {
            "memories_processed": updated_count,
            "memories_created": 0,
            "memories_archived": 0,
            "description": f"Decayed strength of {updated_count} old memories"
        }

    async def _consolidate_integrate(self, agent_id: Optional[str]) -> Dict[str, Any]:
        """Integrate new memories with existing knowledge."""
        # TODO: Implement knowledge graph integration
        return {
            "memories_processed": 0,
            "memories_created": 0,
            "memories_archived": 0,
            "description": "Integration not yet implemented"
        }


# Global memory system instance
memory_system = MemorySystem()


async def get_memory_system() -> MemorySystem:
    """Dependency for FastAPI routes."""
    return memory_system