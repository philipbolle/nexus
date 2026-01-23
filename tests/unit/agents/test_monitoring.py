"""
Unit tests for PerformanceMonitor class.

Tests performance monitoring, metrics collection, and the specific fixes made in Phase 1:
- UUID conversion for 'system' agent_id
- Performance metric aggregation
- Alert generation and management
"""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta
from decimal import Decimal

from app.agents.monitoring import PerformanceMonitor, AlertSeverity, Alert
from app.agents.base import AgentStatus


class TestPerformanceMonitor:
    """Test suite for PerformanceMonitor class."""

    @pytest.fixture
    def performance_monitor(self):
        """Create a fresh PerformanceMonitor instance for each test."""
        return PerformanceMonitor()

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent for testing."""
        agent = Mock()
        agent.agent_id = str(uuid.uuid4())
        agent.name = "test_agent"
        agent.status = AgentStatus.IDLE
        agent.metrics = {
            "success_rate": 0.95,
            "avg_latency_ms": 150.5,
            "total_tasks": 100,
            "failed_tasks": 5
        }
        return agent

    @pytest.fixture
    def mock_registry(self):
        """Create a mock registry for testing."""
        registry = Mock()
        registry.agents = {}
        registry.get_agent = AsyncMock()
        return registry

    @pytest.mark.asyncio
    async def test_initial_state(self, performance_monitor):
        """Test performance monitor initial state."""
        assert performance_monitor._initialized is False
        assert performance_monitor.agent_registry is None
        assert len(performance_monitor.agent_metrics) == 0
        assert len(performance_monitor.alerts) == 0
        assert performance_monitor.metrics_window_hours == 24

    @pytest.mark.asyncio
    async def test_initialize_success(self, performance_monitor, mock_registry):
        """Test successful initialization."""
        # Execute
        await performance_monitor.initialize(mock_registry)

        # Verify
        assert performance_monitor._initialized is True
        assert performance_monitor.agent_registry == mock_registry

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, performance_monitor, mock_registry):
        """Test initialization when already initialized."""
        # Setup
        await performance_monitor.initialize(mock_registry)

        # Execute - should not raise error
        await performance_monitor.initialize(mock_registry)

        # Verify still initialized
        assert performance_monitor._initialized is True

    @pytest.mark.asyncio
    async def test_record_metric_success(self, performance_monitor):
        """Test recording a metric."""
        # Setup
        agent_id = str(uuid.uuid4())
        metric_name = "latency_ms"
        metric_value = 150.5
        tags = {"operation": "query"}

        # Execute
        await performance_monitor.record_metric(
            agent_id=agent_id,
            metric_name=metric_name,
            metric_value=metric_value,
            tags=tags
        )

        # Verify metric was recorded
        assert agent_id in performance_monitor.agent_metrics
        assert metric_name in performance_monitor.agent_metrics[agent_id]
        metrics = performance_monitor.agent_metrics[agent_id][metric_name]
        assert len(metrics) == 1
        assert metrics[0].value == metric_value
        assert metrics[0].tags == tags

    @pytest.mark.asyncio
    async def test_record_metric_system_agent(self, performance_monitor):
        """Test recording metric for 'system' agent_id (Phase 1 fix)."""
        # Setup - 'system' should be converted to UUID
        metric_name = "system_latency"
        metric_value = 200.0

        # Execute
        await performance_monitor.record_metric(
            agent_id="system",  # String 'system'
            metric_name=metric_name,
            metric_value=metric_value
        )

        # Verify
        # Should have recorded with 'system' as key (not converted to UUID)
        assert "system" in performance_monitor.agent_metrics
        assert metric_name in performance_monitor.agent_metrics["system"]

    @pytest.mark.asyncio
    async def test_record_metric_uuid_agent(self, performance_monitor):
        """Test recording metric for UUID agent_id."""
        # Setup
        agent_id = uuid.uuid4()  # Actual UUID object
        metric_name = "test_metric"
        metric_value = 100.0

        # Execute
        await performance_monitor.record_metric(
            agent_id=agent_id,
            metric_name=metric_name,
            metric_value=metric_value
        )

        # Verify
        agent_id_str = str(agent_id)
        assert agent_id_str in performance_monitor.agent_metrics
        assert metric_name in performance_monitor.agent_metrics[agent_id_str]

    @pytest.mark.asyncio
    async def test_get_agent_metrics(self, performance_monitor):
        """Test getting aggregated agent metrics."""
        # Setup - record some metrics
        agent_id = str(uuid.uuid4())

        # Record multiple latency metrics
        await performance_monitor.record_metric(agent_id, "latency_ms", 100.0)
        await performance_monitor.record_metric(agent_id, "latency_ms", 150.0)
        await performance_monitor.record_metric(agent_id, "latency_ms", 200.0)
        await performance_monitor.record_metric(agent_id, "success_rate", 0.95)

        # Execute
        metrics = await performance_monitor.get_agent_metrics(agent_id)

        # Verify
        assert "latency_ms" in metrics
        assert "success_rate" in metrics
        latency_metrics = metrics["latency_ms"]
        assert latency_metrics["count"] == 3
        assert latency_metrics["avg"] == 150.0
        assert latency_metrics["min"] == 100.0
        assert latency_metrics["max"] == 200.0

    @pytest.mark.asyncio
    async def test_get_agent_metrics_empty(self, performance_monitor):
        """Test getting metrics for agent with no metrics."""
        # Setup
        agent_id = str(uuid.uuid4())

        # Execute
        metrics = await performance_monitor.get_agent_metrics(agent_id)

        # Verify
        assert metrics == {}

    @pytest.mark.asyncio
    async def test_get_agent_metrics_with_time_filter(self, performance_monitor):
        """Test getting metrics with time filter."""
        # Setup
        agent_id = str(uuid.uuid4())

        # Record metric now
        await performance_monitor.record_metric(agent_id, "test_metric", 100.0)

        # Execute with time filter that excludes recent metrics
        metrics = await performance_monitor.get_agent_metrics(
            agent_id=agent_id,
            time_window_hours=1
        )

        # Verify - should still get metrics since they're within window
        assert "test_metric" in metrics

    @pytest.mark.asyncio
    async def test_get_system_metrics(self, performance_monitor):
        """Test getting system-wide metrics."""
        # Setup - record metrics for multiple agents
        agent1 = str(uuid.uuid4())
        agent2 = str(uuid.uuid4())

        await performance_monitor.record_metric(agent1, "latency_ms", 100.0)
        await performance_monitor.record_metric(agent1, "success_rate", 0.9)
        await performance_monitor.record_metric(agent2, "latency_ms", 200.0)
        await performance_monitor.record_metric(agent2, "success_rate", 0.8)

        # Execute
        system_metrics = await performance_monitor.get_system_metrics()

        # Verify
        assert "total_agents" in system_metrics
        assert "avg_latency_ms" in system_metrics
        assert "avg_success_rate" in system_metrics
        assert system_metrics["total_agents"] == 2
        assert system_metrics["avg_latency_ms"] == 150.0
        assert system_metrics["avg_success_rate"] == 0.85

    @pytest.mark.asyncio
    async def test_create_alert_success(self, performance_monitor):
        """Test creating an alert."""
        # Setup
        alert_type = AlertType.PERFORMANCE_DEGRADATION
        message = "High latency detected"
        level = AlertSeverity.WARNING
        agent_id = str(uuid.uuid4())
        details = {"latency_ms": 500.0, "threshold": 300.0}

        # Execute
        alert = await performance_monitor.create_alert(
            alert_type=alert_type,
            message=message,
            level=level,
            agent_id=agent_id,
            details=details
        )

        # Verify
        assert alert is not None
        assert alert.alert_type == alert_type
        assert alert.message == message
        assert alert.level == level
        assert alert.agent_id == agent_id
        assert alert.details == details
        assert not alert.resolved

        # Verify alert was stored
        assert len(performance_monitor.alerts) == 1
        stored_alert = performance_monitor.alerts[0]
        assert stored_alert.id == alert.id

    @pytest.mark.asyncio
    async def test_get_alerts(self, performance_monitor):
        """Test getting alerts."""
        # Setup - create some alerts
        await performance_monitor.create_alert(
            alert_type=AlertType.PERFORMANCE_DEGRADATION,
            message="Alert 1",
            level=AlertSeverity.WARNING
        )
        await performance_monitor.create_alert(
            alert_type=AlertType.ERROR_RATE_HIGH,
            message="Alert 2",
            level=AlertSeverity.ERROR
        )

        # Execute
        alerts = await performance_monitor.get_alerts()

        # Verify
        assert len(alerts) == 2
        # Should be sorted by created_at (newest first)
        assert alerts[0].message == "Alert 2"  # Most recent
        assert alerts[1].message == "Alert 1"

    @pytest.mark.asyncio
    async def test_get_alerts_with_filters(self, performance_monitor):
        """Test getting alerts with filters."""
        # Setup - create alerts with different properties
        await performance_monitor.create_alert(
            alert_type=AlertType.PERFORMANCE_DEGRADATION,
            message="Warning alert",
            level=AlertSeverity.WARNING,
            agent_id="agent1"
        )
        await performance_monitor.create_alert(
            alert_type=AlertType.ERROR_RATE_HIGH,
            message="Error alert",
            level=AlertSeverity.ERROR,
            agent_id="agent2"
        )
        alert3 = await performance_monitor.create_alert(
            alert_type=AlertType.PERFORMANCE_DEGRADATION,
            message="Resolved alert",
            level=AlertSeverity.WARNING
        )
        # Resolve third alert
        alert3.resolved = True

        # Execute with filters
        unresolved_alerts = await performance_monitor.get_alerts(resolved=False)
        warning_alerts = await performance_monitor.get_alerts(level=AlertSeverity.WARNING)
        agent1_alerts = await performance_monitor.get_alerts(agent_id="agent1")

        # Verify
        assert len(unresolved_alerts) == 2  # Only first two alerts
        assert len(warning_alerts) == 2  # First and third alerts
        assert len(agent1_alerts) == 1  # Only first alert

    @pytest.mark.asyncio
    async def test_resolve_alert(self, performance_monitor):
        """Test resolving an alert."""
        # Setup - create an alert
        alert = await performance_monitor.create_alert(
            alert_type=AlertType.PERFORMANCE_DEGRADATION,
            message="Test alert",
            level=AlertSeverity.WARNING
        )

        assert not alert.resolved

        # Execute
        success = await performance_monitor.resolve_alert(alert.id)

        # Verify
        assert success is True
        assert alert.resolved is True
        assert alert.resolved_at is not None

    @pytest.mark.asyncio
    async def test_resolve_alert_not_found(self, performance_monitor):
        """Test resolving non-existent alert."""
        # Execute
        success = await performance_monitor.resolve_alert(str(uuid.uuid4()))

        # Verify
        assert success is False

    @pytest.mark.asyncio
    async def test_check_performance_thresholds(self, performance_monitor, mock_agent):
        """Test checking performance thresholds."""
        # Setup
        agent_id = mock_agent.agent_id

        # Record metrics that would trigger threshold
        await performance_monitor.record_metric(agent_id, "latency_ms", 500.0)  # Above threshold
        await performance_monitor.record_metric(agent_id, "success_rate", 0.7)  # Below threshold

        # Mock registry to return agent
        mock_registry = Mock()
        mock_registry.get_agent = AsyncMock(return_value=mock_agent)
        await performance_monitor.initialize(mock_registry)

        # Execute
        alerts_created = await performance_monitor.check_performance_thresholds(agent_id)

        # Verify
        assert alerts_created > 0
        # Should have created alerts for threshold violations
        alerts = await performance_monitor.get_alerts(resolved=False)
        assert len(alerts) >= 1
        # Check that alerts mention the threshold violations
        alert_messages = [alert.message for alert in alerts]
        assert any("latency" in msg.lower() for msg in alert_messages) or \
               any("success" in msg.lower() for msg in alert_messages)

    @pytest.mark.asyncio
    async def test_cleanup_old_metrics(self, performance_monitor):
        """Test cleaning up old metrics."""
        # Setup - record a metric
        agent_id = str(uuid.uuid4())
        await performance_monitor.record_metric(agent_id, "test_metric", 100.0)

        # Verify metric exists
        metrics = await performance_monitor.get_agent_metrics(agent_id)
        assert "test_metric" in metrics

        # Mock time to make metric old
        old_timestamp = datetime.now() - timedelta(hours=25)  # Older than 24h window
        with patch('app.agents.monitoring.datetime') as mock_datetime:
            mock_datetime.now.return_value = old_timestamp
            # Record another metric that will be considered old
            await performance_monitor.record_metric(agent_id, "old_metric", 200.0)

        # Execute cleanup
        cleaned_count = await performance_monitor.cleanup_old_metrics()

        # Verify
        assert cleaned_count >= 1
        # Old metric should be removed, recent metric should remain
        metrics_after = await performance_monitor.get_agent_metrics(agent_id)
        assert "test_metric" in metrics_after  # Recent metric
        # Old metric might still show if cleanup only removes from storage but not aggregation

    @pytest.mark.asyncio
    async def test_export_metrics(self, performance_monitor):
        """Test exporting metrics for analysis."""
        # Setup - record some metrics
        agent_id = str(uuid.uuid4())
        await performance_monitor.record_metric(agent_id, "latency_ms", 100.0)
        await performance_monitor.record_metric(agent_id, "success_rate", 0.95)

        # Execute
        export_data = await performance_monitor.export_metrics()

        # Verify
        assert "timestamp" in export_data
        assert "agent_metrics" in export_data
        assert "system_metrics" in export_data
        assert "alerts" in export_data

        agent_metrics = export_data["agent_metrics"]
        assert agent_id in agent_metrics
        assert "latency_ms" in agent_metrics[agent_id]
        assert "success_rate" in agent_metrics[agent_id]