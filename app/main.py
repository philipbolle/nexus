"""
NEXUS FastAPI Application
Main entry point for the NEXUS API.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .config import settings
from .database import db
from .routers import health, chat, finance, email, agents, evolution, swarm, manual_tasks, autonomous_monitoring
# from .routers import distributed_tasks  # Disabled for simplification
from .agents.swarm import initialize_swarm_pubsub, initialize_event_bus, close_swarm_pubsub, close_event_bus
from .logging_config import setup_logging, get_logger
from .middleware.error_handler import setup_error_handling
from .monitoring_integration import monitoring_integration

# Setup centralized logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("Starting NEXUS API...")
    await db.connect()
    logger.info(f"Database connected: {settings.postgres_host}:{settings.postgres_port}")

    # Initialize agent framework components
    try:
        await agents.initialize_agent_framework()
        logger.info("Agent framework initialized")
    except Exception as e:
        logger.error(f"Failed to initialize agent framework: {e}")
        # Continue without agent framework - endpoints may fail

    # Initialize basic swarm communication (Redis Pub/Sub only)
    try:
        await initialize_swarm_pubsub()
        logger.info("Swarm Pub/Sub initialized")
    except Exception as e:
        logger.error(f"Failed to initialize swarm Pub/Sub: {e}")
        # Continue without swarm - endpoints may fail

    # Initialize monitoring integration
    try:
        await monitoring_integration.initialize()
        logger.info("Monitoring integration initialized")
    except Exception as e:
        logger.error(f"Failed to initialize monitoring integration: {e}")
        # Continue without monitoring integration

    logger.info(f"API running on port {settings.api_port}")

    yield

    # Shutdown
    logger.info("Shutting down NEXUS API...")
    await db.disconnect()
    logger.info("Database disconnected")

    # Close swarm communication layer
    try:
        await close_swarm_pubsub()
        logger.info("Swarm Pub/Sub closed")
    except Exception as e:
        logger.error(f"Failed to close swarm Pub/Sub: {e}")

    # Close monitoring integration
    try:
        await monitoring_integration.shutdown()
        logger.info("Monitoring integration closed")
    except Exception as e:
        logger.error(f"Failed to close monitoring integration: {e}")


# Create FastAPI app
app = FastAPI(
    title="NEXUS API",
    description="Autonomous AI Operating System for Philip",
    version="1.0.0",
    lifespan=lifespan,
)

# Store settings in app state for middleware access
app.state.settings = {
    "environment": "production" if settings.environment == "production" else "development"
}

# Setup error handling middleware
setup_error_handling(app)

# Configure CORS (allow all for Tailscale/iPhone access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(finance.router)
app.include_router(email.router)
app.include_router(agents.router)
app.include_router(evolution.router)
app.include_router(swarm.router)
app.include_router(manual_tasks.router)
app.include_router(autonomous_monitoring.router)
# app.include_router(distributed_tasks.router)  # Disabled for simplification


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "NEXUS",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=True
    )
