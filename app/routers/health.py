"""
NEXUS Health & Status Endpoints
"""

from fastapi import APIRouter, Depends
from datetime import datetime
import subprocess
import logging

from ..database import db, get_db, Database
from ..config import settings
from ..models.schemas import HealthResponse, StatusResponse, ServiceStatus

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Simple health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow()
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

    # Check Ollama
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", "nexus-ollama"],
            capture_output=True, text=True, timeout=5
        )
        if "true" in result.stdout.lower():
            services.append(ServiceStatus(name="ollama", status="healthy"))
        else:
            services.append(ServiceStatus(name="ollama", status="unhealthy"))
    except Exception as e:
        services.append(ServiceStatus(name="ollama", status="unknown", details=str(e)))

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
