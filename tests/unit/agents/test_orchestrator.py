"""
Unit tests for OrchestratorEngine class.

Tests task decomposition, agent delegation, load balancing, and coordination.
"""

import pytest
import uuid
import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List

from app.agents.orchestrator import (
    OrchestratorEngine,
    DecompositionStrategy,
    DelegationStrategy,
    Subtask,
    TaskDecomposition,
    DelegationPlan
)
from app.agents.registry import AgentRegistry


class TestOrchestratorEngine:
    """Test suite for OrchestratorEngine class."""

    @pytest.fixture
    def orchestrator(self):
        """Create a fresh OrchestratorEngine instance for each test."""
        return OrchestratorEngine()

    @pytest.fixture
    def mock_registry(self):
        """Create a mock agent registry."""
        registry = Mock(spec=AgentRegistry)
        registry.select_agent_for_task = AsyncMock(return_value=(None, 0.0))
        registry.get_agent = AsyncMock(return_value=None)
        registry.list_agents = AsyncMock(return_value=[])
        return registry

    @pytest.fixture
    def sample_task_description(self):
        """Sample task description for testing."""
        return "Analyze monthly finances and generate budget recommendations"

    @pytest.mark.asyncio
    async def test_initial_state(self, orchestrator):
        """Test OrchestratorEngine initial state."""
        assert orchestrator.registry is not None
        assert len(orchestrator.active_tasks) == 0
        assert orchestrator._running == False
        assert orchestrator._task_processor_task is None

    @pytest.mark.asyncio
    async def test_initialize_starts_processor(self, orchestrator):
        """Test that initialize starts the task processor."""
        with patch.object(orchestrator, '_task_processor', AsyncMock()) as mock_processor:
            await orchestrator.initialize()

            assert orchestrator._running == True
            assert orchestrator._task_processor_task is not None
            mock_processor.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_stops_processor(self, orchestrator):
        """Test that shutdown stops the task processor."""
        # First initialize to start processor
        mock_task = Mock()
        orchestrator._task_processor_task = mock_task
        orchestrator._running = True

        await orchestrator.shutdown()

        assert orchestrator._running == False
        assert orchestrator._task_processor_task is None

    @pytest.mark.asyncio
    async def test_decompose_task_hierarchical_strategy(self, orchestrator, sample_task_description):
        """Test task decomposition with hierarchical strategy."""
        with patch('app.agents.orchestrator.chat', AsyncMock()) as mock_chat:
            # Mock AI response for decomposition
            mock_chat.return_value = {
                "content": json.dumps({
                    "subtasks": [
                        {
                            "description": "Analyze expense patterns",
                            "required_capabilities": ["data_analysis", "financial_analysis"],
                            "estimated_complexity": "medium",
                            "dependencies": []
                        },
                        {
                            "description": "Generate budget recommendations",
                            "required_capabilities": ["recommendation_generation", "financial_analysis"],
                            "estimated_complexity": "high",
                            "dependencies": ["subtask_1"]
                        }
                    ],
                    "estimated_total_complexity": 2,
                    "max_parallelism": 1,
                    "critical_path": ["subtask_1", "subtask_2"]
                })
            }

            decomposition = await orchestrator.decompose_task(
                task_description=sample_task_description,
                strategy=DecompositionStrategy.HIERARCHICAL
            )

            assert decomposition is not None
            assert decomposition.task_id is not None
            assert decomposition.original_task == sample_task_description
            assert decomposition.strategy == DecompositionStrategy.HIERARCHICAL
            assert len(decomposition.subtasks) == 2
            assert decomposition.estimated_total_complexity == 2
            assert decomposition.max_parallelism == 1
            assert decomposition.critical_path == ["subtask_1", "subtask_2"]

    @pytest.mark.asyncio
    async def test_decompose_task_sequential_strategy(self, orchestrator, sample_task_description):
        """Test task decomposition with sequential strategy."""
        with patch('app.agents.orchestrator.chat', AsyncMock()):
            # We'll trust the AI returns something valid
            decomposition = await orchestrator.decompose_task(
                task_description=sample_task_description,
                strategy=DecompositionStrategy.SEQUENTIAL
            )

            assert decomposition is not None
            assert decomposition.strategy == DecompositionStrategy.SEQUENTIAL

    @pytest.mark.asyncio
    async def test_decompose_task_ai_failure(self, orchestrator, sample_task_description):
        """Test task decomposition when AI call fails."""
        with patch('app.agents.orchestrator.chat', AsyncMock(side_effect=Exception("AI service unavailable"))):
            decomposition = await orchestrator.decompose_task(
                task_description=sample_task_description,
                strategy=DecompositionStrategy.HIERARCHICAL
            )

            # Should return minimal decomposition
            assert decomposition is not None
            assert len(decomposition.subtasks) == 1  # Single fallback subtask
            assert decomposition.subtasks[0].description == sample_task_description

    @pytest.mark.asyncio
    async def test_select_agent_for_subtask_capability_match(self, orchestrator, mock_registry):
        """Test agent selection with capability matching strategy."""
        subtask = Subtask(
            id="subtask_1",
            description="Analyze expense patterns",
            required_capabilities=["data_analysis", "financial_analysis"],
            estimated_complexity="medium",
            dependencies=[]
        )

        mock_agent = Mock()
        mock_agent.agent_id = "agent_123"
        mock_agent.name = "Analysis Agent"
        mock_agent.capabilities = ["data_analysis", "financial_analysis", "statistical_modeling"]

        mock_registry.select_agent_for_task.return_value = (mock_agent, 0.9)

        orchestrator.registry = mock_registry

        agent_id, score = await orchestrator._select_agent_for_subtask(
            subtask=subtask,
            strategy=DelegationStrategy.CAPABILITY_MATCH
        )

        assert agent_id == "agent_123"
        assert score == 0.9
        mock_registry.select_agent_for_task.assert_called_once_with(
            capabilities=["data_analysis", "financial_analysis"],
            strategy=DelegationStrategy.CAPABILITY_MATCH
        )

    @pytest.mark.asyncio
    async def test_select_agent_for_subtask_no_match(self, orchestrator, mock_registry):
        """Test agent selection when no agent matches."""
        subtask = Subtask(
            id="subtask_1",
            description="Analyze expense patterns",
            required_capabilities=["specialized_capability"],
            estimated_complexity="medium",
            dependencies=[]
        )

        mock_registry.select_agent_for_task.return_value = (None, 0.0)

        orchestrator.registry = mock_registry

        agent_id, score = await orchestrator._select_agent_for_subtask(
            subtask=subtask,
            strategy=DelegationStrategy.CAPABILITY_MATCH
        )

        assert agent_id is None
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_create_delegation_plan(self, orchestrator, mock_registry):
        """Test creation of delegation plan for subtasks."""
        subtasks = [
            Subtask(
                id="subtask_1",
                description="Analyze expense patterns",
                required_capabilities=["data_analysis"],
                estimated_complexity="medium",
                dependencies=[]
            ),
            Subtask(
                id="subtask_2",
                description="Generate recommendations",
                required_capabilities=["recommendation_generation"],
                estimated_complexity="high",
                dependencies=["subtask_1"]
            )
        ]

        decomposition = TaskDecomposition(
            task_id="task_123",
            original_task="Test task",
            strategy=DecompositionStrategy.HIERARCHICAL,
            subtasks=subtasks,
            estimated_total_complexity=2,
            max_parallelism=1,
            critical_path=["subtask_1", "subtask_2"]
        )

        # Mock agent selection
        mock_agent1 = Mock()
        mock_agent1.agent_id = "agent_1"
        mock_agent2 = Mock()
        mock_agent2.agent_id = "agent_2"

        with patch.object(orchestrator, '_select_agent_for_subtask', AsyncMock()) as mock_select:
            mock_select.side_effect = [
                ("agent_1", 0.9),
                ("agent_2", 0.8)
            ]

            plan = await orchestrator.create_delegation_plan(
                decomposition=decomposition,
                strategy=DelegationStrategy.CAPABILITY_MATCH
            )

            assert plan is not None
            assert plan.task_id == "task_123"
            assert plan.strategy == DelegationStrategy.CAPABILITY_MATCH
            assert plan.assignments == {"subtask_1": "agent_1", "subtask_2": "agent_2"}
            assert plan.estimated_cost >= 0
            assert plan.estimated_duration_ms >= 0
            assert plan.load_distribution == {"agent_1": 1, "agent_2": 1}

    @pytest.mark.asyncio
    async def test_delegate_subtask(self, orchestrator, mock_registry):
        """Test delegating a subtask to an agent."""
        subtask = Subtask(
            id="subtask_1",
            description="Analyze expense patterns",
            required_capabilities=["data_analysis"],
            estimated_complexity="medium",
            dependencies=[]
        )

        mock_agent = AsyncMock()
        mock_agent.agent_id = "agent_123"
        mock_agent.execute = AsyncMock(return_value={"result": "success"})

        mock_registry.get_agent.return_value = mock_agent
        orchestrator.registry = mock_registry

        result = await orchestrator.delegate_subtask(
            subtask_id=subtask.id,
            agent_id=mock_agent.agent_id,
            subtask_description=subtask.description,
            parameters={"data": "test"}
        )

        assert result == {"result": "success"}
        mock_agent.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delegate_subtask_agent_not_found(self, orchestrator, mock_registry):
        """Test delegating subtask when agent not found."""
        mock_registry.get_agent.return_value = None
        orchestrator.registry = mock_registry

        with pytest.raises(ValueError, match="Agent not found"):
            await orchestrator.delegate_subtask(
                subtask_id="subtask_1",
                agent_id="nonexistent_agent",
                subtask_description="Test task",
                parameters={}
            )

    @pytest.mark.asyncio
    async def test_process_task_success(self, orchestrator):
        """Test processing a complete task through the orchestrator."""
        task_id = "test_task_123"
        task_description = "Analyze monthly finances"

        with patch.object(orchestrator, 'decompose_task', AsyncMock()) as mock_decompose, \
             patch.object(orchestrator, 'create_delegation_plan', AsyncMock()) as mock_create_plan, \
             patch.object(orchestrator, 'execute_delegation_plan', AsyncMock()) as mock_execute:

            mock_decomposition = Mock()
            mock_decomposition.task_id = task_id
            mock_decompose.return_value = mock_decomposition

            mock_plan = Mock()
            mock_create_plan.return_value = mock_plan

            mock_results = {"subtask_1": "result_1", "subtask_2": "result_2"}
            mock_execute.return_value = mock_results

            result = await orchestrator.process_task(
                task_id=task_id,
                task_description=task_description,
                parameters={}
            )

            mock_decompose.assert_called_once_with(task_description, DecompositionStrategy.HIERARCHICAL)
            mock_create_plan.assert_called_once_with(mock_decomposition, DelegationStrategy.CAPABILITY_MATCH)
            mock_execute.assert_called_once_with(mock_plan)

            assert result["task_id"] == task_id
            assert result["status"] == "completed"
            assert "results" in result

    @pytest.mark.asyncio
    async def test_execute_delegation_plan(self, orchestrator):
        """Test executing a delegation plan."""
        plan = DelegationPlan(
            task_id="task_123",
            strategy=DelegationStrategy.CAPABILITY_MATCH,
            assignments={"subtask_1": "agent_1", "subtask_2": "agent_2"},
            estimated_cost=10.0,
            estimated_duration_ms=5000,
            load_distribution={"agent_1": 1, "agent_2": 1}
        )

        with patch.object(orchestrator, 'delegate_subtask', AsyncMock()) as mock_delegate:
            mock_delegate.side_effect = [
                "result_1",
                "result_2"
            ]

            results = await orchestrator.execute_delegation_plan(plan)

            assert mock_delegate.call_count == 2
            assert results == {"subtask_1": "result_1", "subtask_2": "result_2"}

    @pytest.mark.asyncio
    async def test_execute_delegation_plan_with_error(self, orchestrator):
        """Test executing a delegation plan with subtask error."""
        plan = DelegationPlan(
            task_id="task_123",
            strategy=DelegationStrategy.CAPABILITY_MATCH,
            assignments={"subtask_1": "agent_1", "subtask_2": "agent_2"},
            estimated_cost=10.0,
            estimated_duration_ms=5000,
            load_distribution={"agent_1": 1, "agent_2": 1}
        )

        with patch.object(orchestrator, 'delegate_subtask', AsyncMock()) as mock_delegate:
            mock_delegate.side_effect = [
                "result_1",
                RuntimeError("Subtask failed")
            ]

            results = await orchestrator.execute_delegation_plan(plan)

            assert mock_delegate.call_count == 2
            assert "subtask_1" in results
            assert "subtask_2" in results
            assert isinstance(results["subtask_2"], RuntimeError)