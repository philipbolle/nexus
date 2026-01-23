"""
Unit tests for MemorySystem class.

Tests memory storage, retrieval, and the specific fixes made in Phase 1:
- get_memories() method with proper database queries
- Memory type handling and filtering
- Memory consolidation and pruning
"""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any, List

from app.agents.memory import MemorySystem, MemoryType, MemoryQuery, MemoryResult


class TestMemorySystem:
    """Test suite for MemorySystem class."""

    @pytest.fixture
    def memory_system(self):
        """Create a fresh MemorySystem instance for each test."""
        return MemorySystem()

    @pytest.fixture
    def sample_memory_data(self):
        """Create sample memory data for testing."""
        return {
            "id": str(uuid.uuid4()),
            "agent_id": str(uuid.uuid4()),
            "memory_type": "semantic",
            "content": "Test memory content",
            "importance_score": 0.8,
            "strength_score": 0.9,
            "last_accessed_at": datetime.now(),
            "tags": ["test", "unit"],
            "metadata": {"source": "test"},
            "created_at": datetime.now()
        }

    @pytest.mark.asyncio
    async def test_initial_state(self, memory_system):
        """Test memory system initial state."""
        assert memory_system._initialized is False
        assert len(memory_system.agent_memory_blocks) == 0
        assert len(memory_system.memory_cache) == 0
        assert memory_system.chroma_client is None
        assert len(memory_system.chroma_collections) == 0

    @pytest.mark.asyncio
    async def test_get_memories_success(self, memory_system, sample_memory_data):
        """Test successful memory retrieval (Phase 1 fix)."""
        # Setup
        agent_id = sample_memory_data["agent_id"]

        # Mock database to return memory data
        with patch('app.agents.memory.db') as mock_db:
            mock_db.fetch_all = AsyncMock(return_value=[sample_memory_data])

            # Execute
            memories = await memory_system.get_memories(
                agent_id=agent_id,
                memory_type=None,
                limit=50
            )

            # Verify
            assert len(memories) == 1
            memory = memories[0]
            assert memory["id"] == sample_memory_data["id"]
            assert memory["agent_id"] == sample_memory_data["agent_id"]
            assert memory["content"] == sample_memory_data["content"]

            # Verify database query
            mock_db.fetch_all.assert_called_once()
            call_args = mock_db.fetch_all.call_args[0][0]
            assert "WHERE agent_id = $1" in call_args
            assert "(expires_at IS NULL OR expires_at > NOW())" in call_args

    @pytest.mark.asyncio
    async def test_get_memories_with_type_filter(self, memory_system, sample_memory_data):
        """Test memory retrieval with type filter."""
        # Setup
        agent_id = sample_memory_data["agent_id"]
        memory_type = "semantic"

        # Mock database
        with patch('app.agents.memory.db') as mock_db:
            mock_db.fetch_all = AsyncMock(return_value=[sample_memory_data])

            # Execute
            memories = await memory_system.get_memories(
                agent_id=agent_id,
                memory_type=memory_type,
                limit=50
            )

            # Verify
            assert len(memories) == 1
            # Verify database query includes memory_type filter
            mock_db.fetch_all.assert_called_once()
            call_args = mock_db.fetch_all.call_args[0][0]
            assert "AND memory_type = $2" in call_args

    @pytest.mark.asyncio
    async def test_get_memories_with_limit(self, memory_system, sample_memory_data):
        """Test memory retrieval with limit."""
        # Setup
        agent_id = sample_memory_data["agent_id"]

        # Mock database to return multiple memories
        multiple_memories = [sample_memory_data.copy() for _ in range(10)]
        for i, mem in enumerate(multiple_memories):
            mem["id"] = str(uuid.uuid4())

        with patch('app.agents.memory.db') as mock_db:
            mock_db.fetch_all = AsyncMock(return_value=multiple_memories)

            # Execute with limit 5
            memories = await memory_system.get_memories(
                agent_id=agent_id,
                memory_type=None,
                limit=5
            )

            # Verify
            assert len(memories) == 5
            mock_db.fetch_all.assert_called_once()
            call_args = mock_db.fetch_all.call_args[0][0]
            assert "LIMIT 5" in call_args or "LIMIT $2" in call_args

    @pytest.mark.asyncio
    async def test_get_memories_empty_result(self, memory_system):
        """Test memory retrieval when no memories exist."""
        # Setup
        agent_id = str(uuid.uuid4())

        # Mock database to return empty list
        with patch('app.agents.memory.db') as mock_db:
            mock_db.fetch_all = AsyncMock(return_value=[])

            # Execute
            memories = await memory_system.get_memories(
                agent_id=agent_id,
                memory_type=None,
                limit=50
            )

            # Verify
            assert len(memories) == 0

    @pytest.mark.asyncio
    async def test_get_memories_database_error(self, memory_system, caplog):
        """Test memory retrieval handles database errors gracefully."""
        # Setup
        agent_id = str(uuid.uuid4())

        # Mock database to raise exception
        with patch('app.agents.memory.db') as mock_db:
            mock_db.fetch_all = AsyncMock(side_effect=Exception("Database error"))

            # Execute
            memories = await memory_system.get_memories(
                agent_id=agent_id,
                memory_type=None,
                limit=50
            )

            # Verify
            assert len(memories) == 0
            assert "Failed to get memories for agent" in caplog.text

    @pytest.mark.asyncio
    async def test_store_memory_success(self, memory_system, sample_memory_data):
        """Test successful memory storage."""
        # Setup
        agent_id = sample_memory_data["agent_id"]
        content = sample_memory_data["content"]
        memory_type = MemoryType.SEMANTIC

        # Mock database insert
        with patch('app.agents.memory.db') as mock_db:
            mock_db.execute = AsyncMock()

            # Mock embedding generation
            with patch('app.agents.memory.get_embedding', AsyncMock(return_value=[0.1] * 384)):
                # Execute
                memory_id = await memory_system.store_memory(
                    agent_id=agent_id,
                    content=content,
                    memory_type=memory_type,
                    importance_score=0.8,
                    tags=["test"],
                    metadata={"source": "test"}
                )

                # Verify
                assert memory_id is not None
                mock_db.execute.assert_called_once()
                # Verify the insert query includes all required fields
                call_args = mock_db.execute.call_args[0][0]
                assert "INSERT INTO memories" in call_args

    @pytest.mark.asyncio
    async def test_store_memory_with_embedding(self, memory_system):
        """Test memory storage with embedding generation."""
        # Setup
        agent_id = str(uuid.uuid4())
        content = "Test content for embedding"
        memory_type = MemoryType.SEMANTIC
        expected_embedding = [0.1] * 384

        # Mock embedding generation
        with patch('app.agents.memory.get_embedding', AsyncMock(return_value=expected_embedding)):
            # Mock database insert
            with patch('app.agents.memory.db') as mock_db:
                mock_db.execute = AsyncMock()

                # Execute
                await memory_system.store_memory(
                    agent_id=agent_id,
                    content=content,
                    memory_type=memory_type
                )

                # Verify embedding was generated
                from app.agents.memory import get_embedding
                get_embedding.assert_called_once_with(content)

    @pytest.mark.asyncio
    async def test_query_memories_semantic(self, memory_system):
        """Test semantic memory query."""
        # Setup
        agent_id = str(uuid.uuid4())
        query_text = "test query"
        memory_query = MemoryQuery(
            query_text=query_text,
            memory_types=[MemoryType.SEMANTIC],
            agent_id=agent_id,
            limit=10,
            min_similarity=0.7
        )

        # Mock embedding and similarity calculation
        with patch('app.agents.memory.get_embedding', AsyncMock(return_value=[0.1] * 384)):
            with patch('app.agents.memory.cosine_similarity', Mock(return_value=0.8)):
                # Mock database query for memories
                with patch.object(memory_system, 'get_memories', AsyncMock(return_value=[])):
                    # Execute
                    results = await memory_system.query_memories(memory_query)

                    # Verify
                    assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_update_memory_strength(self, memory_system, sample_memory_data):
        """Test updating memory strength score."""
        # Setup
        memory_id = sample_memory_data["id"]
        new_strength = 0.95

        # Mock database update
        with patch('app.agents.memory.db') as mock_db:
            mock_db.execute = AsyncMock()

            # Execute
            success = await memory_system.update_memory_strength(
                memory_id=memory_id,
                strength_score=new_strength
            )

            # Verify
            assert success is True
            mock_db.execute.assert_called_once()
            call_args = mock_db.execute.call_args[0][0]
            assert "UPDATE memories" in call_args
            assert "strength_score = $1" in call_args

    @pytest.mark.asyncio
    async def test_delete_memory(self, memory_system):
        """Test memory deletion."""
        # Setup
        memory_id = str(uuid.uuid4())

        # Mock database delete
        with patch('app.agents.memory.db') as mock_db:
            mock_db.execute = AsyncMock()

            # Execute
            success = await memory_system.delete_memory(memory_id)

            # Verify
            assert success is True
            mock_db.execute.assert_called_once()
            call_args = mock_db.execute.call_args[0][0]
            assert "DELETE FROM memories" in call_args
            assert "id = $1" in call_args

    @pytest.mark.asyncio
    async def test_add_memory_block(self, memory_system):
        """Test adding memory block for agent."""
        # Setup
        agent_id = str(uuid.uuid4())
        block_label = "context"
        content = "Test context block"

        # Execute
        memory_system.add_memory_block(
            agent_id=agent_id,
            block_label=block_label,
            content=content,
            char_limit=1000,
            priority=50
        )

        # Verify
        assert agent_id in memory_system.agent_memory_blocks
        assert block_label in memory_system.agent_memory_blocks[agent_id]
        block = memory_system.agent_memory_blocks[agent_id][block_label]
        assert block.content == content
        assert block.char_limit == 1000
        assert block.priority == 50

    @pytest.mark.asyncio
    async def test_get_memory_blocks(self, memory_system):
        """Test retrieving memory blocks for agent."""
        # Setup
        agent_id = str(uuid.uuid4())

        # Add some memory blocks
        memory_system.add_memory_block(
            agent_id=agent_id,
            block_label="context",
            content="Context block",
            priority=30
        )
        memory_system.add_memory_block(
            agent_id=agent_id,
            block_label="task",
            content="Task block",
            priority=50
        )

        # Execute
        blocks = memory_system.get_memory_blocks(agent_id)

        # Verify
        assert len(blocks) == 2
        # Blocks should be sorted by priority (lower = more important)
        assert blocks[0].block_label == "context"  # priority 30
        assert blocks[1].block_label == "task"     # priority 50

    @pytest.mark.asyncio
    async def test_clear_memory_blocks(self, memory_system):
        """Test clearing memory blocks for agent."""
        # Setup
        agent_id = str(uuid.uuid4())

        # Add memory block
        memory_system.add_memory_block(
            agent_id=agent_id,
            block_label="context",
            content="Test block"
        )

        assert agent_id in memory_system.agent_memory_blocks

        # Execute
        memory_system.clear_memory_blocks(agent_id)

        # Verify
        assert agent_id not in memory_system.agent_memory_blocks

    @pytest.mark.asyncio
    async def test_prune_old_memories(self, memory_system):
        """Test pruning old memories."""
        # Mock database call to delete old memories
        with patch('app.agents.memory.db') as mock_db:
            mock_db.execute = AsyncMock()

            # Execute
            pruned_count = await memory_system.prune_old_memories(
                days_old=30,
                max_memories_per_agent=1000
            )

            # Verify
            assert pruned_count >= 0
            mock_db.execute.assert_called()
            # Should have at least one DELETE query
            call_args = mock_db.execute.call_args[0][0]
            assert "DELETE FROM memories" in call_args

    @pytest.mark.asyncio
    async def test_consolidate_memories(self, memory_system):
        """Test memory consolidation."""
        # Mock database operations for consolidation
        with patch('app.agents.memory.db') as mock_db:
            mock_db.fetch_all = AsyncMock(return_value=[])
            mock_db.execute = AsyncMock()

            # Execute
            consolidated = await memory_system.consolidate_memories(
                agent_id=str(uuid.uuid4()),
                consolidation_type="summarize"
            )

            # Verify
            assert isinstance(consolidated, dict)
            assert "consolidated_count" in consolidated
            assert "new_memories_created" in consolidated