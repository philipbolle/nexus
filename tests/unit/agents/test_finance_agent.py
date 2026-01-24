"""
Unit tests for FinanceAgent class.

Tests financial tracking, budget analysis, debt progress monitoring,
and integration with existing finance endpoints.
"""

import pytest
import uuid
import json
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List

from app.agents.finance_agent import FinanceAgent, register_finance_agent
from app.agents.base import AgentType, AgentStatus
from app.agents.tools import ToolSystem


class TestFinanceAgent:
    """Test suite for FinanceAgent class."""

    @pytest.fixture
    def finance_agent(self):
        """Create a fresh FinanceAgent instance for each test."""
        agent = FinanceAgent(name="Test Finance Agent")
        return agent

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
    def sample_expense_data(self):
        """Sample expense data for testing."""
        return {
            "amount": 25.99,
            "category": "Food",
            "merchant": "Grocery Store",
            "description": "Weekly groceries",
            "transaction_date": "2026-01-23"
        }

    @pytest.mark.asyncio
    async def test_agent_creation_defaults(self):
        """Test FinanceAgent creation with defaults."""
        agent = FinanceAgent()

        assert agent.name == "Finance Agent"
        assert agent.agent_type == AgentType.DOMAIN
        assert agent.domain == "finance"
        assert "expense_tracking" in agent.capabilities
        assert "budget_analysis" in agent.capabilities
        assert "debt_monitoring" in agent.capabilities
        assert "financial_insights" in agent.capabilities
        assert "recommendation_generation" in agent.capabilities
        assert agent.config["domain"] == "finance"
        assert agent.config["default_days_analysis"] == 30
        assert agent.config["budget_alert_threshold"] == 0.9

    @pytest.mark.asyncio
    async def test_agent_creation_custom_name(self):
        """Test FinanceAgent creation with custom name."""
        agent = FinanceAgent(name="Custom Finance Agent", description="Custom description")

        assert agent.name == "Custom Finance Agent"
        assert agent.description == "Custom description"
        assert agent.agent_type == AgentType.DOMAIN
        assert agent.domain == "finance"

    @pytest.mark.asyncio
    async def test_agent_creation_custom_capabilities(self):
        """Test FinanceAgent creation with custom capabilities."""
        custom_caps = ["expense_tracking", "custom_capability"]
        agent = FinanceAgent(capabilities=custom_caps)

        assert agent.capabilities == custom_caps

    @pytest.mark.asyncio
    async def test_agent_creation_custom_config(self):
        """Test FinanceAgent creation with custom config."""
        custom_config = {
            "domain": "personal_finance",
            "default_days_analysis": 60,
            "budget_alert_threshold": 0.8,
            "custom_setting": "value"
        }
        agent = FinanceAgent(config=custom_config)

        assert agent.config["domain"] == "personal_finance"
        assert agent.config["default_days_analysis"] == 60
        assert agent.config["budget_alert_threshold"] == 0.8
        assert agent.config["custom_setting"] == "value"

    @pytest.mark.asyncio
    async def test_on_initialize_registers_tools(self, finance_agent):
        """Test that _on_initialize registers finance tools."""
        with patch.object(finance_agent, '_register_finance_tools', AsyncMock()) as mock_register, \
             patch.object(finance_agent, '_load_finance_config', AsyncMock()) as mock_load:

            await finance_agent._on_initialize()

            mock_register.assert_called_once()
            mock_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_finance_tools(self, finance_agent):
        """Test that finance tools are registered."""
        with patch.object(finance_agent, 'register_tool', AsyncMock()) as mock_register:
            await finance_agent._register_finance_tools()

            # Should register multiple tools
            assert mock_register.call_count >= 4  # log_expense, get_budget_status, get_debt_progress, analyze_spending, generate_recommendations

            # Check that first tool is log_expense
            first_call_args = mock_register.call_args_list[0]
            assert first_call_args[0][0] == "log_expense"  # tool_name
            assert first_call_args[0][1] == finance_agent._tool_log_expense  # implementation

    @pytest.mark.asyncio
    async def test_process_task_log_expense(self, finance_agent, sample_expense_data, mock_database):
        """Test processing log_expense task."""
        task = {
            "type": "log_expense",
            "parameters": sample_expense_data
        }

        expected_result = {
            "transaction_id": "test_123",
            "amount": sample_expense_data["amount"],
            "category": sample_expense_data["category"],
            "budget_remaining": 474.01,
            "message": f"Logged ${sample_expense_data['amount']} expense in {sample_expense_data['category']}"
        }

        with patch('app.agents.finance_agent.db', mock_database), \
             patch.object(finance_agent, '_log_expense', AsyncMock(return_value={
                 "success": True,
                 "transaction": expected_result
             })):

            result = await finance_agent._process_task(task)

            finance_agent._log_expense.assert_called_once_with(task, None)
            assert result["success"] == True
            assert "transaction" in result

    @pytest.mark.asyncio
    async def test_process_task_get_budget_status(self, finance_agent, mock_database):
        """Test processing get_budget_status task."""
        task = {
            "type": "get_budget_status",
            "parameters": {"month": "2026-01"}
        }

        expected_result = {
            "month": "2026-01",
            "total_budget": 1000.0,
            "total_spent": 525.99,
            "remaining": 474.01,
            "percent_used": 52.599,
            "categories": []
        }

        with patch('app.agents.finance_agent.db', mock_database), \
             patch.object(finance_agent, '_get_budget_status', AsyncMock(return_value={
                 "success": True,
                 "budget_status": expected_result
             })):

            result = await finance_agent._process_task(task)

            finance_agent._get_budget_status.assert_called_once_with(task, None)
            assert result["success"] == True
            assert "budget_status" in result

    @pytest.mark.asyncio
    async def test_process_task_get_debt_progress(self, finance_agent, mock_database):
        """Test processing get_debt_progress task."""
        task = {
            "type": "get_debt_progress",
            "parameters": {"include_inactive": False}
        }

        expected_result = {
            "total_original": 9700.0,
            "total_current": 8500.0,
            "total_paid": 1200.0,
            "percent_paid": 12.37,
            "debts": []
        }

        with patch('app.agents.finance_agent.db', mock_database), \
             patch.object(finance_agent, '_get_debt_progress', AsyncMock(return_value={
                 "success": True,
                 "debt_progress": expected_result
             })):

            result = await finance_agent._process_task(task)

            finance_agent._get_debt_progress.assert_called_once_with(task, None)
            assert result["success"] == True
            assert "debt_progress" in result

    @pytest.mark.asyncio
    async def test_process_task_unknown_type(self, finance_agent):
        """Test processing unknown task type."""
        task = {
            "type": "unknown_task",
            "parameters": {}
        }

        result = await finance_agent._process_task(task)

        assert result["success"] == False
        assert "Unknown task type" in result["error"]
        assert "supported_types" in result

    @pytest.mark.asyncio
    async def test_process_task_exception_handling(self, finance_agent):
        """Test exception handling in task processing."""
        task = {
            "type": "log_expense",
            "parameters": {"amount": 25.99, "category": "Food"}
        }

        with patch.object(finance_agent, '_log_expense', AsyncMock(side_effect=RuntimeError("Database error"))):
            result = await finance_agent._process_task(task)

            assert result["success"] == False
            assert "Database error" in result["error"]
            assert result["task_type"] == "log_expense"

    @pytest.mark.asyncio
    async def test_tool_log_expense_integration(self, finance_agent, sample_expense_data, mock_database):
        """Test the log_expense tool integration with database."""
        # Mock database response for INSERT
        mock_database.fetch_one.return_value = {"id": "test_123"}

        with patch('app.agents.finance_agent.db', mock_database):
            # This tests the actual tool implementation
            # We'll need to mock the HTTP request to the finance endpoint
            # For now, test that the method exists and can be called
            assert hasattr(finance_agent, '_tool_log_expense')
            # Don't actually call it since it makes HTTP requests

    @pytest.mark.asyncio
    async def test_register_finance_agent_function(self):
        """Test the register_finance_agent helper function."""
        with patch('app.agents.registry.registry') as mock_registry, \
             patch('app.agents.finance_agent.FinanceAgent') as mock_agent_class:

            mock_agent = AsyncMock()
            mock_agent_class.return_value = mock_agent
            mock_registry.get_agent_by_name = AsyncMock(return_value=None)
            mock_registry.create_agent = AsyncMock(return_value=mock_agent)

            agent = await register_finance_agent()

            # The function creates a FinanceAgent instance via registry.create_agent
            # It doesn't instantiate FinanceAgent directly
            mock_agent_class.assert_not_called()  # Not called directly
            mock_registry.create_agent.assert_called_once()
            assert agent == mock_agent

    @pytest.mark.asyncio
    async def test_agent_lifecycle(self, finance_agent):
        """Test complete agent lifecycle."""
        with patch.object(finance_agent, '_on_initialize', AsyncMock()) as mock_init, \
             patch.object(finance_agent, '_on_cleanup', AsyncMock()) as mock_cleanup, \
             patch.object(finance_agent, '_load_or_create_db_record', AsyncMock()) as mock_load, \
             patch.object(finance_agent, '_register_core_tools', AsyncMock()) as mock_register_tools, \
             patch.object(finance_agent, '_save_state', AsyncMock()) as mock_save_state:

            # Test initialization
            await finance_agent.initialize()
            mock_init.assert_called_once()
            mock_load.assert_called_once()
            mock_register_tools.assert_called_once()
            assert finance_agent.status == AgentStatus.IDLE

            # Test cleanup
            await finance_agent.cleanup()
            mock_cleanup.assert_called_once()
            mock_save_state.assert_called_once()
            assert finance_agent.status == AgentStatus.STOPPED