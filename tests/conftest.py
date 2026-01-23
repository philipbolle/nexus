"""
Minimal pytest configuration for NEXUS tests.
"""
import asyncio
import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_ai_response():
    """Mock AI response for testing."""
    return {
        "content": "Mock AI response for testing",
        "provider": "mock",
        "model": "mock-model",
        "input_tokens": 10,
        "output_tokens": 20,
        "cost_usd": 0.0001,
        "latency_ms": 50,
        "cached": False
    }


# Import fixtures from fixtures module
from tests.fixtures import *