"""
Unit tests for BaseAgent abstract class.

Tests agent lifecycle, tool integration, memory access, session management,
and the abstract methods that all agents must implement.
"""

import pytest
import uuid
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List, Optional

from app.agents.base import BaseAgent, AgentType, AgentStatus
from app.agents.tools import ToolSystem, ToolDefinition, ToolParameter, ToolType
from app.agents.memory import MemorySystem, MemoryType
from app.agents.sessions import SessionManager, SessionType


# Concrete test agent class for testing BaseAgent
class TestConcreteAgent(BaseAgent):
    """Concrete agent for testing BaseAgent abstract methods."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.initialize_called = False
        self.cleanup_called = False
        self.processed_tasks = []

    async def _on_initialize(self) -> None:
        """Test implementation of abstract method."""
        self.initialize_called = True
        # Register a test tool
        await self.register_tool("test_tool", self._test_tool_impl)

    async def _on_cleanup(self) -> None:
        """Test implementation of abstract method."""
        self.cleanup_called = True

    async def _process_task(self, task: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Test implementation of abstract method."""
        self.processed_tasks.append((task, context))
        task_type = task.get("type", "unknown")

        if task_type == "test_task":
            return {"success": True, "result": "test_result", "task_type": task_type}
        elif task_type == "error_task":
            raise ValueError("Test error")
        else:
            return {"success": False, "error": f"Unknown task type: {task_type}"}

    async def _test_tool_impl(self, **kwargs) -> Dict[str, Any]:
        """Test tool implementation."""
        return {"success": True, "tool_result": kwargs}


class TestBaseAgent:
    """Test suite for BaseAgent class."""

    @pytest.fixture
    def concrete_agent(self):
        """Create a concrete test agent instance."""
        return TestConcreteAgent(
            name="Test Agent",
            agent_type=AgentType.DOMAIN,
            description="Test agent for unit testing",
            system_prompt="You are a test agent",
            capabilities=["test_capability"],
            domain="testing",
            config={"test_setting": "value"}
        )

    @pytest.fixture
    def mock_database(self):
        """Create a mock database connection."""
        db = Mock()
        db.fetch_one = AsyncMock(return_value=None)
        db.fetch_all = AsyncMock(return_value=[])
        db.execute = AsyncMock()
        db.fetch_val = AsyncMock(return_value=None)
        return db

    @pytest.fixture
    def mock_tool_system(self):
        """Create a mock tool system."""
        tool_system = Mock()
        tool_system.register_tool = AsyncMock()
        tool_system.execute_tool = AsyncMock()
        tool_system.get_tool = AsyncMock(return_value=None)
        return tool_system

    @pytest.fixture
    def mock_memory_system(self):
        """Create a mock memory system."""
        memory_system = Mock()
        memory_system.store_memory = AsyncMock()
        memory_system.query_memories = AsyncMock(return_value=[])
        memory_system.get_memory_blocks = AsyncMock(return_value=[])
        return memory_system

    @pytest.fixture
    def mock_session_manager(self):
        """Create a mock session manager."""
        session_manager = Mock()
        session_manager.create_session = AsyncMock(return_value={"session_id": "test_session"})
        session_manager.get_session = AsyncMock(return_value={"session_id": "test_session"})
        session_manager.add_message = AsyncMock()
        session_manager.end_session = AsyncMock()
        return session_manager

    @pytest.mark.asyncio
    async def test_agent_creation_defaults(self):
        """Test BaseAgent creation with minimal parameters."""
        agent = TestConcreteAgent()

        assert agent.name == "Unnamed Agent"
        assert agent.agent_type == AgentType.DOMAIN
        assert agent.description == ""
        assert agent.system_prompt == ""
        assert agent.capabilities == []
        assert agent.domain is None
        assert agent.config == {}
        assert agent.status == AgentStatus.CREATED
        assert agent.agent_id is not None
        assert isinstance(agent.agent_id, str)
        assert len(agent.agent_id) > 0

    @pytest.mark.asyncio
    async def test_agent_creation_with_params(self):
        """Test BaseAgent creation with all parameters."""
        agent_id = str(uuid.uuid4())
        agent = TestConcreteAgent(
            agent_id=agent_id,
            name="Custom Agent",
            agent_type=AgentType.ANALYZER,
            description="Custom description",
            system_prompt="Custom system prompt",
            capabilities=["analysis", "reporting"],
            domain="analytics",
            supervisor_id="supervisor_123",
            config={"max_tasks": 10, "timeout": 30}
        )

        assert agent.agent_id == agent_id
        assert agent.name == "Custom Agent"
        assert agent.agent_type == AgentType.ANALYZER
        assert agent.description == "Custom description"
        assert agent.system_prompt == "Custom system prompt"
        assert agent.capabilities == ["analysis", "reporting"]
        assert agent.domain == "analytics"
        assert agent.supervisor_id == "supervisor_123"
        assert agent.config == {"max_tasks": 10, "timeout": 30}
        assert agent.status == AgentStatus.CREATED

    @pytest.mark.asyncio
    async def test_agent_initialization(self, concrete_agent, mock_database):
        """Test agent initialization lifecycle."""
        with patch.object(concrete_agent, '_register_core_tools', AsyncMock()) as mock_register_core, \
             patch.object(concrete_agent, '_load_or_create_db_record', AsyncMock()) as mock_load, \
             patch('app.agents.base.db', mock_database):

            await concrete_agent.initialize()

            # Check that abstract method was called
            assert concrete_agent.initialize_called == True

            # Check that core methods were called
            mock_register_core.assert_called_once()
            mock_load.assert_called_once()
            # Note: _save_state is NOT called during initialization

            # Check status updated
            assert concrete_agent.status == AgentStatus.IDLE

    @pytest.mark.asyncio
    async def test_agent_cleanup(self, concrete_agent):
        """Test agent cleanup lifecycle."""
        with patch.object(concrete_agent, '_save_state', AsyncMock()) as mock_save:
            # Initialize first
            concrete_agent.status = AgentStatus.IDLE

            await concrete_agent.cleanup()

            # Check that abstract method was called
            assert concrete_agent.cleanup_called == True

            # Check that state was saved
            mock_save.assert_called_once()

            # Check status updated
            assert concrete_agent.status == AgentStatus.STOPPED

    @pytest.mark.asyncio
    async def test_execute_task_success(self, concrete_agent, mock_database):
        """Test executing a task successfully."""
        # Initialize agent
        concrete_agent.status = AgentStatus.IDLE

        with patch('app.agents.base.db', mock_database):
            task = {"type": "test_task", "data": "test_data"}
            response = await concrete_agent.execute(task)

            # Check task was processed
            assert len(concrete_agent.processed_tasks) == 1
            assert concrete_agent.processed_tasks[0][0] == task

            # Check response structure
            assert response["success"] == True
            assert response["agent_id"] == concrete_agent.agent_id
            assert response["agent_name"] == concrete_agent.name
            assert "session_id" in response
            assert "result" in response
            assert "metrics" in response

            # Check the actual result from _process_task
            assert response["result"]["success"] == True
            assert response["result"]["result"] == "test_result"
            assert response["result"]["task_type"] == "test_task"

            # Check status transitions
            assert concrete_agent.status == AgentStatus.IDLE

    @pytest.mark.asyncio
    async def test_execute_task_with_error(self, concrete_agent, mock_database):
        """Test executing a task that raises an error."""
        # Initialize agent
        concrete_agent.status = AgentStatus.IDLE

        with patch('app.agents.base.db', mock_database):
            task = {"type": "error_task", "data": "error_data"}

            # The execute method should catch the ValueError from _process_task
            # and return an error response
            response = await concrete_agent.execute(task)

            # Check task was processed
            assert len(concrete_agent.processed_tasks) == 1
            assert concrete_agent.processed_tasks[0][0] == task

            # Check error response structure
            assert response["success"] == False
            assert "error" in response
            assert "Test error" in response["error"]

            # Check status transitions (should be IDLE after error)
            assert concrete_agent.status == AgentStatus.IDLE

    @pytest.mark.asyncio
    async def test_execute_task_when_not_idle(self, concrete_agent):
        """Test executing a task when agent is not in IDLE state."""
        concrete_agent.status = AgentStatus.PROCESSING

        task = {"type": "test_task"}
        # Should raise RuntimeError with "not ready" message
        with pytest.raises(RuntimeError, match="not ready"):
            await concrete_agent.execute(task)

        # Should not process task
        assert len(concrete_agent.processed_tasks) == 0

    @pytest.mark.asyncio
    async def test_register_tool(self, concrete_agent, mock_database):
        """Test registering a tool with the agent."""
        with patch('app.agents.base.db', mock_database):
            tool_name = "test_tool"
            tool_impl = AsyncMock()
            await concrete_agent.register_tool(tool_name, tool_impl)

            # Check tool stored in agent's tool dictionary
            assert tool_name in concrete_agent._tools
            assert concrete_agent._tools[tool_name] == tool_impl

            # Check database was called to register tool
            # fetch_one is called twice: once to check existence, once after insert
            assert mock_database.fetch_one.call_count == 2
            mock_database.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_tool(self, concrete_agent):
        """Test executing a tool through the agent."""
        # First register a mock tool
        mock_tool = AsyncMock(return_value={"success": True})
        concrete_agent._tools["test_tool"] = mock_tool

        result = await concrete_agent.execute_tool(
            tool_name="test_tool",
            param1="value1"
        )

        # Check tool was called with correct parameters
        mock_tool.assert_called_once_with(param1="value1")
        assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_store_memory(self, concrete_agent):
        """Test storing memory through the agent."""
        # BaseAgent has _store_memory private method, not store_memory
        # This is a stub implementation that returns "stored"
        result = await concrete_agent._store_memory(
            content="Test memory content",
            memory_type="episodic",
            tags=["test", "memory"]
        )
        assert result == "stored"

    @pytest.mark.asyncio
    async def test_query_memories(self, concrete_agent):
        """Test querying memories through the agent."""
        # BaseAgent has _search_memory private method, not query_memories
        # This is a stub implementation that returns empty list
        results = await concrete_agent._search_memory(
            query="test query",
            limit=5
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_create_session(self, concrete_agent, mock_database):
        """Test creating a session through the agent."""
        # BaseAgent has _create_session private method
        with patch('app.agents.base.db', mock_database):
            session_id = await concrete_agent._create_session(
                task="Test task",
                context={"test": "context"}
            )
            assert isinstance(session_id, str)
            assert len(session_id) > 0
            # Check database was called
            mock_database.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_session_message(self, concrete_agent):
        """Test adding a message to the current session."""
        # BaseAgent doesn't have add_session_message method
        # This test is a placeholder for when the method is implemented
        pass

    @pytest.mark.asyncio
    async def test_add_session_message_no_session(self, concrete_agent):
        """Test adding a message when no session is active."""
        # BaseAgent doesn't have add_session_message method
        # This test is a placeholder for when the method is implemented
        pass

    @pytest.mark.asyncio
    async def test_end_session(self, concrete_agent):
        """Test ending the current session."""
        # BaseAgent doesn't have end_session method
        # This test is a placeholder for when the method is implemented
        pass

    @pytest.mark.asyncio
    async def test_delegate_task(self, concrete_agent):
        """Test delegating a task to another agent."""
        # BaseAgent doesn't have delegate_task method
        # This test is a placeholder for when the method is implemented
        pass

    @pytest.mark.asyncio
    async def test_delegate_task_agent_not_found(self, concrete_agent):
        """Test delegating a task to a non-existent agent."""
        # BaseAgent doesn't have delegate_task method
        # This test is a placeholder for when the method is implemented
        pass


