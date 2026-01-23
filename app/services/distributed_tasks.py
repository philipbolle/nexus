"""
NEXUS Distributed Task Processing Service

Service for managing distributed task processing with Celery integration.
Provides worker management, task submission, and coordination with orchestrator.
"""

import asyncio
import uuid
import socket
import os
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from enum import Enum

from ..database import db
from ..config import settings
from ..agents.orchestrator import OrchestratorEngine, TaskDecomposition, DelegationPlan
from ..agents.base import BaseAgent

try:
    from ..celery_app import app as celery_app
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    celery_app = None


class TaskDistributionMode(Enum):
    """Task distribution modes."""
    LOCAL = "local"           # Process locally (in-memory)
    DISTRIBUTED = "distributed"  # Process via Celery workers
    HYBRID = "hybrid"         # Decompose locally, execute distributed


class WorkerStatus(Enum):
    """Worker status values."""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    IDLE = "idle"
    ERROR = "error"


class DistributedTaskService:
    """
    Service for distributed task processing with Celery integration.
    """

    def __init__(self):
        """Initialize distributed task service."""
        self.orchestrator = OrchestratorEngine()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the distributed task service."""
        if self._initialized:
            return

        # Initialize orchestrator
        await self.orchestrator.initialize()

        # Check Celery availability
        if not CELERY_AVAILABLE:
            print("Warning: Celery not available, distributed processing disabled")

        self._initialized = True
        print("Distributed task service initialized")

    async def shutdown(self) -> None:
        """Shutdown the distributed task service."""
        if not self._initialized:
            return

        await self.orchestrator.shutdown()
        self._initialized = False
        print("Distributed task service shutdown")

    async def submit_task(
        self,
        task: Union[str, Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        distribution_mode: TaskDistributionMode = TaskDistributionMode.HYBRID,
        use_distributed: bool = True,
        queue_name: str = "default",
        priority: int = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Submit a task for processing with optional distributed execution.

        Args:
            task: Task description or structured task
            context: Additional context
            distribution_mode: How to distribute the task
            use_distributed: Whether to use distributed processing
            queue_name: Queue name for distributed processing
            priority: Task priority (0-10, higher = more urgent)

        Returns:
            Task submission result
        """
        task_id = str(uuid.uuid4())
        task_description = task if isinstance(task, str) else str(task)

        # Determine processing mode
        if not use_distributed or not CELERY_AVAILABLE:
            distribution_mode = TaskDistributionMode.LOCAL

        # Create task record in database
        await db.execute(
            """
            INSERT INTO tasks
            (id, description, context, status, priority, use_distributed,
             queue_name, distributed_priority, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
            """,
            task_id,
            task_description,
            context or {},
            "submitted",
            kwargs.get("priority", "medium"),  # Original priority column
            use_distributed,
            queue_name,
            priority  # New distributed_priority column
        )

        # Process based on distribution mode
        if distribution_mode == TaskDistributionMode.LOCAL:
            # Process locally via orchestrator
            result = await self._process_local(task_id, task_description, context, **kwargs)
            return result

        elif distribution_mode == TaskDistributionMode.DISTRIBUTED:
            # Submit directly to Celery
            result = await self._submit_to_celery(task_id, task_description, context, queue_name, priority, **kwargs)
            return result

        elif distribution_mode == TaskDistributionMode.HYBRID:
            # Decompose locally, execute distributed
            result = await self._process_hybrid(task_id, task_description, context, queue_name, priority, **kwargs)
            return result

        else:
            raise ValueError(f"Unknown distribution mode: {distribution_mode}")

    async def _process_local(
        self,
        task_id: str,
        task_description: str,
        context: Optional[Dict[str, Any]],
        **kwargs
    ) -> Dict[str, Any]:
        """Process task locally via orchestrator."""
        try:
            # Update task status
            await db.execute(
                "UPDATE tasks SET status = 'processing', started_at = NOW() WHERE id = $1",
                task_id
            )

            # Submit to orchestrator
            orchestrator_task_id = await self.orchestrator.submit_task(
                task_description,
                context=context,
                **kwargs
            )

            # Wait for completion (simplified - in reality would poll)
            await asyncio.sleep(0.1)  # Placeholder

            # Get result from orchestrator
            status = await self.orchestrator.get_task_status(orchestrator_task_id)

            # Update task record
            await db.execute(
                """
                UPDATE tasks SET
                    status = $2,
                    completed_at = NOW(),
                    result = $3
                WHERE id = $1
                """,
                task_id,
                status["status"] if status else "unknown",
                status
            )

            return {
                "task_id": task_id,
                "orchestrator_task_id": orchestrator_task_id,
                "status": "processing_local",
                "message": "Task submitted for local processing"
            }

        except Exception as e:
            await db.execute(
                "UPDATE tasks SET status = 'failed', last_error = $2 WHERE id = $1",
                task_id, str(e)
            )
            raise

    async def _submit_to_celery(
        self,
        task_id: str,
        task_description: str,
        context: Optional[Dict[str, Any]],
        queue_name: str,
        priority: int,
        **kwargs
    ) -> Dict[str, Any]:
        """Submit task directly to Celery for distributed processing."""
        if not CELERY_AVAILABLE:
            raise RuntimeError("Celery not available")

        try:
            # Update task status
            await db.execute(
                """
                UPDATE tasks SET
                    status = 'queued',
                    queue_name = $2,
                    distributed_priority = $3
                WHERE id = $1
                """,
                task_id, queue_name, priority
            )

            # Submit to Celery
            from ..celery_tasks.agent_tasks import process_agent_task
            celery_task = process_agent_task.apply_async(
                args=[task_id],
                queue=queue_name,
                priority=priority
            )

            # Update task with Celery ID
            await db.execute(
                "UPDATE tasks SET celery_task_id = $2 WHERE id = $1",
                task_id, celery_task.id
            )

            return {
                "task_id": task_id,
                "celery_task_id": celery_task.id,
                "queue": queue_name,
                "priority": priority,
                "status": "queued",
                "message": "Task submitted to distributed queue"
            }

        except Exception as e:
            await db.execute(
                "UPDATE tasks SET status = 'failed', last_error = $2 WHERE id = $1",
                task_id, str(e)
            )
            raise

    async def _process_hybrid(
        self,
        task_id: str,
        task_description: str,
        context: Optional[Dict[str, Any]],
        queue_name: str,
        priority: int,
        **kwargs
    ) -> Dict[str, Any]:
        """Decompose task locally, execute subtasks distributed."""
        try:
            # Update task status
            await db.execute(
                "UPDATE tasks SET status = 'decomposing', started_at = NOW() WHERE id = $1",
                task_id
            )

            # Decompose task using orchestrator
            decomposition = await self.orchestrator.decompose_task(task_description)

            # Create delegation plan
            plan = await self.orchestrator.create_delegation_plan(decomposition)

            # Store decomposition in database
            await db.execute(
                """
                UPDATE tasks SET
                    status = 'decomposed',
                    result = $2
                WHERE id = $1
                """,
                task_id,
                {
                    "subtasks": len(decomposition.subtasks),
                    "decomposition_id": decomposition.task_id,
                    "plan_id": plan.task_id
                }
            )

            # Submit subtasks to Celery
            subtask_results = []
            for subtask in decomposition.subtasks:
                agent_id = plan.assignments.get(subtask.id)
                if not agent_id:
                    continue

                # Create subtask record
                subtask_id = str(uuid.uuid4())
                await db.execute(
                    """
                    INSERT INTO tasks
                    (id, description, context, status, agent_id, parent_task_id,
                     use_distributed, queue_name, distributed_priority, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                    """,
                    subtask_id,
                    subtask.description,
                    {"subtask_id": subtask.id, "dependencies": subtask.dependencies},
                    "queued",
                    agent_id,
                    task_id,
                    True,
                    queue_name,
                    priority
                )

                # Submit to Celery
                from ..celery_tasks.agent_tasks import execute_agent_tool
                celery_task = execute_agent_tool.apply_async(
                    args=[agent_id, "execute_task", {"task": subtask.description}],
                    queue=queue_name,
                    priority=priority
                )

                # Update subtask with Celery ID
                await db.execute(
                    "UPDATE tasks SET celery_task_id = $2 WHERE id = $1",
                    subtask_id, celery_task.id
                )

                subtask_results.append({
                    "subtask_id": subtask.id,
                    "celery_task_id": celery_task.id,
                    "agent_id": agent_id,
                    "status": "queued"
                })

            return {
                "task_id": task_id,
                "decomposition_id": decomposition.task_id,
                "plan_id": plan.task_id,
                "subtasks": subtask_results,
                "status": "decomposed_and_queued",
                "message": f"Task decomposed into {len(subtask_results)} subtasks and queued for distributed execution"
            }

        except Exception as e:
            await db.execute(
                "UPDATE tasks SET status = 'failed', last_error = $2 WHERE id = $1",
                task_id, str(e)
            )
            raise

    # ===== Worker Management =====

    async def register_worker(
        self,
        worker_type: str = "celery_worker",
        max_tasks: int = 10,
        queue_names: List[str] = None,
        capabilities: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Register a worker in the database."""
        worker_id = self._generate_worker_id()

        await db.execute(
            """
            INSERT INTO task_workers
            (worker_id, worker_type, hostname, pid, status, max_tasks,
             queue_names, capabilities, metadata, last_heartbeat)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
            ON CONFLICT (worker_id) DO UPDATE SET
                status = EXCLUDED.status,
                last_heartbeat = NOW(),
                updated_at = NOW()
            """,
            worker_id,
            worker_type,
            socket.gethostname(),
            os.getpid(),
            WorkerStatus.ONLINE.value,
            max_tasks,
            queue_names or ["default"],
            capabilities or {},
            metadata or {}
        )

        # Log worker event
        await db.execute(
            """
            INSERT INTO worker_events (worker_id, event_type, event_data)
            VALUES ($1, $2, $3)
            """,
            worker_id,
            "registered",
            {
                "hostname": socket.gethostname(),
                "pid": os.getpid(),
                "worker_type": worker_type,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        return {
            "worker_id": worker_id,
            "status": WorkerStatus.ONLINE.value,
            "message": "Worker registered successfully"
        }

    async def unregister_worker(self, worker_id: str = None) -> Dict[str, Any]:
        """Unregister a worker from the database."""
        if worker_id is None:
            worker_id = self._generate_worker_id()

        await db.execute(
            """
            UPDATE task_workers
            SET status = $2, updated_at = NOW()
            WHERE worker_id = $1
            """,
            worker_id,
            WorkerStatus.OFFLINE.value
        )

        # Log worker event
        await db.execute(
            """
            INSERT INTO worker_events (worker_id, event_type, event_data)
            VALUES ($1, $2, $3)
            """,
            worker_id,
            "unregistered",
            {"timestamp": datetime.utcnow().isoformat()}
        )

        return {
            "worker_id": worker_id,
            "status": WorkerStatus.OFFLINE.value,
            "message": "Worker unregistered successfully"
        }

    async def update_worker_heartbeat(self, worker_id: str = None) -> Dict[str, Any]:
        """Update worker heartbeat in database."""
        if worker_id is None:
            worker_id = self._generate_worker_id()

        await db.execute(
            """
            UPDATE task_workers
            SET last_heartbeat = NOW(), updated_at = NOW()
            WHERE worker_id = $1
            """,
            worker_id
        )

        return {
            "worker_id": worker_id,
            "status": "heartbeat_updated",
            "timestamp": datetime.utcnow().isoformat()
        }

    async def get_worker_status(self, worker_id: str = None) -> Dict[str, Any]:
        """Get worker status from database."""
        if worker_id is None:
            worker_id = self._generate_worker_id()

        worker = await db.fetch_one(
            """
            SELECT * FROM task_workers
            WHERE worker_id = $1
            """,
            worker_id
        )

        if not worker:
            return {
                "worker_id": worker_id,
                "status": "not_found",
                "message": "Worker not registered"
            }

        # Check if worker is stale (no heartbeat in 5 minutes)
        last_heartbeat = worker["last_heartbeat"]
        if last_heartbeat and datetime.utcnow() - last_heartbeat > timedelta(minutes=5):
            status = "stale"
        else:
            status = worker["status"]

        return {
            "worker_id": worker_id,
            "status": status,
            "details": dict(worker)
        }

    async def list_workers(
        self,
        status: Optional[str] = None,
        queue_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List workers with optional filtering."""
        query = "SELECT * FROM task_workers WHERE 1=1"
        params = []

        if status:
            params.append(status)
            query += f" AND status = ${len(params)}"

        if queue_name:
            params.append(queue_name)
            query += f" AND ${len(params)} = ANY(queue_names)"

        query += " ORDER BY last_heartbeat DESC"

        workers = await db.fetch_all(query, *params)
        return [dict(worker) for worker in workers]

    # ===== Queue Management =====

    async def get_queue_depth(self, queue_name: str = "default") -> int:
        """Get current depth of a queue."""
        result = await db.fetch_one(
            "SELECT get_queue_depth($1) as depth",
            queue_name
        )
        return result["depth"] if result else 0

    async def get_queue_stats(self, queue_name: str = "default") -> Dict[str, Any]:
        """Get statistics for a queue."""
        depth = await self.get_queue_depth(queue_name)

        # Get worker count for queue
        worker_count = await db.fetch_one(
            """
            SELECT COUNT(*) as count
            FROM task_workers
            WHERE status = 'online'
            AND $1 = ANY(queue_names)
            """,
            queue_name
        )

        # Get active tasks for queue
        active_tasks = await db.fetch_one(
            """
            SELECT COUNT(*) as count
            FROM tasks
            WHERE queue_name = $1
            AND status IN ('processing', 'queued', 'retrying')
            AND use_distributed = true
            """,
            queue_name
        )

        return {
            "queue_name": queue_name,
            "depth": depth,
            "worker_count": worker_count["count"] if worker_count else 0,
            "active_tasks": active_tasks["count"] if active_tasks else 0,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def scale_workers(
        self,
        queue_name: str,
        target_workers: int,
        reason: str = "manual_scaling"
    ) -> Dict[str, Any]:
        """
        Scale workers for a queue (simulated - in production would spawn/kill workers).

        Args:
            queue_name: Queue to scale
            target_workers: Target number of workers
            reason: Reason for scaling

        Returns:
            Scaling result
        """
        # Get current workers for queue
        current_workers = await db.fetch_one(
            """
            SELECT COUNT(*) as count
            FROM task_workers
            WHERE status = 'online'
            AND $1 = ANY(queue_names)
            """,
            queue_name
        )

        current_count = current_workers["count"] if current_workers else 0

        # Record scaling decision
        decision_id = str(uuid.uuid4())
        await db.execute(
            """
            INSERT INTO scaling_decisions
            (id, decision_type, queue_name, current_workers, target_workers, reason, applied)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            decision_id,
            "scale_up" if target_workers > current_count else "scale_down",
            queue_name,
            current_count,
            target_workers,
            reason,
            False  # Not actually applied in this simulation
        )

        return {
            "decision_id": decision_id,
            "queue_name": queue_name,
            "current_workers": current_count,
            "target_workers": target_workers,
            "change": target_workers - current_count,
            "reason": reason,
            "message": "Scaling decision recorded (simulation)"
        }

    # ===== Helper Methods =====

    def _generate_worker_id(self) -> str:
        """Generate unique worker ID."""
        hostname = socket.gethostname()
        pid = os.getpid()
        unique = uuid.uuid4().hex[:8]
        return f"{hostname}_{pid}_{unique}"

    async def health_check(self) -> Dict[str, Any]:
        """Health check for distributed task service."""
        # Check database connection
        db_ok = False
        try:
            await db.execute("SELECT 1")
            db_ok = True
        except Exception as e:
            db_ok = False
            db_error = str(e)

        # Check Celery availability
        celery_ok = CELERY_AVAILABLE

        # Check Redis connection (via Celery)
        redis_ok = False
        if celery_ok and celery_app:
            try:
                # Try to get Celery broker connection
                with celery_app.connection() as conn:
                    conn.connect()
                    redis_ok = True
            except Exception:
                redis_ok = False

        # Get worker count
        worker_count = await db.fetch_one(
            "SELECT COUNT(*) as count FROM task_workers WHERE status = 'online'"
        )

        # Get queue depths
        queues = ["default", "agent_tasks", "system_tasks"]
        queue_depths = {}
        for queue in queues:
            depth = await self.get_queue_depth(queue)
            queue_depths[queue] = depth

        return {
            "status": "healthy" if db_ok and (not celery_ok or redis_ok) else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "database": {
                    "status": "ok" if db_ok else "error",
                    "error": db_error if not db_ok else None
                },
                "celery": {
                    "status": "available" if celery_ok else "unavailable",
                    "redis": "ok" if redis_ok else "error"
                }
            },
            "metrics": {
                "online_workers": worker_count["count"] if worker_count else 0,
                "queue_depths": queue_depths
            }
        }


# Global instance
distributed_task_service = DistributedTaskService()


async def get_distributed_task_service() -> DistributedTaskService:
    """Dependency for FastAPI routes."""
    return distributed_task_service