"""
NEXUS Monitoring Integration

Connects the monitoring system to API endpoints and provides
real-time monitoring, alerting, and performance tracking.
"""

import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
import logging

from .logging_config import get_logger, log_error
from .agents.monitoring import performance_monitor, AlertSeverity
from .database import db

logger = get_logger(__name__)


class MonitoringIntegration:
    """
    Integrates monitoring system with API endpoints.

    Features:
    - Request/response monitoring
    - Error tracking and alerting
    - Performance metrics collection
    - Health check integration
    - Cost tracking
    """

    def __init__(self):
        """Initialize monitoring integration."""
        self.request_metrics: Dict[str, List[float]] = {}
        self.error_counts: Dict[str, int] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def initialize(self) -> None:
        """Initialize monitoring integration."""
        if self._running:
            logger.warning("Monitoring integration already initialized")
            return

        logger.info("Initializing monitoring integration...")
        self._running = True

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_old_metrics())

        logger.info("Monitoring integration initialized")

    async def shutdown(self) -> None:
        """Shutdown monitoring integration."""
        if not self._running:
            return

        logger.info("Shutting down monitoring integration...")
        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("Monitoring integration shut down")

    async def track_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Track API request metrics.

        Args:
            endpoint: API endpoint
            method: HTTP method
            status_code: HTTP status code
            duration_ms: Request duration in milliseconds
            user_id: User ID (if available)
            agent_id: Agent ID (if request was processed by agent)
        """
        try:
            # Record request metrics
            key = f"{method}:{endpoint}"
            if key not in self.request_metrics:
                self.request_metrics[key] = []

            self.request_metrics[key].append(duration_ms)

            # Record to performance monitor if agent is involved
            if agent_id:
                await performance_monitor.record_agent_execution(
                    agent_id=agent_id,
                    success=status_code < 400,
                    execution_time_ms=duration_ms,
                    tokens_used=kwargs.get("tokens_used"),
                    cost_usd=kwargs.get("cost_usd"),
                    tools_used=kwargs.get("tools_used"),
                )

            # Record system metrics for non-agent requests
            else:
                await performance_monitor.record_metric(
                    agent_id="system",
                    metric_type="latency",
                    value=duration_ms,
                    tags={
                        "endpoint": endpoint,
                        "method": method,
                        "status_code": status_code,
                        "success": status_code < 400,
                        "user_id": user_id,
                    }
                )

            # Check for performance anomalies
            await self._check_performance_anomalies(endpoint, method, duration_ms, status_code)

            # Track error rates
            if status_code >= 400:
                error_key = f"{method}:{endpoint}:{status_code}"
                self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
                await self._check_error_rates()

        except Exception as e:
            logger.error(f"Failed to track request: {e}", exc_info=True)

    async def track_error(
        self,
        error: Exception,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Track error for monitoring and alerting.

        Args:
            error: Exception that occurred
            endpoint: API endpoint where error occurred
            method: HTTP method
            user_id: User ID (if available)
            agent_id: Agent ID (if error occurred in agent)
        """
        try:
            # Create alert for serious errors
            severity = self._determine_error_severity(error, endpoint, method)

            if severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
                await performance_monitor.create_alert(
                    title=f"API Error: {error.__class__.__name__}",
                    message=f"Error in {method} {endpoint}: {str(error)}",
                    severity=severity,
                    source="api" if not agent_id else "agent",
                    source_id=agent_id,
                    metadata={
                        "endpoint": endpoint,
                        "method": method,
                        "user_id": user_id,
                        "error_type": error.__class__.__name__,
                        "error_message": str(error),
                        **kwargs,
                    }
                )

            # Record error metric
            await performance_monitor.record_metric(
                agent_id=agent_id or "system",
                metric_type="error_rate",
                value=1.0,
                tags={
                    "endpoint": endpoint,
                    "method": method,
                    "error_type": error.__class__.__name__,
                    "user_id": user_id,
                }
            )

        except Exception as e:
            logger.error(f"Failed to track error: {e}", exc_info=True)

    async def get_api_metrics(
        self,
        time_range_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get API metrics for monitoring dashboard.

        Args:
            time_range_hours: Time range to analyze

        Returns:
            API metrics dictionary
        """
        try:
            start_time = datetime.now() - timedelta(hours=time_range_hours)

            # Get request counts by endpoint
            request_counts = await db.fetch_all(
                """
                SELECT endpoint, method, status_code, COUNT(*) as count,
                       AVG(duration_ms) as avg_duration,
                       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_duration
                FROM api_request_logs
                WHERE timestamp >= $1
                GROUP BY endpoint, method, status_code
                ORDER BY count DESC
                LIMIT 50
                """,
                start_time
            )

            # Get error rates
            error_rates = await db.fetch_all(
                """
                SELECT endpoint, method,
                       COUNT(*) as total_requests,
                       SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as error_count,
                       (SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as error_percentage
                FROM api_request_logs
                WHERE timestamp >= $1
                GROUP BY endpoint, method
                HAVING COUNT(*) > 10
                ORDER BY error_percentage DESC
                LIMIT 20
                """,
                start_time
            )

            # Get slow endpoints
            slow_endpoints = await db.fetch_all(
                """
                SELECT endpoint, method,
                       AVG(duration_ms) as avg_duration,
                       COUNT(*) as request_count
                FROM api_request_logs
                WHERE timestamp >= $1 AND duration_ms > 1000
                GROUP BY endpoint, method
                ORDER BY avg_duration DESC
                LIMIT 20
                """,
                start_time
            )

            # Get hourly request volume
            hourly_volume = await db.fetch_all(
                """
                SELECT DATE_TRUNC('hour', timestamp) as hour,
                       COUNT(*) as request_count,
                       AVG(duration_ms) as avg_duration
                FROM api_request_logs
                WHERE timestamp >= $1
                GROUP BY DATE_TRUNC('hour', timestamp)
                ORDER BY hour
                """,
                start_time
            )

            return {
                "time_range_hours": time_range_hours,
                "request_counts": [
                    {
                        "endpoint": row["endpoint"],
                        "method": row["method"],
                        "status_code": row["status_code"],
                        "count": row["count"],
                        "avg_duration_ms": float(row["avg_duration"] or 0),
                        "p95_duration_ms": float(row["p95_duration"] or 0),
                    }
                    for row in request_counts
                ],
                "error_rates": [
                    {
                        "endpoint": row["endpoint"],
                        "method": row["method"],
                        "total_requests": row["total_requests"],
                        "error_count": row["error_count"],
                        "error_percentage": float(row["error_percentage"] or 0),
                    }
                    for row in error_rates
                ],
                "slow_endpoints": [
                    {
                        "endpoint": row["endpoint"],
                        "method": row["method"],
                        "avg_duration_ms": float(row["avg_duration"] or 0),
                        "request_count": row["request_count"],
                    }
                    for row in slow_endpoints
                ],
                "hourly_volume": [
                    {
                        "hour": row["hour"].isoformat() if row["hour"] else None,
                        "request_count": row["request_count"],
                        "avg_duration_ms": float(row["avg_duration"] or 0),
                    }
                    for row in hourly_volume
                ],
            }

        except Exception as e:
            logger.error(f"Failed to get API metrics: {e}", exc_info=True)
            return {}

    async def get_system_health(self) -> Dict[str, Any]:
        """
        Get comprehensive system health status.

        Returns:
            System health dictionary
        """
        try:
            # Get performance monitor status
            system_performance = await performance_monitor.get_system_performance(time_range_hours=1)

            # Get recent alerts
            recent_alerts = await performance_monitor.get_alerts(resolved=False)

            # Get database health
            db_health = await self._check_database_health()

            # Get service health
            service_health = await self._check_service_health()

            return {
                "timestamp": datetime.now().isoformat(),
                "system_performance": system_performance,
                "active_alerts": len(recent_alerts),
                "recent_alerts": recent_alerts[:5],  # Last 5 alerts
                "database_health": db_health,
                "service_health": service_health,
                "overall_status": self._determine_overall_status(
                    system_performance, recent_alerts, db_health, service_health
                ),
            }

        except Exception as e:
            logger.error(f"Failed to get system health: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    # ============ Internal Methods ============

    async def _cleanup_old_metrics(self) -> None:
        """Clean up old in-memory metrics."""
        while self._running:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes

                # Clean up request metrics older than 1 hour
                current_time = time.time()
                one_hour_ago = current_time - 3600

                # We're storing durations, not timestamps, so we'll just limit list size
                for key in list(self.request_metrics.keys()):
                    if len(self.request_metrics[key]) > 1000:  # Keep last 1000 measurements
                        self.request_metrics[key] = self.request_metrics[key][-1000:]

                # Clean up error counts
                self.error_counts.clear()  # Reset error counts periodically

            except Exception as e:
                logger.error(f"Error in metrics cleanup: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def _check_performance_anomalies(
        self,
        endpoint: str,
        method: str,
        duration_ms: float,
        status_code: int
    ) -> None:
        """Check for performance anomalies."""
        try:
            # Check for slow requests
            if duration_ms > 5000:  # 5 seconds threshold
                await performance_monitor.create_alert(
                    title=f"Slow API request: {method} {endpoint}",
                    message=f"Request took {duration_ms:.0f}ms (status: {status_code})",
                    severity=AlertSeverity.WARNING,
                    source="api",
                    source_id=None,
                    metadata={
                        "endpoint": endpoint,
                        "method": method,
                        "duration_ms": duration_ms,
                        "status_code": status_code,
                        "threshold": 5000,
                    }
                )

            # Check for high error rates on specific endpoints
            error_key = f"{method}:{endpoint}:{status_code}"
            if status_code >= 400:
                error_count = self.error_counts.get(error_key, 0)

                if error_count > 10:  # More than 10 errors on same endpoint
                    await performance_monitor.create_alert(
                        title=f"High error rate: {method} {endpoint}",
                        message=f"{error_count} errors with status {status_code}",
                        severity=AlertSeverity.ERROR,
                        source="api",
                        source_id=None,
                        metadata={
                            "endpoint": endpoint,
                            "method": method,
                            "status_code": status_code,
                            "error_count": error_count,
                            "threshold": 10,
                        }
                    )

        except Exception as e:
            logger.error(f"Failed to check performance anomalies: {e}")

    async def _check_error_rates(self) -> None:
        """Check overall error rates."""
        try:
            total_errors = sum(self.error_counts.values())

            if total_errors > 50:  # More than 50 total errors
                await performance_monitor.create_alert(
                    title="High overall error rate",
                    message=f"Total errors: {total_errors}",
                    severity=AlertSeverity.WARNING,
                    source="api",
                    source_id=None,
                    metadata={
                        "total_errors": total_errors,
                        "threshold": 50,
                    }
                )

        except Exception as e:
            logger.error(f"Failed to check error rates: {e}")

    def _determine_error_severity(
        self,
        error: Exception,
        endpoint: Optional[str],
        method: Optional[str]
    ) -> AlertSeverity:
        """Determine alert severity based on error type and context."""
        # Critical errors
        critical_errors = [
            "DatabaseError",
            "ConnectionError",
            "TimeoutError",
            "MemoryError",
        ]

        error_type = error.__class__.__name__

        if error_type in critical_errors:
            return AlertSeverity.CRITICAL

        # Error severity based on endpoint
        if endpoint and method:
            # Critical endpoints
            critical_endpoints = [
                ("POST", "/chat"),
                ("POST", "/finance/expense"),
                ("POST", "/email/scan"),
            ]

            if (method, endpoint) in critical_endpoints:
                return AlertSeverity.ERROR

        # Default to warning for other errors
        return AlertSeverity.WARNING

    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database health."""
        try:
            start_time = time.time()

            # Check connection
            await db.fetch_val("SELECT 1")
            connection_time = (time.time() - start_time) * 1000

            # Check table counts
            table_count = await db.fetch_val(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
            )

            # Check for long-running queries
            long_queries = await db.fetch_all(
                """
                SELECT pid, query, age(clock_timestamp(), query_start) as duration
                FROM pg_stat_activity
                WHERE state = 'active' AND query_start IS NOT NULL
                AND age(clock_timestamp(), query_start) > interval '5 minutes'
                """
            )

            return {
                "status": "healthy",
                "connection_time_ms": connection_time,
                "table_count": table_count,
                "long_running_queries": len(long_queries),
                "details": {
                    "long_queries": [
                        {
                            "pid": row["pid"],
                            "duration": str(row["duration"]),
                            "query": row["query"][:100] if row["query"] else None,
                        }
                        for row in long_queries
                    ]
                }
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection_time_ms": 0,
                "table_count": 0,
                "long_running_queries": 0,
            }

    async def _check_service_health(self) -> Dict[str, Any]:
        """Check external service health."""
        import subprocess

        services = {}

        # Check Redis
        try:
            result = subprocess.run(
                ["docker", "exec", "nexus-redis", "redis-cli", "-a", "nexus_redis_password", "ping"],
                capture_output=True, text=True, timeout=5
            )
            services["redis"] = {
                "status": "healthy" if "PONG" in result.stdout else "unhealthy",
                "response": result.stdout.strip(),
            }
        except Exception as e:
            services["redis"] = {
                "status": "unhealthy",
                "error": str(e),
            }

        # Check ChromaDB
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", "nexus-chromadb"],
                capture_output=True, text=True, timeout=5
            )
            services["chromadb"] = {
                "status": "healthy" if "true" in result.stdout.lower() else "unhealthy",
                "running": "true" in result.stdout.lower(),
            }
        except Exception as e:
            services["chromadb"] = {
                "status": "unhealthy",
                "error": str(e),
            }

        return services

    def _determine_overall_status(
        self,
        system_performance: Dict[str, Any],
        recent_alerts: List[Dict[str, Any]],
        db_health: Dict[str, Any],
        service_health: Dict[str, Any]
    ) -> str:
        """Determine overall system status."""
        # Check for critical alerts
        critical_alerts = [
            alert for alert in recent_alerts
            if alert.get("severity") in ["error", "critical"]
        ]

        if critical_alerts:
            return "degraded"

        # Check database health
        if db_health.get("status") != "healthy":
            return "degraded"

        # Check critical services
        critical_services = ["redis"]
        for service in critical_services:
            if service in service_health and service_health[service].get("status") != "healthy":
                return "degraded"

        return "healthy"


# Global monitoring integration instance
monitoring_integration = MonitoringIntegration()


async def get_monitoring_integration() -> MonitoringIntegration:
    """Dependency for FastAPI routes."""
    return monitoring_integration