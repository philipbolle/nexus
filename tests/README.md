# NEXUS Test Suite

Comprehensive pytest test suite for the NEXUS AI Operating System.

## Directory Structure

```
tests/
├── api/                    # API endpoint tests (FastAPI TestClient)
│   ├── test_agents_api.py     # Agent framework API tests
│   └── test_swarm_api.py      # Swarm communication API tests
├── unit/                   # Unit tests (mocked dependencies)
│   ├── agents/                # Agent framework unit tests
│   │   ├── test_registry.py      # AgentRegistry tests
│   │   ├── test_memory.py        # MemorySystem tests
│   │   ├── test_sessions.py      # SessionManager tests
│   │   ├── test_monitoring.py    # PerformanceMonitor tests
│   │   ├── test_tools.py         # ToolSystem tests (TODO)
│   │   ├── test_orchestrator.py  # OrchestratorEngine tests (TODO)
│   │   └── test_email_intelligence.py  # EmailIntelligenceAgent tests (TODO)
│   └── swarm/               # Swarm communication unit tests
│       ├── test_pubsub.py      # SwarmPubSub tests (ENABLED)
│       ├── test_agent.py       # SwarmAgent tests (ENABLED)
│       └── test_event_bus.py   # EventBus tests (DISABLED - TODO if enabled)
├── fixtures/              # Shared test fixtures
│   └── __init__.py
├── conftest.py           # Pytest configuration and shared fixtures
├── pytest.ini           # Pytest configuration (TODO)
└── .coveragerc          # Coverage configuration (TODO)
```

## Test Coverage

### Agent Framework Tests (Phase 1 Fixes)

**✅ COMPLETED - Tests for Phase 1 fixes:**

1. **AgentRegistry** (`test_registry.py`):
   - Duplicate name checking (in-memory and database)
   - `get_agent_by_name()` database query fallback
   - Agent lifecycle management
   - Registry status and metrics

2. **MemorySystem** (`test_memory.py`):
   - `get_memories()` method with proper database queries
   - Memory type handling and filtering
   - Memory storage and retrieval

3. **SessionManager** (`test_sessions.py`):
   - SQL `$2` syntax error fixes
   - Session creation and management
   - Message handling within sessions

4. **PerformanceMonitor** (`test_monitoring.py`):
   - UUID conversion for 'system' agent_id
   - Performance metric aggregation
   - Alert generation and management

**📋 TODO - Additional agent framework tests:**
- `test_tools.py` - ToolSystem class
- `test_orchestrator.py` - OrchestratorEngine class
- `test_email_intelligence.py` - EmailIntelligenceAgent class

### Swarm Communication Tests (Simplified Architecture)

**✅ COMPLETED - Tests for ENABLED components:**

1. **SwarmPubSub** (`test_pubsub.py`):
   - Redis Pub/Sub wrapper functionality
   - Channel management and reconnection
   - Message publishing and subscription

2. **SwarmAgent** (`test_agent.py`):
   - Swarm membership management
   - Message communication via Redis Pub/Sub
   - Basic agent coordination

**❌ DISABLED - Components not tested (simplified swarm):**
- EventBus system (`event_bus.py`)
- RAFT consensus protocol (`raft.py`)
- Voting system (`voting.py`)
- Swarm-enabled orchestrator (`swarm_orchestrator.py`)

### API Endpoint Tests

**✅ COMPLETED:**

1. **Agent Framework API** (`test_agents_api.py`):
   - Agent management endpoints (`/agents/*`)
   - Task execution endpoints (`/tasks/*`)
   - Session management endpoints (`/sessions/*`)
   - Registry status and agent selection

2. **Swarm Communication API** (`test_swarm_api.py`):
   - Swarm management endpoints (`/swarm/*`)
   - Swarm membership endpoints (`/swarm/{id}/members`)
   - Swarm messaging endpoints (`/swarm/{id}/messages`)
   - Tests only ENABLED endpoints in simplified architecture

## Running Tests

### Quick Test Runner

```bash
# Run the comprehensive test suite
./scripts/run_tests.sh
```

### Manual Test Execution

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
python -m pytest tests/ -v

# Run specific test category
python -m pytest tests/unit/agents/ -v
python -m pytest tests/unit/swarm/ -v
python -m pytest tests/api/ -v

# Run specific test file
python -m pytest tests/unit/agents/test_registry.py -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=term-missing

# Generate HTML coverage report
python -m pytest tests/ --cov=app --cov-report=html:coverage_report
```

### Test Configuration

- **Async Tests**: All async tests use `@pytest.mark.asyncio`
- **Markers**: Tests use `@pytest.mark.unit` and `@pytest.mark.api` markers
- **Fixtures**: Shared fixtures in `tests/fixtures/` and `tests/conftest.py`
- **Mocking**: Extensive use of `unittest.mock` for external dependencies

## Test Patterns

### Unit Test Structure

```python
import pytest
from unittest.mock import AsyncMock, patch

class TestClassName:
    """Test suite for ClassName."""

    @pytest.fixture
    def test_instance(self):
        """Create test instance."""
        return ClassName()

    @pytest.mark.asyncio
    async def test_method_success(self, test_instance):
        """Test successful method execution."""
        # Setup
        with patch('module.dependency', AsyncMock(return_value=result)):
            # Execute
            result = await test_instance.method()

            # Verify
            assert result == expected
```

### API Test Structure

```python
import pytest
from fastapi.testclient import TestClient

def test_endpoint_success(client):
    """Test successful API endpoint."""
    # Setup mock dependencies
    with patch('app.routers.module.dependency', AsyncMock(return_value=data)):
        # Execute
        response = client.get("/endpoint")

        # Verify
        assert response.status_code == 200
        assert response.json() == expected_data
```

## Test Fixtures

Common fixtures available in `tests/fixtures/`:

- `mock_agent_base` - Mock BaseAgent with common attributes
- `mock_swarm_agent` - Mock SwarmAgent with swarm capabilities
- `mock_registry` - Mock AgentRegistry
- `mock_pubsub` - Mock SwarmPubSub
- `mock_database` - Mock database connection
- Sample data fixtures for agents, swarms, tasks, and sessions

## Coverage Goals

- **Unit Tests**: 80%+ coverage for core business logic
- **API Tests**: 90%+ coverage for all enabled endpoints
- **Integration**: Basic integration tests for critical paths
- **Error Handling**: Comprehensive error case testing

## Notes

1. **Simplified Swarm**: Tests only cover ENABLED components in the simplified swarm architecture
2. **Phase 1 Focus**: Tests specifically cover fixes made in Phase 1 of agent framework development
3. **Mock External Dependencies**: All tests mock database, Redis, and AI providers
4. **Async Support**: All async functions properly tested with `pytest-asyncio`
5. **Error Cases**: Comprehensive testing of error conditions and edge cases