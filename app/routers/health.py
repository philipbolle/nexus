"""
NEXUS Health & Status Endpoints

Provides comprehensive health checks, readiness/liveness probes,
and system status monitoring for production deployments.
"""

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
import subprocess
import psutil
import time
import asyncio
from typing import Dict, List, Optional, Any

from ..database import db, get_db, Database
from ..config import settings
from ..models.schemas import (
    HealthResponse,
    StatusResponse,
    ServiceStatus,
    ReadinessResponse,
    LivenessResponse,
    SystemMetricsResponse,
    HealthCheckResult
)
from ..logging_config import get_logger

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Simple health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow()
    )


@router.get("/health/detailed", response_model=List[HealthCheckResult])
async def detailed_health_check():
    """
    Detailed health check with individual component status.

    Useful for debugging and monitoring individual services.
    """
    checks = []

    # Database check
    try:
        start_time = time.time()
        await db.fetch_val("SELECT 1")
        checks.append(HealthCheckResult(
            component="postgresql",
            status="healthy",
            latency_ms=(time.time() - start_time) * 1000,
            details={"connection": "established"}
        ))
    except Exception as e:
        checks.append(HealthCheckResult(
            component="postgresql",
            status="unhealthy",
            latency_ms=0,
            details={"error": str(e)}
        ))

    # Redis check
    try:
        start_time = time.time()
        result = subprocess.run(
            ["docker", "exec", "nexus-redis", "redis-cli", "-a", settings.redis_password, "ping"],
            capture_output=True, text=True, timeout=5
        )
        latency_ms = (time.time() - start_time) * 1000
        if "PONG" in result.stdout:
            checks.append(HealthCheckResult(
                component="redis",
                status="healthy",
                latency_ms=latency_ms,
                details={"response": "PONG"}
            ))
        else:
            checks.append(HealthCheckResult(
                component="redis",
                status="unhealthy",
                latency_ms=latency_ms,
                details={"error": "No PONG response"}
            ))
    except Exception as e:
        checks.append(HealthCheckResult(
            component="redis",
            status="unhealthy",
            latency_ms=0,
            details={"error": str(e)}
        ))

    # ChromaDB check
    try:
        start_time = time.time()
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", "nexus-chromadb"],
            capture_output=True, text=True, timeout=5
        )
        latency_ms = (time.time() - start_time) * 1000
        if "true" in result.stdout.lower():
            checks.append(HealthCheckResult(
                component="chromadb",
                status="healthy",
                latency_ms=latency_ms,
                details={"running": True}
            ))
        else:
            checks.append(HealthCheckResult(
                component="chromadb",
                status="unhealthy",
                latency_ms=latency_ms,
                details={"running": False}
            ))
    except Exception as e:
        checks.append(HealthCheckResult(
            component="chromadb",
            status="unhealthy",
            latency_ms=0,
            details={"error": str(e)}
        ))

    # Agent Framework check
    try:
        start_time = time.time()
        from ..agents.registry import registry
        agents = await registry.list_agents()
        latency_ms = (time.time() - start_time) * 1000
        checks.append(HealthCheckResult(
            component="agent_framework",
            status="healthy",
            latency_ms=latency_ms,
            details={"agent_count": len(agents)}
        ))
    except Exception as e:
        checks.append(HealthCheckResult(
            component="agent_framework",
            status="unhealthy",
            latency_ms=0,
            details={"error": str(e)}
        ))

    return checks


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_probe():
    """
    Readiness probe for Kubernetes/container orchestration.

    Checks if the application is ready to receive traffic.
    Returns 200 if ready, 503 if not ready.
    """
    checks = await detailed_health_check()

    # Check if all critical components are healthy
    critical_components = {"postgresql", "redis"}
    unhealthy_components = [
        check.component for check in checks
        if check.component in critical_components and check.status != "healthy"
    ]

    if unhealthy_components:
        raise HTTPException(
            status_code=503,
            detail=f"Not ready: {', '.join(unhealthy_components)} unhealthy"
        )

    return ReadinessResponse(
        status="ready",
        timestamp=datetime.utcnow(),
        checks=checks
    )


@router.get("/live", response_model=LivenessResponse)
async def liveness_probe():
    """
    Liveness probe for Kubernetes/container orchestration.

    Checks if the application is still alive and functioning.
    Returns 200 if alive, 500 if dead.
    """
    # Basic liveness check - can we respond to requests?
    try:
        # Quick database check
        await db.fetch_val("SELECT 1")

        return LivenessResponse(
            status="alive",
            timestamp=datetime.utcnow(),
            uptime_seconds=time.time() - psutil.boot_time()
        )
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Application not alive: {str(e)}"
        )


@router.get("/metrics/system", response_model=SystemMetricsResponse)
async def system_metrics():
    """
    System metrics endpoint for monitoring.

    Provides CPU, memory, disk, and network metrics.
    """
    # CPU metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_count = psutil.cpu_count()

    # Memory metrics
    memory = psutil.virtual_memory()

    # Disk metrics
    disk = psutil.disk_usage("/")

    # Network metrics
    net_io = psutil.net_io_counters()

    # Process metrics
    process = psutil.Process()
    process_memory = process.memory_info()

    return SystemMetricsResponse(
        timestamp=datetime.utcnow(),
        cpu={
            "percent": cpu_percent,
            "count": cpu_count,
            "load_avg": psutil.getloadavg()
        },
        memory={
            "total_gb": memory.total / (1024**3),
            "available_gb": memory.available / (1024**3),
            "used_percent": memory.percent,
            "process_rss_mb": process_memory.rss / (1024**2)
        },
        disk={
            "total_gb": disk.total / (1024**3),
            "used_gb": disk.used / (1024**3),
            "free_gb": disk.free / (1024**3),
            "used_percent": disk.percent
        },
        network={
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv
        },
        process={
            "pid": process.pid,
            "create_time": datetime.fromtimestamp(process.create_time()),
            "num_threads": process.num_threads(),
            "cpu_percent": process.cpu_percent()
        }
    )


@router.get("/status", response_model=StatusResponse)
async def system_status(database: Database = Depends(get_db)):
    """Detailed system status including all services."""
    services = []

    # Check PostgreSQL
    try:
        table_count = await database.fetch_val(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
        )
        services.append(ServiceStatus(
            name="postgresql",
            status="healthy",
            details=f"{table_count} tables"
        ))
    except Exception as e:
        services.append(ServiceStatus(
            name="postgresql",
            status="unhealthy",
            details=str(e)
        ))
        table_count = 0

    # Check Redis (with auth)
    try:
        result = subprocess.run(
            ["docker", "exec", "nexus-redis", "redis-cli", "-a", settings.redis_password, "ping"],
            capture_output=True, text=True, timeout=5
        )
        if "PONG" in result.stdout:
            services.append(ServiceStatus(name="redis", status="healthy"))
        else:
            services.append(ServiceStatus(name="redis", status="unhealthy", details="No PONG"))
    except Exception as e:
        services.append(ServiceStatus(name="redis", status="unknown", details=str(e)))

    # Check n8n
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", "nexus-n8n"],
            capture_output=True, text=True, timeout=5
        )
        if "true" in result.stdout.lower():
            services.append(ServiceStatus(name="n8n", status="healthy"))
        else:
            services.append(ServiceStatus(name="n8n", status="unhealthy"))
    except Exception as e:
        services.append(ServiceStatus(name="n8n", status="unknown", details=str(e)))

    # Check ChromaDB
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", "nexus-chromadb"],
            capture_output=True, text=True, timeout=5
        )
        if "true" in result.stdout.lower():
            services.append(ServiceStatus(name="chromadb", status="healthy"))
        else:
            services.append(ServiceStatus(name="chromadb", status="unhealthy"))
    except Exception as e:
        services.append(ServiceStatus(name="chromadb", status="unknown", details=str(e)))

    # Check Agent Framework
    try:
        from ..agents.registry import registry
        agents = await registry.list_agents()
        services.append(ServiceStatus(
            name="agent_framework",
            status="healthy",
            details=f"{len(agents)} agents registered"
        ))
    except Exception as e:
        services.append(ServiceStatus(
            name="agent_framework",
            status="unhealthy",
            details=f"Initialization error: {str(e)}"
        ))

    # Determine overall status
    unhealthy_count = sum(1 for s in services if s.status == "unhealthy")
    if unhealthy_count == 0:
        overall_status = "healthy"
    elif unhealthy_count < len(services):
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    return StatusResponse(
        status=overall_status,
        services=services,
        database_tables=table_count
    )
