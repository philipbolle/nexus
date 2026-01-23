"""
NEXUS Distributed Task Processing API Endpoints

FastAPI endpoints for distributed task processing with Celery integration.
Includes worker management, queue monitoring, and distributed task submission.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from uuid import UUID
import logging

from ..database import db
# from ..models.schemas import (
#     # We'll need to create distributed task schemas
#     # For now, using generic dict
# )
from ..services.distributed_tasks import (
    DistributedTaskService,
    TaskDistributionMode,
    distributed_task_service,
    get_distributed_task_service
)

router = APIRouter(prefix="/distributed-tasks", tags=["distributed-tasks"])
logger = logging.getLogger(__name__)


# ===== Task Submission =====

@router.post("/submit")
async def submit_distributed_task(
    task: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
    distribution_mode: TaskDistributionMode = TaskDistributionMode.HYBRID,
    use_distributed: bool = True,
    queue_name: str = "default",
    priority: int = 0,
    service: DistributedTaskService = Depends(get_distributed_task_service)
) -> Dict[str, Any]:
    """
    Submit a task for distributed processing.

    Args in query params:
    - distribution_mode: local, distributed, or hybrid
    - use_distributed: Whether to use distributed processing
    - queue_name: Queue name for distributed processing
    - priority: Task priority (0-10, higher = more urgent)

    Args in body:
    - task: Task description or structured task
    - context: Additional context
    """
    try:
        result = await service.submit_task(
            task=task,
            context=context,
            distribution_mode=distribution_mode,
            use_distributed=use_distributed,
            queue_name=queue_name,
            priority=priority
        )
        return result
    except Exception as e:
        logger.error(f"Failed to submit distributed task: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/workers/register")
async def register_worker(
    worker_type: str = "celery_worker",
    max_tasks: int = Query(default=10, ge=1, le=100),
    queue_names: List[str] = Query(default=["default"]),
    capabilities: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    service: DistributedTaskService = Depends(get_distributed_task_service)
) -> Dict[str, Any]:
    """Register a worker for distributed task processing."""
    try:
        result = await service.register_worker(
            worker_type=worker_type,
            max_tasks=max_tasks,
            queue_names=queue_names,
            capabilities=capabilities,
            metadata=metadata
        )
        return result
    except Exception as e:
        logger.error(f"Failed to register worker: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/workers/unregister")
async def unregister_worker(
    worker_id: Optional[str] = None,
    service: DistributedTaskService = Depends(get_distributed_task_service)
) -> Dict[str, Any]:
    """Unregister a worker from distributed task processing."""
    try:
        result = await service.unregister_worker(worker_id)
        return result
    except Exception as e:
        logger.error(f"Failed to unregister worker: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/workers")
async def list_workers(
    status: Optional[str] = Query(None, regex="^(online|offline|busy|idle|error)$"),
    queue_name: Optional[str] = None,
    service: DistributedTaskService = Depends(get_distributed_task_service)
) -> List[Dict[str, Any]]:
    """List workers with optional filtering."""
    try:
        workers = await service.list_workers(status=status, queue_name=queue_name)
        return workers
    except Exception as e:
        logger.error(f"Failed to list workers: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/workers/{worker_id}")
async def get_worker_status(
    worker_id: str,
    service: DistributedTaskService = Depends(get_distributed_task_service)
) -> Dict[str, Any]:
    """Get status of a specific worker."""
    try:
        result = await service.get_worker_status(worker_id)
        if result["status"] == "not_found":
            raise HTTPException(status_code=404, detail="Worker not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get worker status: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/workers/heartbeat")
async def update_worker_heartbeat(
    worker_id: Optional[str] = None,
    service: DistributedTaskService = Depends(get_distributed_task_service)
) -> Dict[str, Any]:
    """Update worker heartbeat (keep-alive)."""
    try:
        result = await service.update_worker_heartbeat(worker_id)
        return result
    except Exception as e:
        logger.error(f"Failed to update worker heartbeat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Queue Management =====


@router.get("/queues")
async def list_queues(
    service: DistributedTaskService = Depends(get_distributed_task_service)
) -> List[Dict[str, Any]]:
    """List all queues with their current status."""
    try:
        queues = ["default", "agent_tasks", "system_tasks"]
        results = []

        for queue in queues:
            stats = await service.get_queue_stats(queue)
            results.append(stats)

        return results
    except Exception as e:
        logger.error(f"Failed to list queues: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/queues/{queue_name}")
async def get_queue_status(
    queue_name: str,
    service: DistributedTaskService = Depends(get_distributed_task_service)
) -> Dict[str, Any]:
    """Get detailed status of a specific queue."""
    try:
        stats = await service.get_queue_stats(queue_name)
        return stats
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/queues/{queue_name}/depth")
async def get_queue_depth(
    queue_name: str,
    service: DistributedTaskService = Depends(get_distributed_task_service)
) -> Dict[str, Any]:
    """Get current depth of a queue."""
    try:
        depth = await service.get_queue_depth(queue_name)
        return {
            "queue_name": queue_name,
            "depth": depth,
            "timestamp": "now"  # Would be actual timestamp
        }
    except Exception as e:
        logger.error(f"Failed to get queue depth: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/queues/{queue_name}/scale")
async def scale_queue_workers(
    queue_name: str,
    target_workers: int = Query(..., ge=1, le=50),
    reason: str = "manual_scaling",
    service: DistributedTaskService = Depends(get_distributed_task_service)
) -> Dict[str, Any]:
    """Scale workers for a queue."""
    try:
        result = await service.scale_workers(queue_name, target_workers, reason)
        return result
    except Exception as e:
        logger.error(f"Failed to scale queue workers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== System Management =====


@router.get("/health")
async def distributed_tasks_health(
    service: DistributedTaskService = Depends(get_distributed_task_service)
) -> Dict[str, Any]:
    """Health check for distributed task processing system."""
    try:
        health = await service.health_check()
        return health
    except Exception as e:
        logger.error(f"Failed to check distributed tasks health: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/stats")
async def get_system_stats(
    service: DistributedTaskService = Depends(get_distributed_task_service)
) -> Dict[str, Any]:
    """Get system statistics for distributed task processing."""
    try:
        # Get worker counts by status
        status_counts = await db.fetch_all(
            """
            SELECT status, COUNT(*) as count
            FROM task_workers
            GROUP BY status
            """
        )

        # Get queue statistics
        queue_stats = await db.fetch_all(
            """
            SELECT queue_name, AVG(queued_tasks) as avg_depth,
                   MAX(queued_tasks) as max_depth, COUNT(*) as samples
            FROM task_queue_stats
            WHERE sampled_at > NOW() - INTERVAL '1 hour'
            GROUP BY queue_name
            """
        )

        # Get task completion rate
        completion_rate = await db.fetch_one(
            """
            SELECT
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                COUNT(*) as total,
                CASE WHEN COUNT(*) > 0
                     THEN COUNT(CASE WHEN status = 'completed' THEN 1 END)::float / COUNT(*)
                     ELSE 0
                END as rate
            FROM tasks
            WHERE created_at > NOW() - INTERVAL '1 hour'
            AND use_distributed = true
            """
        )

        return {
            "worker_counts": {row["status"]: row["count"] for row in status_counts},
            "queue_statistics": [dict(row) for row in queue_stats],
            "completion_rate": completion_rate["rate"] if completion_rate else 0,
            "tasks_completed": completion_rate["completed"] if completion_rate else 0,
            "tasks_total": completion_rate["total"] if completion_rate else 0,
        }
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/cleanup")
async def cleanup_system(
    background_tasks: BackgroundTasks,
    max_age_hours: int = Query(default=24, ge=1, le=168),
    service: DistributedTaskService = Depends(get_distributed_task_service)
) -> Dict[str, Any]:
    """Clean up old data from distributed task processing system."""
    try:
        # This would run in background
        async def cleanup_task():
            # Clean up old worker events
            await db.execute(
                """
                DELETE FROM worker_events
                WHERE created_at < NOW() - INTERVAL '1 day' * $1
                """,
                max_age_hours / 24
            )

            # Clean up old queue stats
            await db.execute(
                """
                DELETE FROM task_queue_stats
                WHERE sampled_at < NOW() - INTERVAL '1 day' * $1
                """,
                max_age_hours / 24
            )

            # Clean up old scaling decisions
            await db.execute(
                """
                DELETE FROM scaling_decisions
                WHERE created_at < NOW() - INTERVAL '1 day' * $1
                AND applied = true
                """,
                max_age_hours / 24
            )

            # Clean up old metrics
            await db.execute(
                """
                DELETE FROM distributed_task_metrics
                WHERE sampled_at < NOW() - INTERVAL '1 day' * $1
                """,
                max_age_hours / 24
            )

        background_tasks.add_task(cleanup_task)

        return {
            "message": f"Cleanup scheduled for data older than {max_age_hours} hours",
            "cleanup_type": "background",
            "max_age_hours": max_age_hours
        }
    except Exception as e:
        logger.error(f"Failed to schedule cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{task_id}")
async def get_distributed_task_status(
    task_id: UUID,
    service: DistributedTaskService = Depends(get_distributed_task_service)
) -> Dict[str, Any]:
    """Get status of a distributed task."""
    try:
        # Get task from database
        task = await db.fetch_one(
            """
            SELECT * FROM tasks
            WHERE id = $1 AND use_distributed = true
            """,
            str(task_id)
        )

        if not task:
            raise HTTPException(status_code=404, detail="Distributed task not found")

        # Get additional info if available
        if task["celery_task_id"]:
            # Try to get Celery task status
            try:
                from ..celery_app import app as celery_app
                celery_task = celery_app.AsyncResult(task["celery_task_id"])
                celery_status = {
                    "celery_status": celery_task.status,
                    "celery_result": celery_task.result if celery_task.ready() else None,
                    "celery_task_id": task["celery_task_id"]
                }
            except Exception as e:
                celery_status = {"celery_error": str(e)}
        else:
            celery_status = {}

        return {
            **dict(task),
            **celery_status,
            "is_distributed": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get distributed task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/{task_id}/cancel")
async def cancel_distributed_task(
    task_id: UUID,
    service: DistributedTaskService = Depends(get_distributed_task_service)
) -> Dict[str, Any]:
    """Cancel a distributed task."""
    try:
        # Get task
        task = await db.fetch_one(
            "SELECT * FROM tasks WHERE id = $1",
            str(task_id)
        )

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Cancel Celery task if exists
        if task["celery_task_id"]:
            try:
                from ..celery_app import app as celery_app
                celery_task = celery_app.AsyncResult(task["celery_task_id"])
                celery_task.revoke(terminate=True)
                celery_cancelled = True
            except Exception as e:
                logger.error(f"Failed to cancel Celery task: {e}")
                celery_cancelled = False
        else:
            celery_cancelled = False

        # Update task status
        await db.execute(
            """
            UPDATE tasks SET
                status = 'cancelled',
                completed_at = NOW()
            WHERE id = $1
            """,
            str(task_id)
        )

        return {
            "task_id": str(task_id),
            "cancelled": True,
            "celery_cancelled": celery_cancelled,
            "message": "Task cancelled"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel distributed task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Worker Management =====