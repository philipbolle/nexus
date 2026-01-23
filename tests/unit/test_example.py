"""
Example unit test pattern for NEXUS.
Use this as a template for creating unit tests.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch


class TestExamplePatterns:
    """Example test patterns for NEXUS unit tests."""

    def test_simple_assertion(self):
        """Simple assertion example."""
        result = 2 + 2
        assert result == 4

    @pytest.mark.asyncio
    async def test_async_function(self):
        """Async test example."""
        async def async_add(a, b):
            return a + b

        result = await async_add(2, 3)
        assert result == 5

    def test_mocking(self):
        """Mocking example."""
        mock_obj = Mock()
        mock_obj.some_method.return_value = 42

        result = mock_obj.some_method()
        assert result == 42
        mock_obj.some_method.assert_called_once()

    @patch("builtins.print")
    def test_patching(self, mock_print):
        """Patching example."""
        print("Hello, World!")
        mock_print.assert_called_once_with("Hello, World!")

    @pytest.mark.asyncio
    async def test_async_mocking(self):
        """Async mocking example."""
        mock_async = AsyncMock()
        mock_async.async_method.return_value = "async result"

        result = await mock_async.async_method()
        assert result == "async result"
        mock_async.async_method.assert_called_once()


# Example of test organization
@pytest.mark.unit
class TestServicePattern:
    """Example service test pattern."""

    @pytest.fixture
    def sample_data(self):
        """Example fixture."""
        return {"key": "value"}

    def test_with_fixture(self, sample_data):
        """Test using fixture."""
        assert sample_data["key"] == "value"

    @pytest.mark.parametrize("input_val,expected", [(1, 2), (2, 4), (3, 6)])
    def test_parametrized(self, input_val, expected):
        """Parametrized test example."""
        result = input_val * 2
        assert result == expected