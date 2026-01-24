"""
API tests for agent framework endpoints.

Tests FastAPI endpoints in app/routers/agents.py.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.main import app
from app.agents.base import AgentStatus, AgentType
from app.models.agent_schemas import (
    AgentCreate, AgentUpdate, AgentResponse,
    TaskRequest, TaskResponse,
    SessionCreate, SessionResponse,
    ToolCreate, ToolResponse
)


class TestAgentsAPI:
    """Test suite for agent framework API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def sample_agent_data(self):
        """Create sample agent data for testing."""
        return {
            "name": "test_agent",
            "agent_type": "domain",
            "description": "Test agent",
            "system_prompt": "You are a test agent",
            "capabilities": ["test_capability"],
            "domain": "testing",
            "config": {"test": "config"}
        }

    @pytest.fixture
    def sample_agent_response(self):
        """Create sample agent response for testing."""
        agent_id = str(uuid.uuid4())
        return {
            "id": agent_id,
            "name": "test_agent",
            "agent_type": "domain",
            "status": "idle",
            "description": "Test agent",
            "system_prompt": "You are a test agent",
            "capabilities": ["test_capability"],
            "domain": "testing",
            "config": {"test": "config"},
            "metrics": {},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }

    def test_root_endpoint(self, client):
        """Test root endpoint redirects to /health."""
        response = client.get("/")
        assert response.status_code == 200
        # Should redirect to /health or return health info
        assert response.json() is not None

    def test_health_endpoint(self, client):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        # Note: /health endpoint returns simple health check without services field
        # Detailed health check with services is at /health/detailed

    @pytest.mark.asyncio
    async def test_list_agents_success(self, client, sample_agent_response):
        """Test GET /agents endpoint."""
        # Mock agent registry
        mock_agent = Mock()
        mock_agent.id = sample_agent_response["id"]
        mock_agent.agent_id = sample_agent_response["id"]  # Needed by _agent_to_response
        mock_agent.name = sample_agent_response["name"]
        mock_agent.agent_type = AgentType.DOMAIN
        mock_agent.status = AgentStatus.IDLE
        mock_agent.description = sample_agent_response["description"]
        mock_agent.system_prompt = sample_agent_response["system_prompt"]
        mock_agent.capabilities = sample_agent_response["capabilities"]
        mock_agent.domain = sample_agent_response["domain"]
        mock_agent.config = sample_agent_response["config"]
        mock_agent.metrics = sample_agent_response["metrics"]
        mock_agent.created_at = sample_agent_response["created_at"]
        mock_agent.updated_at = sample_agent_response["updated_at"]

        with patch('app.routers.agents.agent_registry') as mock_registry:
            mock_registry.list_agents = AsyncMock(return_value=[mock_agent])

            # Execute
            response = client.get("/agents")

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            agent_data = data[0]
            assert agent_data["id"] == sample_agent_response["id"]
            assert agent_data["name"] == sample_agent_response["name"]
            assert agent_data["status"] == "idle"

    @pytest.mark.asyncio
    async def test_create_agent_success(self, client, sample_agent_data, sample_agent_response):
        """Test POST /agents endpoint."""
        # Mock agent registry
        mock_agent = Mock()
        mock_agent.agent_id = sample_agent_response["id"]
        mock_agent.name = sample_agent_response["name"]
        mock_agent.agent_type = AgentType.DOMAIN
        mock_agent.status = AgentStatus.IDLE
        mock_agent.description = sample_agent_response["description"]
        mock_agent.system_prompt = sample_agent_response["system_prompt"]
        mock_agent.capabilities = sample_agent_response["capabilities"]
        mock_agent.domain = sample_agent_response["domain"]
        mock_agent.config = sample_agent_response["config"]
        mock_agent.metrics = sample_agent_response["metrics"]
        mock_agent.created_at = sample_agent_response["created_at"]
        mock_agent.updated_at = sample_agent_response["updated_at"]

        with patch('app.routers.agents.agent_registry') as mock_registry:
            mock_registry.register_agent = AsyncMock(return_value=mock_agent)

            # Execute
            response = client.post("/agents", json=sample_agent_data)

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == sample_agent_response["id"]
            assert data["name"] == sample_agent_response["name"]
            assert data["status"] == "idle"

    @pytest.mark.asyncio
    async def test_create_agent_duplicate_name(self, client, sample_agent_data):
        """Test POST /agents with duplicate name."""
        # Mock registry to raise ValueError for duplicate name
        with patch('app.routers.agents.agent_registry') as mock_registry:
            mock_registry.register_agent = AsyncMock(
                side_effect=ValueError("Agent with name 'test_agent' already exists")
            )

            # Execute
            response = client.post("/agents", json=sample_agent_data)

            # Verify
            assert response.status_code == 400
            data = response.json()
            assert "detail" in data
            assert "already exists" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_agent_success(self, client, sample_agent_response):
        """Test GET /agents/{agent_id} endpoint."""
        agent_id = sample_agent_response["id"]

        # Mock agent registry
        mock_agent = Mock()
        mock_agent.agent_id = sample_agent_response["id"]
        mock_agent.name = sample_agent_response["name"]
        mock_agent.agent_type = AgentType.DOMAIN
        mock_agent.status = AgentStatus.IDLE
        mock_agent.description = sample_agent_response["description"]
        mock_agent.system_prompt = sample_agent_response["system_prompt"]
        mock_agent.capabilities = sample_agent_response["capabilities"]
        mock_agent.domain = sample_agent_response["domain"]
        mock_agent.config = sample_agent_response["config"]
        mock_agent.metrics = sample_agent_response["metrics"]
        mock_agent.created_at = sample_agent_response["created_at"]
        mock_agent.updated_at = sample_agent_response["updated_at"]

        with patch('app.routers.agents.agent_registry') as mock_registry:
            mock_registry.get_agent = AsyncMock(return_value=mock_agent)

            # Execute
            response = client.get(f"/agents/{agent_id}")

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == agent_id
            assert data["name"] == sample_agent_response["name"]

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, client):
        """Test GET /agents/{agent_id} with non-existent agent."""
        agent_id = str(uuid.uuid4())

        # Mock registry to return None
        with patch('app.routers.agents.agent_registry') as mock_registry:
            mock_registry.get_agent = AsyncMock(return_value=None)

            # Execute
            response = client.get(f"/agents/{agent_id}")

            # Verify
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data
            assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_agent_success(self, client, sample_agent_response):
        """Test PUT /agents/{agent_id} endpoint."""
        agent_id = sample_agent_response["id"]
        update_data = {
            "name": "updated_agent",
            "description": "Updated description",
            "capabilities": ["updated_capability"]
        }

        # Mock agent (updated)
        mock_agent = Mock()
        mock_agent.agent_id = sample_agent_response["id"]
        mock_agent.name = "updated_agent"
        mock_agent.agent_type = AgentType.DOMAIN
        mock_agent.status = AgentStatus.IDLE
        mock_agent.description = "Updated description"
        mock_agent.system_prompt = sample_agent_response["system_prompt"]
        mock_agent.capabilities = ["updated_capability"]
        mock_agent.domain = sample_agent_response["domain"]
        mock_agent.config = sample_agent_response["config"]
        mock_agent.metrics = sample_agent_response["metrics"]
        mock_agent.created_at = sample_agent_response["created_at"]
        mock_agent.updated_at = sample_agent_response["updated_at"]

        with patch('app.routers.agents.agent_registry') as mock_registry:
            mock_registry.update_agent = AsyncMock(return_value=mock_agent)

            # Execute
            response = client.put(f"/agents/{agent_id}", json=update_data)

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "updated_agent"
            assert data["description"] == "Updated description"
            assert data["capabilities"] == ["updated_capability"]

    @pytest.mark.asyncio
    async def test_delete_agent_success(self, client):
        """Test DELETE /agents/{agent_id} endpoint."""
        agent_id = str(uuid.uuid4())

        # Mock registry to return True (successful deletion)
        with patch('app.routers.agents.agent_registry') as mock_registry:
            mock_registry.delete_agent = AsyncMock(return_value=True)

            # Execute
            response = client.delete(f"/agents/{agent_id}")

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "Agent deleted successfully"

    @pytest.mark.asyncio
    async def test_delete_agent_not_found(self, client):
        """Test DELETE /agents/{agent_id} with non-existent agent."""
        agent_id = str(uuid.uuid4())

        # Mock registry to return False (agent not found)
        with patch('app.routers.agents.agent_registry') as mock_registry:
            mock_registry.delete_agent = AsyncMock(return_value=False)

            # Execute
            response = client.delete(f"/agents/{agent_id}")

            # Verify
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data
            assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_start_agent_success(self, client):
        """Test POST /agents/{agent_id}/start endpoint."""
        agent_id = str(uuid.uuid4())

        # Mock registry to return True (successful start)
        with patch('app.routers.agents.agent_registry') as mock_registry:
            mock_registry.start_agent = AsyncMock(return_value=True)

            # Execute
            response = client.post(f"/agents/{agent_id}/start")

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "Agent started successfully"

    @pytest.mark.asyncio
    async def test_stop_agent_success(self, client):
        """Test POST /agents/{agent_id}/stop endpoint."""
        agent_id = str(uuid.uuid4())

        # Mock registry to return True (successful stop)
        with patch('app.routers.agents.agent_registry') as mock_registry:
            mock_registry.stop_agent = AsyncMock(return_value=True)

            # Execute
            response = client.post(f"/agents/{agent_id}/stop")

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "Agent stopped successfully"

    @pytest.mark.asyncio
    async def test_get_agent_status(self, client, sample_agent_response):
        """Test GET /agents/{agent_id}/status endpoint."""
        agent_id = sample_agent_response["id"]

        # Mock agent with metrics
        mock_agent = Mock()
        mock_agent.agent_id = agent_id
        mock_agent.name = sample_agent_response["name"]
        mock_agent.status = AgentStatus.IDLE
        mock_agent.metrics = {
            "success_rate": 0.95,
            "avg_latency_ms": 150.5,
            "total_tasks": 100
        }

        with patch('app.routers.agents.agent_registry') as mock_registry:
            mock_registry.get_agent = AsyncMock(return_value=mock_agent)

            # Execute
            response = client.get(f"/agents/{agent_id}/status")

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["agent_id"] == agent_id
            assert data["status"] == "idle"
            assert "metrics" in data
            assert data["metrics"]["success_rate"] == 0.95
            assert data["metrics"]["avg_latency_ms"] == 150.5

    @pytest.mark.asyncio
    async def test_submit_task(self, client):
        """Test POST /tasks endpoint."""
        task_data = {
            "description": "Test task description",
            "parameters": {"param1": "value1"},
            "priority": "medium",
            "timeout_seconds": 300
        }

        # Mock orchestrator
        mock_task_response = {
            "task_id": str(uuid.uuid4()),
            "status": "pending",
            "assigned_agent_id": str(uuid.uuid4()),
            "created_at": "2024-01-01T00:00:00"
        }

        with patch('app.routers.agents.orchestrator') as mock_orchestrator:
            mock_orchestrator.submit_task = AsyncMock(return_value=mock_task_response)

            # Execute
            response = client.post("/tasks", json=task_data)

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == mock_task_response["task_id"]
            assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_task_status(self, client):
        """Test GET /tasks/{task_id} endpoint."""
        task_id = str(uuid.uuid4())

        # Mock orchestrator
        mock_task_status = {
            "task_id": task_id,
            "status": "completed",
            "result": {"output": "Task completed successfully"},
            "assigned_agent_id": str(uuid.uuid4()),
            "created_at": "2024-01-01T00:00:00",
            "completed_at": "2024-01-01T00:01:00"
        }

        with patch('app.routers.agents.orchestrator') as mock_orchestrator:
            mock_orchestrator.get_task_status = AsyncMock(return_value=mock_task_status)

            # Execute
            response = client.get(f"/tasks/{task_id}")

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == task_id
            assert data["status"] == "completed"
            assert data["result"]["output"] == "Task completed successfully"

    @pytest.mark.asyncio
    async def test_get_registry_status(self, client):
        """Test GET /registry-status endpoint."""
        # Mock registry status
        mock_status = {
            "status": "running",
            "total_agents": 5,
            "active_agents": 3,
            "idle_agents": 2,
            "processing_agents": 1,
            "error_agents": 0,
            "capabilities_available": ["test_capability"],
            "domains_available": ["testing"]
        }

        with patch('app.routers.agents.agent_registry') as mock_registry:
            mock_registry.get_registry_status = AsyncMock(return_value=mock_status)

            # Execute
            response = client.get("/registry-status")

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "running"
            assert data["total_agents"] == 5
            assert data["active_agents"] == 3

    @pytest.mark.asyncio
    async def test_select_agent_for_task(self, client):
        """Test POST /registry-select-agent endpoint."""
        selection_request = {
            "task_description": "Test task description",
            "required_capabilities": ["test_capability"],
            "preferred_domain": "testing"
        }

        # Mock agent
        mock_agent = Mock()
        mock_agent.agent_id = str(uuid.uuid4())
        mock_agent.name = "selected_agent"
        mock_agent.status = AgentStatus.IDLE

        # Mock registry selection
        with patch('app.routers.agents.agent_registry') as mock_registry:
            mock_registry.select_agent_for_task = AsyncMock(return_value=(mock_agent, 0.85))

            # Execute
            response = client.post("/registry-select-agent", json=selection_request)

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["agent_id"] == mock_agent.agent_id
            assert data["agent_name"] == mock_agent.name
            assert data["confidence_score"] == 0.85

    @pytest.mark.asyncio
    async def test_create_session(self, client):
        """Test POST /sessions endpoint."""
        session_data = {
            "agent_id": str(uuid.uuid4()),
            "user_id": "test_user",
            "config": {
                "max_messages": 100,
                "timeout_minutes": 30,
                "context": {"topic": "testing"}
            }
        }

        # Mock session
        mock_session = Mock()
        mock_session.id = str(uuid.uuid4())
        mock_session.agent_id = session_data["agent_id"]
        mock_session.user_id = session_data["user_id"]
        mock_session.state = "active"
        mock_session.config = session_data["config"]
        mock_session.created_at = "2024-01-01T00:00:00"

        with patch('app.routers.agents.session_manager') as mock_manager:
            mock_manager.create_session = AsyncMock(return_value=mock_session)

            # Execute
            response = client.post("/sessions", json=session_data)

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == mock_session.id
            assert data["agent_id"] == session_data["agent_id"]
            assert data["state"] == "active"

    @pytest.mark.asyncio
    async def test_get_session(self, client):
        """Test GET /sessions/{session_id} endpoint."""
        session_id = str(uuid.uuid4())

        # Mock session
        mock_session = Mock()
        mock_session.id = session_id
        mock_session.agent_id = str(uuid.uuid4())
        mock_session.user_id = "test_user"
        mock_session.state = "active"
        mock_session.config = {}
        mock_session.created_at = "2024-01-01T00:00:00"
        mock_session.updated_at = "2024-01-01T00:00:00"

        with patch('app.routers.agents.session_manager') as mock_manager:
            mock_manager.get_session = AsyncMock(return_value=mock_session)

            # Execute
            response = client.get(f"/sessions/{session_id}")

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == session_id
            assert data["state"] == "active"

    @pytest.mark.asyncio
    async def test_add_session_message(self, client):
        """Test POST /sessions/{session_id}/messages endpoint."""
        session_id = str(uuid.uuid4())
        message_data = {
            "role": "user",
            "content": "Hello, agent!",
            "metadata": {"source": "test"}
        }

        # Mock message
        mock_message = Mock()
        mock_message.id = str(uuid.uuid4())
        mock_message.session_id = session_id
        mock_message.role = "user"
        mock_message.content = "Hello, agent!"
        mock_message.metadata = {"source": "test"}
        mock_message.created_at = "2024-01-01T00:00:00"

        with patch('app.routers.agents.session_manager') as mock_manager:
            mock_manager.add_message = AsyncMock(return_value=mock_message)

            # Execute
            response = client.post(f"/sessions/{session_id}/messages", json=message_data)

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == mock_message.id
            assert data["session_id"] == session_id
            assert data["role"] == "user"
            assert data["content"] == "Hello, agent!"