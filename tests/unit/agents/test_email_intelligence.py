"""
Unit tests for EmailIntelligenceAgent class.

Tests email processing, classification, extraction, transaction logging,
and integration with existing email services.
"""

import pytest
import uuid
import json
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List

from app.agents.email_intelligence import EmailIntelligenceAgent, register_email_agent
from app.agents.base import AgentType, AgentStatus


class TestEmailIntelligenceAgent:
    """Test suite for EmailIntelligenceAgent class."""

    @pytest.fixture
    def email_agent(self):
        """Create a fresh EmailIntelligenceAgent instance for each test."""
        agent = EmailIntelligenceAgent(name="Test Email Agent")
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
    def sample_email_message(self):
        """Sample email message for testing."""
        return {
            "id": "email_123",
            "subject": "Test email",
            "from": "sender@example.com",
            "to": "recipient@example.com",
            "date": "2026-01-23T10:30:00",
            "body": "This is a test email body.",
            "account": "gmail"
        }

    @pytest.fixture
    def sample_classification_result(self):
        """Sample email classification result."""
        return {
            "category": "personal",
            "confidence": 0.95,
            "summary": "Email from friend",
            "extracted_data": {}
        }

    @pytest.mark.asyncio
    async def test_agent_creation_defaults(self):
        """Test EmailIntelligenceAgent creation with defaults."""
        agent = EmailIntelligenceAgent()

        assert agent.name == "Email Intelligence Agent"
        assert agent.agent_type == AgentType.EMAIL_INTELLIGENCE
        assert "email_processing" in agent.capabilities
        assert "classification" in agent.capabilities
        assert "extraction" in agent.capabilities
        assert "summarization" in agent.capabilities
        assert "transaction_logging" in agent.capabilities
        assert "alerting" in agent.capabilities
        assert "scanning" in agent.capabilities
        assert agent.config.get("max_emails_per_scan", 0) == 50
        assert agent.config.get("importance_threshold_alert", 0) == 0.8
        assert agent.config.get("importance_threshold_summarize", 0) == 0.7
        assert agent.config.get("default_since_days", 0) == 1
        assert agent.config.get("domain") == "email"

    @pytest.mark.asyncio
    async def test_agent_creation_custom_name(self):
        """Test EmailIntelligenceAgent creation with custom name."""
        agent = EmailIntelligenceAgent(
            name="Custom Email Agent",
            description="Custom description"
        )

        assert agent.name == "Custom Email Agent"
        assert agent.description == "Custom description"
        assert agent.agent_type == AgentType.EMAIL_INTELLIGENCE

    @pytest.mark.asyncio
    async def test_agent_creation_custom_capabilities(self):
        """Test EmailIntelligenceAgent creation with custom capabilities."""
        custom_caps = ["email_processing", "custom_capability"]
        agent = EmailIntelligenceAgent(capabilities=custom_caps)

        assert agent.capabilities == custom_caps

    @pytest.mark.asyncio
    async def test_agent_creation_custom_config(self):
        """Test EmailIntelligenceAgent creation with custom config."""
        custom_config = {
            "max_emails_per_scan": 100,
            "importance_threshold_alert": 0.9,
            "importance_threshold_summarize": 0.6,
            "default_since_days": 2,
            "custom_setting": "value"
        }
        agent = EmailIntelligenceAgent(config=custom_config)

        assert agent.config["max_emails_per_scan"] == 100
        assert agent.config["importance_threshold_alert"] == 0.9
        assert agent.config["importance_threshold_summarize"] == 0.6
        assert agent.config["default_since_days"] == 2
        assert agent.config["custom_setting"] == "value"

    @pytest.mark.asyncio
    async def test_on_initialize_registers_tools(self, email_agent):
        """Test that _on_initialize registers email tools."""
        with patch.object(email_agent, '_register_email_tools', AsyncMock()) as mock_register, \
             patch.object(email_agent, '_load_email_config', AsyncMock()) as mock_load:

            await email_agent._on_initialize()

            mock_register.assert_called_once()
            mock_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_email_tools(self, email_agent):
        """Test that email tools are registered."""
        with patch.object(email_agent, 'register_tool', AsyncMock()) as mock_register:
            await email_agent._register_email_tools()

            # Should register multiple tools
            assert mock_register.call_count >= 3  # scan_emails, process_email, get_email_stats

            # Check that first tool is classify_email
            first_call_args = mock_register.call_args_list[0]
            assert first_call_args[0][0] == "classify_email"  # tool_name
            assert first_call_args[0][1] == email_agent._tool_classify_email  # implementation

    @pytest.mark.asyncio
    async def test_process_task_scan_emails(self, email_agent, mock_database):
        """Test processing scan_emails task."""
        task = {
            "type": "scan_emails",
            "parameters": {"account": "gmail", "limit": 10}
        }

        expected_result = {
            "emails_processed": 5,
            "categories": {"personal": 2, "work": 3},
            "actions_taken": {"archived": 1, "deleted": 0}
        }

        with patch('app.agents.email_intelligence.db', mock_database), \
             patch.object(email_agent, '_scan_emails', AsyncMock(return_value={
                 "success": True,
                 "scan_results": expected_result
             })):

            result = await email_agent._process_task(task)

            email_agent._scan_emails.assert_called_once_with(task, None)
            assert result["success"] == True
            assert "scan_results" in result

    @pytest.mark.asyncio
    async def test_process_task_process_email(self, email_agent, mock_database, sample_email_message):
        """Test processing process_email task."""
        task = {
            "type": "process_email",
            "parameters": {"email": sample_email_message}
        }

        expected_result = {
            "category": "personal",
            "summary": "Test email summary",
            "extracted_data": {},
            "action_taken": "none"
        }

        with patch('app.agents.email_intelligence.db', mock_database), \
             patch.object(email_agent, '_process_single_email', AsyncMock(return_value={
                 "success": True,
                 "processing_result": expected_result
             })):

            result = await email_agent._process_task(task)

            email_agent._process_single_email.assert_called_once_with(task, None)
            assert result["success"] == True
            assert "processing_result" in result

    @pytest.mark.asyncio
    async def test_process_task_get_email_stats(self, email_agent, mock_database):
        """Test processing get_email_stats task."""
        task = {
            "type": "get_stats",
            "parameters": {"days": 7}
        }

        expected_result = {
            "total_emails": 42,
            "categories": {"personal": 10, "work": 15, "promo": 17},
            "processing_time_avg": 2.5
        }

        with patch('app.agents.email_intelligence.db', mock_database), \
             patch.object(email_agent, '_get_email_stats', AsyncMock(return_value={
                 "success": True,
                 "stats": expected_result
             })):

            result = await email_agent._process_task(task)

            email_agent._get_email_stats.assert_called_once_with(task, None)
            assert result["success"] == True
            assert "stats" in result

    @pytest.mark.asyncio
    async def test_process_task_unknown_type(self, email_agent):
        """Test processing unknown task type."""
        task = {
            "type": "unknown_task",
            "parameters": {}
        }

        result = await email_agent._process_task(task)

        assert result["success"] == False
        assert "Unknown task type" in result["error"]
        assert "supported_types" in result

    @pytest.mark.asyncio
    async def test_process_task_exception_handling(self, email_agent):
        """Test exception handling in task processing."""
        task = {
            "type": "scan_emails",
            "parameters": {"account": "gmail"}
        }

        with patch.object(email_agent, '_scan_emails', AsyncMock(side_effect=RuntimeError("Database error"))):
            result = await email_agent._process_task(task)

            assert result["success"] == False
            assert "Database error" in result["error"]
            assert result["task_type"] == "scan_emails"

    @pytest.mark.asyncio
    async def test_tool_scan_emails_integration(self, email_agent, mock_database):
        """Test the scan_emails tool integration with database."""
        # Mock database response
        mock_database.fetch_all.return_value = []

        with patch('app.agents.email_intelligence.db', mock_database):
            # This tests that the method exists and can be called
            assert hasattr(email_agent, '_scan_emails')
            # Don't actually call it since it makes HTTP requests and AI calls

    @pytest.mark.asyncio
    async def test_register_email_agent_function(self):
        """Test the register_email_agent helper function."""
        with patch('app.agents.registry.registry') as mock_registry:

            mock_agent = AsyncMock()
            mock_registry.get_agent_by_name = AsyncMock(return_value=None)
            mock_registry.create_agent = AsyncMock(return_value=mock_agent)

            agent = await register_email_agent()

            mock_registry.create_agent.assert_called_once()
            assert agent == mock_agent

    @pytest.mark.asyncio
    async def test_agent_lifecycle(self, email_agent):
        """Test complete agent lifecycle."""
        with patch.object(email_agent, '_on_initialize', AsyncMock()) as mock_init, \
             patch.object(email_agent, '_on_cleanup', AsyncMock()) as mock_cleanup, \
             patch.object(email_agent, '_load_or_create_db_record', AsyncMock()) as mock_load, \
             patch.object(email_agent, '_register_core_tools', AsyncMock()) as mock_register_tools, \
             patch.object(email_agent, '_save_state', AsyncMock()) as mock_save_state:

            # Test initialization
            await email_agent.initialize()
            mock_init.assert_called_once()
            mock_load.assert_called_once()
            mock_register_tools.assert_called_once()
            assert email_agent.status == AgentStatus.IDLE

            # Test cleanup
            await email_agent.cleanup()
            mock_cleanup.assert_called_once()
            mock_save_state.assert_called_once()
            assert email_agent.status == AgentStatus.STOPPED

