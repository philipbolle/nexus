"""
NEXUS Multi-Agent Framework - Performance Monitoring

Agent performance metrics collection, cost tracking, health checks, and alerting.
Provides real-time visibility into agent system performance and costs.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import statistics
from uuid import UUID
import uuid

from ..database import db
from ..agents.base import AgentStatus
from ..agents.registry import AgentRegistry, registry

logger = logging.getLogger(__name__)

# Special agent ID for system-level metrics
# Use existing 'system' agent ID from database
SYSTEM_AGENT_ID = "50563ee7-5ff8-4dd8-adb7-f544f426f7f9"


class MetricType(Enum):
    """Types of performance metrics."""
    LATENCY = "latency"
    COST = "cost"
    SUCCESS_RATE = "success_rate"
    TOKEN_USAGE = "token_usage"
    TOOL_USAGE = "tool_usage"
    ERROR_RATE = "error_rate"
    QUEUE_SIZE = "queue_size"
    MEMORY_USAGE = "memory_usage"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """Single performance metric measurement."""

    agent_id: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    tags: Dict[str, Any]


@dataclass
class Alert:
    """System alert."""

    id: str
    title: str
    message: str
    severity: AlertSeverity
    source: str  # 'agent', 'orchestrator', 'memory', 'tool'
    source_id: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class PerformanceMonitor:
    """
    Performance monitoring system for NEXUS agents.

    Collects metrics, detects anomalies, generates alerts, and provides
    performance dashboards and reporting.
    """

    def __init__(self):
        """Initialize the performance monitor."""
        self.registry: Optional[AgentRegistry] = None
        self.metrics_buffer: List[PerformanceMetric] = []
        self.alerts: Dict[str, Alert] = {}
        self._buffer_lock = asyncio.Lock()
        self._metrics_task: Optional[asyncio.Task] = None
        self._alert_check_task: Optional[asyncio.Task] = None
        self._running = False

    async def initialize(self, agent_registry: AgentRegistry) -> None:
        """
        Initialize the performance monitor.

        Args:
            agent_registry: Agent registry instance
        """
        if self._running:
            logger.warning("Performance monitor already initialized")
            return

        logger.info("Initializing performance monitor...")

        self.registry = agent_registry
        self._running = True

        # Start background tasks
        self._metrics_task = asyncio.create_task(self._collect_metrics_loop())
        self._alert_check_task = asyncio.create_task(self._check_alerts_loop())

        logger.info("Performance monitor initialized")

    async def shutdown(self) -> None:
        """
        Shutdown the performance monitor.

        Stops background tasks and flushes metrics buffer.
        """
        if not self._running:
            return

        logger.info("Shutting down performance monitor...")

        self._running = False

        # Stop background tasks
        if self._metrics_task:
            self._metrics_task.cancel()
            try:
                await self._metrics_task
            except asyncio.CancelledError:
                pass

        if self._alert_check_task:
            self._alert_check_task.cancel()
            try:
                await self._alert_check_task
            except asyncio.CancelledError:
                pass

        # Flush remaining metrics
        await self._flush_metrics_buffer()

        logger.info("Performance monitor shut down")

    async def record_metric(
        self,
        agent_id: str,
        metric_type: MetricType,
        value: float,
        tags: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a performance metric.

        Args:
            agent_id: Agent ID
            metric_type: Type of metric
            value: Metric value
            tags: Additional tags
        """
        # Convert agent_id to valid UUID string
        agent_id = self._ensure_uuid(agent_id)

        metric = PerformanceMetric(
            agent_id=agent_id,
            metric_type=metric_type,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {}
        )

        async with self._buffer_lock:
            self.metrics_buffer.append(metric)

        # Auto-flush if buffer is large
        if len(self.metrics_buffer) >= 100:
            await self._flush_metrics_buffer()

    async def record_agent_execution(
        self,
        agent_id: str,
        success: bool,
        execution_time_ms: float,
        tokens_used: Optional[int] = None,
        cost_usd: Optional[float] = None,
        tools_used: Optional[List[str]] = None
    ) -> None:
        """
        Record agent execution metrics.

        Args:
            agent_id: Agent ID
            success: Whether execution succeeded
            execution_time_ms: Execution time in milliseconds
            tokens_used: Tokens used
            cost_usd: Cost in USD
            tools_used: List of tools used
        """
        # Record latency metric
        await self.record_metric(
            agent_id,
            MetricType.LATENCY,
            execution_time_ms,
            {"success": success}
        )

        # Record success/failure metric
        await self.record_metric(
            agent_id,
            MetricType.SUCCESS_RATE,
            1.0 if success else 0.0
        )

        if tokens_used is not None:
            await self.record_metric(
                agent_id,
                MetricType.TOKEN_USAGE,
                float(tokens_used)
            )

        if cost_usd is not None:
            await self.record_metric(
                agent_id,
                MetricType.COST,
                cost_usd
            )

        if tools_used:
            for tool in tools_used:
                await self.record_metric(
                    agent_id,
                    MetricType.TOOL_USAGE,
                    1.0,
                    {"tool_name": tool}
                )

        # Check for anomalies
        await self._check_agent_anomalies(agent_id, execution_time_ms, success)

    async def get_agent_metrics(self, agent_id: str) -> Dict[str, Any]:
        """
        Get current metrics for a specific agent.

        Args:
            agent_id: Agent ID

        Returns:
            Agent metrics dictionary
        """
        if not self.registry:
            return {}

        agent = await self.registry.get_agent(agent_id)
        if not agent:
            return {}

        return agent.metrics

    async def create_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        source: str,
        source_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new alert.

        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity
            source: Source system
            source_id: Source ID (agent ID, session ID, etc.)
            metadata: Additional metadata

        Returns:
            Alert ID
        """
        alert_id = f"alert_{int(time.time())}_{len(self.alerts)}"
        alert = Alert(
            id=alert_id,
            title=title,
            message=message,
            severity=severity,
            source=source,
            source_id=source_id,
            metadata=metadata or {},
            created_at=datetime.now()
        )

        self.alerts[alert_id] = alert

        # Store in database
        await self._store_alert_in_db(alert)

        # Send notification for high severity alerts
        if severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
            await self._send_alert_notification(alert)

        logger.warning(f"Alert created: {title} ({severity.value})")
        return alert_id

    async def get_agent_performance(
        self,
        agent_id: str,
        time_range_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get performance statistics for an agent.

        Args:
            agent_id: Agent ID
            time_range_hours: Time range to analyze

        Returns:
            Performance statistics
        """
        start_time = datetime.now() - timedelta(hours=time_range_hours)
        agent_id = self._ensure_uuid(agent_id)

        # Get metrics from database
        metrics = await db.fetch_all(
            """
            SELECT metric_type, value, tags, timestamp
            FROM agent_performance_metrics
            WHERE agent_id = $1 AND timestamp >= $2
            ORDER BY timestamp
            """,
            agent_id,
            start_time
        )

        # Group metrics by type
        metrics_by_type: Dict[str, List[float]] = {}
        for row in metrics:
            metric_type = row["metric_type"]
            if metric_type not in metrics_by_type:
                metrics_by_type[metric_type] = []
            metrics_by_type[metric_type].append(float(row["value"]))

        # Calculate statistics
        stats: Dict[str, Any] = {
            "agent_id": agent_id,
            "time_range_hours": time_range_hours,
            "metric_count": len(metrics),
            "metrics": {}
        }

        for metric_type, values in metrics_by_type.items():
            if not values:
                continue

            stats["metrics"][metric_type] = {
                "count": len(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "min": min(values),
                "max": max(values),
                "stddev": statistics.stdev(values) if len(values) > 1 else 0
            }

        # Get success rate from agent_performance table
        perf_data = await db.fetch_one(
            """
            SELECT successful_requests, total_requests, avg_latency_ms
            FROM agent_performance
            WHERE agent_id = $1 AND date >= $2
            ORDER BY date DESC
            LIMIT 1
            """,
            agent_id,
            datetime.now().date() - timedelta(days=1)
        )

        if perf_data:
            total = perf_data["total_requests"] or 0
            successful = perf_data["successful_requests"] or 0
            stats["recent_performance"] = {
                "success_rate": successful / total if total > 0 else 0,
                "total_requests": total,
                "avg_latency_ms": float(perf_data["avg_latency_ms"] or 0)
            }

        return stats

    async def get_agent_performance_history(
        self,
        query: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Get agent performance history based on query parameters.

        Args:
            query: Dictionary with agent_id, start_date, end_date, metric

        Returns:
            List of agent performance records
        """
        agent_id = query.get("agent_id")
        start_date = query.get("start_date")
        end_date = query.get("end_date")
        metric = query.get("metric")

        if not agent_id:
            raise ValueError("agent_id is required")

        agent_id = self._ensure_uuid(agent_id)

        # Build query
        sql = """
            SELECT ap.*, a.name as agent_name
            FROM agent_performance ap
            JOIN agents a ON ap.agent_id = a.id
            WHERE ap.agent_id = $1
        """
        params = [agent_id]
        param_index = 2

        if start_date:
            sql += f" AND ap.date >= ${param_index}"
            params.append(start_date)
            param_index += 1

        if end_date:
            sql += f" AND ap.date <= ${param_index}"
            params.append(end_date)
            param_index += 1

        sql += " ORDER BY ap.date DESC LIMIT 100"

        rows = await db.fetch_all(sql, *params)

        # Transform to response format
        results = []
        for row in rows:
            result = {
                "agent_id": row["agent_id"],
                "agent_name": row["agent_name"],
                "date": row["date"],
                "total_requests": row["total_requests"] or 0,
                "successful_requests": row["successful_requests"] or 0,
                "failed_requests": (row["total_requests"] or 0) - (row["successful_requests"] or 0),
                "avg_latency_ms": float(row["avg_latency_ms"] or 0),
                "total_cost_usd": float(row["total_cost_usd"] or 0),
                "total_tokens": row["total_tokens"] or 0,
                "p50_latency_ms": row["p50_latency_ms"],
                "p95_latency_ms": row["p95_latency_ms"],
                "p99_latency_ms": row["p99_latency_ms"],
                "avg_user_rating": float(row["avg_user_rating"] or 0) if row["avg_user_rating"] is not None else None,
                "total_ratings": row["total_ratings"] or 0,
                "tools_used": row["tools_used"] or {}
            }

            # Add metric-specific value if requested
            if metric:
                if metric == "success_rate":
                    total = row["total_requests"] or 0
                    successful = row["successful_requests"] or 0
                    result["metric_value"] = successful / total if total > 0 else 0
                elif metric == "avg_latency":
                    result["metric_value"] = float(row["avg_latency_ms"] or 0)
                elif metric == "cost":
                    result["metric_value"] = float(row["total_cost_usd"] or 0)
                elif metric == "tokens":
                    result["metric_value"] = row["total_tokens"] or 0

            results.append(result)

        return results

    async def get_system_performance(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """
        Get overall system performance statistics.

        Args:
            time_range_hours: Time range to analyze

        Returns:
            System performance statistics
        """
        start_time = datetime.now() - timedelta(hours=time_range_hours)

        # Get aggregated metrics
        metrics = await db.fetch_all(
            """
            SELECT metric_type, AVG(value) as avg_value, COUNT(*) as count
            FROM agent_performance_metrics
            WHERE timestamp >= $1
            GROUP BY metric_type
            """,
            start_time
        )

        # Get agent counts
        agent_statuses = await self._get_agent_status_counts()

        # Get recent alerts
        recent_alerts = await self._get_recent_alerts(time_range_hours)

        # Get cost summary
        cost_summary = await self._get_cost_summary(start_time)

        return {
            "time_range_hours": time_range_hours,
            "timestamp": datetime.now().isoformat(),
            "agent_statuses": agent_statuses,
            "metrics": {
                row["metric_type"]: {
                    "average": float(row["avg_value"] or 0),
                    "sample_count": row["count"]
                }
                for row in metrics
            },
            "cost_summary": cost_summary,
            "recent_alerts": recent_alerts,
            "active_alerts": len([a for a in self.alerts.values() if not a.resolved])
        }

    async def get_agent_errors(
        self,
        agent_id: str,
        resolved: Optional[bool] = None,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get errors for a specific agent.

        Args:
            agent_id: Agent ID
            resolved: Filter by resolved status
            severity: Filter by severity

        Returns:
            List of error dictionaries
        """
        # For now, return empty list - implement database query later
        return []

    async def get_cost_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get cost report for agents.

        Args:
            start_date: Start date (default: beginning of month)
            end_date: End date (default: now)

        Returns:
            Cost report
        """
        if not start_date:
            start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0)
        if not end_date:
            end_date = datetime.now()

        # Get agent costs
        agent_costs = await db.fetch_all(
            """
            SELECT agent_id, SUM(total_cost_usd) as total_cost,
                   SUM(total_tokens) as total_tokens
            FROM agent_performance
            WHERE date >= $1 AND date <= $2
            GROUP BY agent_id
            ORDER BY total_cost DESC
            """,
            start_date.date(),
            end_date.date()
        )

        # Get daily cost trend
        daily_costs = await db.fetch_all(
            """
            SELECT date, SUM(total_cost_usd) as daily_cost,
                   SUM(total_tokens) as daily_tokens
            FROM agent_performance
            WHERE date >= $1 AND date <= $2
            GROUP BY date
            ORDER BY date
            """,
            start_date.date(),
            end_date.date()
        )

        # Calculate totals
        total_cost = sum(float(row["total_cost"] or 0) for row in agent_costs)
        total_tokens = sum(row["total_tokens"] or 0 for row in agent_costs)

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_cost_usd": total_cost,
            "total_tokens": total_tokens,
            "cost_per_token": total_cost / total_tokens if total_tokens > 0 else 0,
            "agent_breakdown": [
                {
                    "agent_id": row["agent_id"],
                    "cost_usd": float(row["total_cost"] or 0),
                    "tokens": row["total_tokens"] or 0,
                    "cost_percentage": (
                        float(row["total_cost"] or 0) / total_cost * 100
                        if total_cost > 0 else 0
                    )
                }
                for row in agent_costs
            ],
            "daily_trend": [
                {
                    "date": row["date"].isoformat(),
                    "cost_usd": float(row["daily_cost"] or 0),
                    "tokens": row["daily_tokens"] or 0
                }
                for row in daily_costs
            ]
        }

    async def get_alerts(
        self,
        severity: Optional[str] = None,
        resolved: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Get alerts with optional filtering.

        Args:
            severity: Filter by severity level
            resolved: Filter by resolved status

        Returns:
            List of alert dictionaries
        """
        query = """
            SELECT id, title, message, severity, source, source_id,
                   created_at, acknowledged, resolved, metadata
            FROM system_alerts
            WHERE 1=1
        """
        params = []
        param_index = 1

        if severity:
            query += f" AND severity = ${param_index}"
            params.append(severity)
            param_index += 1

        if resolved is not None:
            query += f" AND resolved = ${param_index}"
            params.append(resolved)
            param_index += 1

        query += " ORDER BY created_at DESC LIMIT 100"

        rows = await db.fetch_all(query, *params)

        return [
            {
                "id": row["id"],
                "title": row["title"],
                "message": row["message"],
                "severity": row["severity"],
                "source": row["source"],
                "source_id": row["source_id"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "acknowledged": row["acknowledged"],
                "resolved": row["resolved"],
                "metadata": row["metadata"]
            }
            for row in rows
        ]

    async def acknowledge_alert(self, alert_id: str) -> bool:
        """
        Acknowledge an alert.

        Args:
            alert_id: Alert ID

        Returns:
            True if successful
        """
        if alert_id not in self.alerts:
            return False

        alert = self.alerts[alert_id]
        alert.acknowledged = True
        alert.acknowledged_at = datetime.now()

        # Update database
        await self._update_alert_in_db(alert)

        logger.info(f"Alert acknowledged: {alert_id}")
        return True

    async def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an alert.

        Args:
            alert_id: Alert ID

        Returns:
            True if successful
        """
        if alert_id not in self.alerts:
            return False

        alert = self.alerts[alert_id]
        alert.resolved = True
        alert.resolved_at = datetime.now()

        # Update database
        await self._update_alert_in_db(alert)

        logger.info(f"Alert resolved: {alert_id}")
        return True

    # ============ Internal Methods ============

    async def _collect_metrics_loop(self) -> None:
        """Background task to collect metrics periodically."""
        logger.info("Metrics collection loop started")

        while self._running:
            try:
                # Wait before next collection
                await asyncio.sleep(60)  # Collect every minute

                # Collect system metrics
                await self._collect_system_metrics()

                # Flush metrics buffer
                await self._flush_metrics_buffer()

            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(10)  # Wait 10 seconds on error

        logger.info("Metrics collection loop stopped")

    async def _check_alerts_loop(self) -> None:
        """Background task to check for alert conditions."""
        logger.info("Alert check loop started")

        while self._running:
            try:
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds

                # Check for agent issues
                await self._check_agent_alerts()

                # Check for system issues
                await self._check_system_alerts()

                # Clean up old resolved alerts
                await self._cleanup_old_alerts()

            except Exception as e:
                logger.error(f"Error in alert check: {e}")
                await asyncio.sleep(10)  # Wait 10 seconds on error

        logger.info("Alert check loop stopped")

    async def _collect_system_metrics(self) -> None:
        """Collect system-wide metrics."""
        if not self.registry:
            return

        # Get agent status counts
        agents = await self.registry.list_agents(include_status=True)
        status_counts = {
            "total": len(agents),
            "idle": 0,
            "processing": 0,
            "error": 0,
            "stopped": 0
        }

        for agent in agents:
            # agent is a BaseAgent object, not a dict
            status_obj = getattr(agent, 'status', None)
            if status_obj is None:
                continue
            # Handle AgentStatus enum or string
            if hasattr(status_obj, 'value'):
                status = status_obj.value.lower()
            else:
                status = str(status_obj).lower()

            if status == "idle":
                status_counts["idle"] += 1
            elif status == "processing":
                status_counts["processing"] += 1
            elif status == "error":
                status_counts["error"] += 1
            elif status == "stopped":
                status_counts["stopped"] += 1

        # Record queue size (if orchestrator available)
        # TODO: Integrate with orchestrator queue metrics

        # Record system metrics - use SYSTEM_AGENT_ID directly to avoid UUID conversion issues
        for status, count in status_counts.items():
            await self.record_metric(
                SYSTEM_AGENT_ID,
                MetricType.QUEUE_SIZE,
                float(count),
                {"status": status, "metric": "agent_count"}
            )

    def _ensure_uuid(self, agent_id: str) -> str:
        """Convert agent_id to valid UUID string, handling special 'system' value."""
        # Handle UUID objects
        if isinstance(agent_id, UUID):
            return str(agent_id)

        # Handle string 'system'
        if agent_id == "system":
            return SYSTEM_AGENT_ID

        # If already a valid UUID string, return as-is
        try:
            UUID(agent_id)
            return agent_id
        except ValueError:
            # Generate deterministic UUID from string
            import uuid
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, agent_id))

    async def _flush_metrics_buffer(self) -> None:
        """Flush metrics buffer to database."""
        if not self.metrics_buffer:
            return

        async with self._buffer_lock:
            buffer = self.metrics_buffer.copy()
            self.metrics_buffer.clear()

        if not buffer:
            return

        logger.debug(f"Flushing {len(buffer)} metrics to database")

        # Batch insert metrics
        try:
            # Prepare values for batch insert
            values = []
            for metric in buffer:
                # Convert tags dict to JSON string for database storage
                tags_json = json.dumps(metric.tags) if metric.tags else "{}"
                values.append((
                    self._ensure_uuid(metric.agent_id),
                    metric.metric_type.value,
                    metric.value,
                    metric.timestamp,
                    tags_json
                ))

            # Use executemany for batch insert
            # Note: asyncpg doesn't have native executemany, so we'll do individual inserts
            # In production, consider using copy_from or unnest for better performance
            for agent_id, metric_type, value, timestamp, tags in values:
                await db.execute(
                    """
                    INSERT INTO agent_performance_metrics
                    (agent_id, metric_type, value, timestamp, tags)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    agent_id,
                    metric_type,
                    value,
                    timestamp,
                    tags
                )

            logger.debug(f"Flushed {len(buffer)} metrics")

        except Exception as e:
            logger.error(f"Failed to flush metrics: {e}")
            # Put metrics back in buffer for retry
            async with self._buffer_lock:
                self.metrics_buffer.extend(buffer)

    async def _check_agent_anomalies(
        self,
        agent_id: str,
        execution_time_ms: float,
        success: bool
    ) -> None:
        """Check for anomalies in agent execution."""
        # Check for high latency
        latency_threshold = 10000  # 10 seconds
        if execution_time_ms > latency_threshold:
            await self.create_alert(
                title=f"High latency for agent {agent_id}",
                message=f"Agent execution took {execution_time_ms:.0f}ms",
                severity=AlertSeverity.WARNING,
                source="agent",
                source_id=agent_id,
                metadata={
                    "execution_time_ms": execution_time_ms,
                    "threshold": latency_threshold
                }
            )

        # Check for repeated failures
        if not success:
            # Get recent failure rate
            recent_failures = await self._get_recent_failure_rate(agent_id)
            if recent_failures > 0.5:  # More than 50% failures in last 10 executions
                await self.create_alert(
                    title=f"High failure rate for agent {agent_id}",
                    message=f"Agent has {recent_failures*100:.0f}% failure rate",
                    severity=AlertSeverity.ERROR,
                    source="agent",
                    source_id=agent_id,
                    metadata={"failure_rate": recent_failures}
                )

    async def _check_agent_alerts(self) -> None:
        """Check for agent-related alert conditions."""
        if not self.registry:
            return

        agents = await self.registry.list_agents(include_status=True)

        for agent_obj in agents:
            # agent_obj is a BaseAgent object, not a dict
            agent_id = getattr(agent_obj, 'agent_id', None)
            if not agent_id:
                continue

            agent_name = getattr(agent_obj, 'name', 'Unknown')

            # Get status
            status_obj = getattr(agent_obj, 'status', None)
            if status_obj is None:
                status = "unknown"
            elif hasattr(status_obj, 'value'):
                status = status_obj.value.lower()
            else:
                status = str(status_obj).lower()

            # Check for agents in error state
            if status == "error":
                await self.create_alert(
                    title=f"Agent {agent_name} in error state",
                    message=f"Agent {agent_name} is in error state and may need intervention",
                    severity=AlertSeverity.ERROR,
                    source="agent",
                    source_id=agent_id,
                    metadata={"agent_name": agent_name, "status": status}
                )

            # Check for low success rate
            # Note: metrics are not stored on agent objects, need to fetch from database
            # For now, use default success rate
            success_rate = 1.0
            if success_rate < 0.7:  # Less than 70% success rate
                await self.create_alert(
                    title=f"Low success rate for agent {agent_name}",
                    message=f"Agent success rate is {success_rate*100:.0f}%",
                    severity=AlertSeverity.WARNING,
                    source="agent",
                    source_id=agent_id,
                    metadata={
                        "agent_name": agent_name,
                        "success_rate": success_rate,
                        "threshold": 0.7
                    }
                )

    async def _check_system_alerts(self) -> None:
        """Check for system-wide alert conditions."""
        # Check for high error rate across all agents
        # Check for cost overruns
        # Check for memory usage
        # TODO: Implement system-wide alert checks
        pass

    async def _cleanup_old_alerts(self) -> None:
        """Clean up old resolved alerts."""
        alert_ids_to_remove = []

        for alert_id, alert in self.alerts.items():
            # Remove alerts resolved more than 7 days ago
            if alert.resolved and alert.resolved_at:
                if datetime.now() - alert.resolved_at > timedelta(days=7):
                    alert_ids_to_remove.append(alert_id)

        # Remove old alerts
        for alert_id in alert_ids_to_remove:
            self.alerts.pop(alert_id, None)

    async def _store_alert_in_db(self, alert: Alert) -> None:
        """Store alert in database."""
        try:
            await db.execute(
                """
                INSERT INTO system_alerts
                (id, title, message, severity, source, source_id,
                 metadata, created_at, acknowledged, resolved)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                alert.id,
                alert.title,
                alert.message,
                alert.severity.value,
                alert.source,
                alert.source_id,
                alert.metadata,
                alert.created_at,
                alert.acknowledged,
                alert.resolved
            )
        except Exception as e:
            logger.error(f"Failed to store alert in database: {e}")

    async def _update_alert_in_db(self, alert: Alert) -> None:
        """Update alert in database."""
        try:
            await db.execute(
                """
                UPDATE system_alerts SET
                    acknowledged = $2,
                    acknowledged_at = $3,
                    resolved = $4,
                    resolved_at = $5,
                    updated_at = NOW()
                WHERE id = $1
                """,
                alert.id,
                alert.acknowledged,
                alert.acknowledged_at,
                alert.resolved,
                alert.resolved_at
            )
        except Exception as e:
            logger.error(f"Failed to update alert in database: {e}")

    async def _send_alert_notification(self, alert: Alert) -> None:
        """Send alert notification via configured notification system."""
        # TODO: Integrate with ntfy.sh or other notification system
        logger.info(f"ALERT [{alert.severity.value}]: {alert.title} - {alert.message}")

    async def _get_agent_status_counts(self) -> Dict[str, int]:
        """Get counts of agents by status."""
        if not self.registry:
            return {}

        agents = await self.registry.list_agents(include_status=True)

        counts = {
            "total": len(agents),
            "idle": 0,
            "processing": 0,
            "error": 0,
            "stopped": 0
        }

        for agent in agents:
            # agent is a BaseAgent object, not a dict
            status_obj = getattr(agent, 'status', None)
            if status_obj is None:
                continue
            # Handle AgentStatus enum or string
            if hasattr(status_obj, 'value'):
                status = status_obj.value.lower()
            else:
                status = str(status_obj).lower()

            if status == "idle":
                counts["idle"] += 1
            elif status == "processing":
                counts["processing"] += 1
            elif status == "error":
                counts["error"] += 1
            elif status == "stopped":
                counts["stopped"] += 1

        return counts

    async def _get_recent_alerts(self, time_range_hours: int) -> List[Dict[str, Any]]:
        """Get recent alerts from database."""
        start_time = datetime.now() - timedelta(hours=time_range_hours)

        rows = await db.fetch_all(
            """
            SELECT id, title, message, severity, source, source_id,
                   created_at, acknowledged, resolved
            FROM system_alerts
            WHERE created_at >= $1
            ORDER BY created_at DESC
            LIMIT 20
            """,
            start_time
        )

        return [
            {
                "id": row["id"],
                "title": row["title"],
                "severity": row["severity"],
                "source": row["source"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "acknowledged": row["acknowledged"],
                "resolved": row["resolved"]
            }
            for row in rows
        ]

    async def _get_cost_summary(self, start_time: datetime) -> Dict[str, Any]:
        """Get cost summary for time period."""
        rows = await db.fetch_all(
            """
            SELECT SUM(total_cost_usd) as total_cost,
                   SUM(total_tokens) as total_tokens,
                   COUNT(DISTINCT agent_id) as agents_with_cost
            FROM agent_performance
            WHERE date >= $1
            """,
            start_time.date()
        )

        if not rows or not rows[0]:
            return {"total_cost_usd": 0, "total_tokens": 0, "agents_with_cost": 0}

        row = rows[0]
        return {
            "total_cost_usd": float(row["total_cost"] or 0),
            "total_tokens": row["total_tokens"] or 0,
            "agents_with_cost": row["agents_with_cost"] or 0
        }

    async def _get_recent_failure_rate(self, agent_id: str) -> float:
        """Get recent failure rate for an agent."""
        agent_id = self._ensure_uuid(agent_id)
        rows = await db.fetch_all(
            """
            SELECT successful_requests, total_requests
            FROM agent_performance
            WHERE agent_id = $1
            ORDER BY date DESC
            LIMIT 3
            """,
            agent_id
        )

        if not rows:
            return 0.0

        total_requests = 0
        successful_requests = 0

        for row in rows:
            total_requests += row["total_requests"] or 0
            successful_requests += row["successful_requests"] or 0

        if total_requests == 0:
            return 0.0

        failure_rate = 1.0 - (successful_requests / total_requests)
        return failure_rate


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


async def get_performance_monitor() -> PerformanceMonitor:
    """Dependency for FastAPI routes."""
    return performance_monitor