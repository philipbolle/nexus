"""
NEXUS Distributed Task Processing - Celery Configuration

Celery app for distributed task processing with Redis broker.
Integrates with PostgreSQL worker tracking and swarm coordination.
"""

import os
import socket
import uuid
from typing import Dict, Any, Optional
from celery import Celery
from celery.signals import worker_ready, worker_shutdown, task_prerun, task_postrun
import asyncio

from .config import settings
from .database import db

# Create Celery app
app = Celery(
    "nexus",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend_url,
    include=[
        "app.celery_tasks",  # Main task module
        "app.celery_tasks.agent_tasks",  # Agent-specific tasks
        "app.celery_tasks.system_tasks",  # System maintenance tasks
    ]
)

# Configure Celery
app.conf.update(
    broker_pool_limit=settings.celery_broker_pool_limit,
    result_backend=settings.celery_result_backend_url,
    task_serializer=settings.celery_task_serializer,
    result_serializer=settings.celery_result_serializer,
    accept_content=settings.celery_accept_content,
    timezone=settings.celery_timezone,
    enable_utc=settings.celery_enable_utc,

    # Task routing
    task_routes={
        "app.celery_tasks.agent_tasks.*": {"queue": "agent_tasks"},
        "app.celery_tasks.system_tasks.*": {"queue": "system_tasks"},
        "app.celery_tasks.*": {"queue": "default"},
    },

    # Task settings
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,

    # Beat schedule (periodic tasks)
    beat_schedule={
        "cleanup-stale-workers": {
            "task": "app.celery_tasks.system_tasks.cleanup_stale_workers",
            "schedule": 300.0,  # Every 5 minutes
        },
        "update-queue-stats": {
            "task": "app.celery_tasks.system_tasks.update_queue_stats",
            "schedule": 60.0,  # Every minute
        },
        "check-leader-election": {
            "task": "app.celery_tasks.system_tasks.check_leader_election",
            "schedule": 10.0,  # Every 10 seconds
        },
        "scheduled-schema-validation": {
            "task": "app.celery_tasks.system_tasks.run_scheduled_schema_validation",
            "schedule": 604800.0,  # 7 days in seconds (weekly)
        },
        "scheduled-test-synchronization": {
            "task": "app.celery_tasks.system_tasks.run_scheduled_test_synchronization",
            "schedule": 86400.0,  # 1 day in seconds (daily)
        },
    },

    # Result expiration
    result_expires=3600,  # 1 hour
)

# Worker tracking
_worker_id: Optional[str] = None


def get_worker_id() -> str:
    """Get or generate unique worker ID."""
    global _worker_id
    if _worker_id is None:
        hostname = socket.gethostname()
        pid = os.getpid()
        _worker_id = f"{hostname}_{pid}_{uuid.uuid4().hex[:8]}"
    return _worker_id


async def register_worker() -> Dict[str, Any]:
    """Register worker in database."""
    worker_id = get_worker_id()

    try:
        # Register worker in task_workers table
        await db.execute(
            """
            INSERT INTO task_workers
            (worker_id, worker_type, hostname, pid, status, max_tasks, queue_names, capabilities, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (worker_id) DO UPDATE SET
                status = EXCLUDED.status,
                last_heartbeat = NOW(),
                active_tasks = task_workers.active_tasks,
                updated_at = NOW()
            """,
            worker_id,
            "celery_worker",
            socket.gethostname(),
            os.getpid(),
            "online",
            10,  # max_tasks
            ["default", "agent_tasks", "system_tasks"],  # queue_names
            {"celery": True, "python_version": os.sys.version},  # capabilities
            {"started_at": "now"}  # metadata
        )

        # Log worker event
        await db.execute(
            """
            INSERT INTO worker_events (worker_id, event_type, event_data)
            VALUES ($1, $2, $3)
            """,
            worker_id,
            "registered",
            {"hostname": socket.gethostname(), "pid": os.getpid()}
        )

        return {"worker_id": worker_id, "status": "registered"}

    except Exception as e:
        print(f"Failed to register worker: {e}")
        return {"worker_id": worker_id, "status": "error", "error": str(e)}


async def unregister_worker() -> Dict[str, Any]:
    """Unregister worker from database."""
    worker_id = get_worker_id()

    try:
        # Update worker status
        await db.execute(
            """
            UPDATE task_workers
            SET status = 'offline', updated_at = NOW()
            WHERE worker_id = $1
            """,
            worker_id
        )

        # Log worker event
        await db.execute(
            """
            INSERT INTO worker_events (worker_id, event_type, event_data)
            VALUES ($1, $2, $3)
            """,
            worker_id,
            "unregistered",
            {"hostname": socket.gethostname(), "pid": os.getpid()}
        )

        return {"worker_id": worker_id, "status": "unregistered"}

    except Exception as e:
        print(f"Failed to unregister worker: {e}")
        return {"worker_id": worker_id, "status": "error", "error": str(e)}


async def update_heartbeat() -> Dict[str, Any]:
    """Update worker heartbeat in database."""
    worker_id = get_worker_id()

    try:
        await db.execute(
            """
            UPDATE task_workers
            SET last_heartbeat = NOW(), updated_at = NOW()
            WHERE worker_id = $1
            """,
            worker_id
        )
        return {"worker_id": worker_id, "status": "heartbeat_updated"}
    except Exception as e:
        print(f"Failed to update heartbeat: {e}")
        return {"worker_id": worker_id, "status": "error", "error": str(e)}


# Celery signal handlers
@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handler for worker ready signal."""
    print(f"Worker ready: {get_worker_id()}")

    # Register worker (async in sync context)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(register_worker())
        print(f"Worker registered: {result}")
    finally:
        loop.close()


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Handler for worker shutdown signal."""
    print(f"Worker shutting down: {get_worker_id()}")

    # Unregister worker (async in sync context)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(unregister_worker())
        print(f"Worker unregistered: {result}")
    finally:
        loop.close()


@task_prerun.connect
def task_prerun_handler(task_id=None, task=None, **kwargs):
    """Handler for task prerun signal."""
    worker_id = get_worker_id()

    # Update active task count
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(db.execute(
            """
            UPDATE task_workers
            SET active_tasks = active_tasks + 1, updated_at = NOW()
            WHERE worker_id = $1
            """,
            worker_id
        ))

        # Update task with worker assignment
        if task and hasattr(task, 'request') and task.request:
            celery_task_id = task_id
            loop.run_until_complete(db.execute(
                """
                UPDATE tasks
                SET assigned_worker_id = $1, celery_task_id = $2
                WHERE id = $3 OR celery_task_id = $2
                """,
                worker_id,
                celery_task_id,
                # Note: task argument parsing would need task-specific logic
                # This is a placeholder - real implementation would map task args to task ID
                str(uuid.uuid4())  # Placeholder
            ))
    finally:
        loop.close()


@task_postrun.connect
def task_postrun_handler(task_id=None, task=None, **kwargs):
    """Handler for task postrun signal."""
    worker_id = get_worker_id()

    # Update active task count
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(db.execute(
            """
            UPDATE task_workers
            SET active_tasks = GREATEST(0, active_tasks - 1), updated_at = NOW()
            WHERE worker_id = $1
            """,
            worker_id
        ))
    finally:
        loop.close()


# Task base class with worker tracking
class NexusTask(app.Task):
    """Base task class with Nexus-specific functionality."""

    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        super().on_failure(exc, task_id, args, kwargs, einfo)

        # Update task error in database
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(db.execute(
                """
                UPDATE tasks
                SET last_error = $1, status = 'failed'
                WHERE celery_task_id = $2
                """,
                str(exc),
                task_id
            ))
        finally:
            loop.close()

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        super().on_success(retval, task_id, args, kwargs)

        # Update task completion in database
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(db.execute(
                """
                UPDATE tasks
                SET status = 'completed', completed_at = NOW()
                WHERE celery_task_id = $1
                """,
                task_id
            ))
        finally:
            loop.close()


# Make base task available
app.Task = NexusTask

if __name__ == "__main__":
    # Start Celery worker
    app.start()