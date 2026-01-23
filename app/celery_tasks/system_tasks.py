"""
NEXUS Distributed Task Processing - System Tasks

Celery tasks for system maintenance, monitoring, and coordination.
"""

import asyncio
from typing import Dict, Any, List
from celery import current_app
from datetime import datetime, timedelta

from ..database import db
from ..config import settings


@current_app.task(bind=True, base=current_app.Task)
def cleanup_stale_workers(self) -> Dict[str, Any]:
    """
    Clean up stale workers that haven't sent a heartbeat.

    Returns:
        Cleanup results
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Call PostgreSQL function
        result = loop.run_until_complete(db.fetch_one(
            "SELECT cleanup_stale_workers() as stale_count"
        ))

        stale_count = result["stale_count"] if result else 0

        # Log cleanup event
        loop.run_until_complete(db.execute(
            """
            INSERT INTO worker_events (worker_id, event_type, event_data)
            VALUES ($1, $2, $3)
            """,
            "system",
            "cleanup_stale_workers",
            {"stale_count": stale_count, "timestamp": datetime.utcnow().isoformat()}
        ))

        return {
            "stale_count": stale_count,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }

    except Exception as e:
        print(f"Cleanup stale workers failed: {e}")
        return {
            "stale_count": 0,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error"
        }


@current_app.task(bind=True, base=current_app.Task)
def update_queue_stats(self) -> Dict[str, Any]:
    """
    Update queue statistics for monitoring and scaling decisions.

    Returns:
        Queue statistics
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Get queue depths
        queues = ["default", "agent_tasks", "system_tasks"]
        stats = {}

        for queue in queues:
            # Get queue depth
            depth_result = loop.run_until_complete(db.fetch_one(
                "SELECT get_queue_depth($1) as depth",
                queue
            ))
            depth = depth_result["depth"] if depth_result else 0

            # Get worker count for queue
            worker_count_result = loop.run_until_complete(db.fetch_one(
                """
                SELECT COUNT(*) as count
                FROM task_workers
                WHERE status = 'online'
                AND $1 = ANY(queue_names)
                """,
                queue
            ))
            worker_count = worker_count_result["count"] if worker_count_result else 0

            # Get active tasks for queue
            active_tasks_result = loop.run_until_complete(db.fetch_one(
                """
                SELECT COUNT(*) as count
                FROM tasks
                WHERE queue_name = $1
                AND status IN ('processing', 'queued', 'retrying')
                AND use_distributed = true
                """,
                queue
            ))
            active_tasks = active_tasks_result["count"] if active_tasks_result else 0

            stats[queue] = {
                "depth": depth,
                "worker_count": worker_count,
                "active_tasks": active_tasks,
                "worker_utilization": active_tasks / max(worker_count, 1)
            }

            # Store in database
            loop.run_until_complete(db.execute(
                """
                INSERT INTO task_queue_stats
                (queue_name, worker_count, queued_tasks, active_tasks, completed_tasks, failed_tasks, max_queue_depth)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                queue,
                worker_count,
                depth,
                active_tasks,
                0,  # completed_tasks (would need tracking)
                0,  # failed_tasks (would need tracking)
                depth  # max_queue_depth (simplified)
            ))

        # Make scaling decisions if needed
        scaling_decisions = await_make_scaling_decisions(loop, stats)

        return {
            "stats": stats,
            "scaling_decisions": scaling_decisions,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }

    except Exception as e:
        print(f"Update queue stats failed: {e}")
        return {
            "stats": {},
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error"
        }


def await_make_scaling_decisions(loop: asyncio.AbstractEventLoop, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Helper to run async scaling decision function."""
    async def make_scaling_decisions():
        decisions = []
        for queue_name, queue_stats in stats.items():
            depth = queue_stats["depth"]
            worker_count = queue_stats["worker_count"]
            utilization = queue_stats["worker_utilization"]

            # Simple scaling logic
            if depth > worker_count * 5 and utilization > 0.8:
                # Scale up
                target_workers = min(worker_count + 1, 10)  # Max 10 workers
                decision = {
                    "decision_type": "scale_up",
                    "queue_name": queue_name,
                    "current_workers": worker_count,
                    "target_workers": target_workers,
                    "reason": f"High queue depth ({depth}) and utilization ({utilization:.2f})"
                }
                decisions.append(decision)

                # Record decision
                await db.execute(
                    """
                    INSERT INTO scaling_decisions
                    (decision_type, queue_name, current_workers, target_workers, reason, metrics, applied)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    "scale_up",
                    queue_name,
                    worker_count,
                    target_workers,
                    decision["reason"],
                    {"depth": depth, "utilization": utilization, "timestamp": datetime.utcnow().isoformat()},
                    False  # Not applied yet
                )

            elif depth < 3 and worker_count > 1 and utilization < 0.3:
                # Scale down
                target_workers = max(worker_count - 1, 1)  # Min 1 worker
                decision = {
                    "decision_type": "scale_down",
                    "queue_name": queue_name,
                    "current_workers": worker_count,
                    "target_workers": target_workers,
                    "reason": f"Low queue depth ({depth}) and utilization ({utilization:.2f})"
                }
                decisions.append(decision)

                # Record decision
                await db.execute(
                    """
                    INSERT INTO scaling_decisions
                    (decision_type, queue_name, current_workers, target_workers, reason, metrics, applied)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    "scale_down",
                    queue_name,
                    worker_count,
                    target_workers,
                    decision["reason"],
                    {"depth": depth, "utilization": utilization, "timestamp": datetime.utcnow().isoformat()},
                    False  # Not applied yet
                )

        return decisions

    return loop.run_until_complete(make_scaling_decisions())


@current_app.task(bind=True, base=current_app.Task)
def check_leader_election(self) -> Dict[str, Any]:
    """
    Check leader election status and perform elections if needed.

    Returns:
        Leader election status
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Get current leader election status
        leaders = loop.run_until_complete(db.fetch_all(
            "SELECT role, node_id, term, lease_expires_at FROM leader_election"
        ))

        current_time = datetime.utcnow()
        elections = []

        for leader in leaders:
            role = leader["role"]
            node_id = leader["node_id"]
            lease_expires = leader["lease_expires_at"]

            # Check if lease expired
            if lease_expires and lease_expires < current_time:
                # Lease expired, need new election
                print(f"Lease expired for {role}, initiating election")

                # Find candidate (simplified - just pick first online worker)
                candidate = loop.run_until_complete(db.fetch_one(
                    """
                    SELECT worker_id, hostname
                    FROM task_workers
                    WHERE status = 'online'
                    ORDER BY last_heartbeat DESC
                    LIMIT 1
                    """
                ))

                if candidate:
                    new_leader = candidate["worker_id"]
                    term = leader["term"] + 1

                    # Update leader
                    loop.run_until_complete(db.execute(
                        """
                        UPDATE leader_election
                        SET node_id = $1, term = $2,
                            last_heartbeat = NOW(),
                            lease_expires_at = NOW() + INTERVAL '30 seconds',
                            updated_at = NOW()
                        WHERE role = $3
                        """,
                        new_leader,
                        term,
                        role
                    ))

                    # Record history
                    loop.run_until_complete(db.execute(
                        """
                        INSERT INTO leader_history
                        (role, old_leader, new_leader, election_type, term, reason)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        role,
                        node_id,
                        new_leader,
                        "lease_expired",
                        term,
                        f"Lease expired at {lease_expires}"
                    ))

                    elections.append({
                        "role": role,
                        "old_leader": node_id,
                        "new_leader": new_leader,
                        "term": term,
                        "reason": "lease_expired"
                    })

        return {
            "leaders": [dict(leader) for leader in leaders],
            "elections": elections,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }

    except Exception as e:
        print(f"Check leader election failed: {e}")
        return {
            "leaders": [],
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error"
        }


@current_app.task(bind=True, base=current_app.Task)
def update_task_shards(self) -> Dict[str, Any]:
    """
    Update task sharding assignments for load distribution.

    Returns:
        Sharding assignments
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Get online workers
        workers = loop.run_until_complete(db.fetch_all(
            """
            SELECT worker_id, active_tasks, max_tasks
            FROM task_workers
            WHERE status = 'online'
            ORDER BY active_tasks ASC
            """
        ))

        # Get shard keys (0-9)
        shard_keys = [str(i) for i in range(10)]
        assignments = []

        # Simple round-robin assignment
        for i, shard_key in enumerate(shard_keys):
            if workers:
                worker_index = i % len(workers)
                worker = workers[worker_index]
                worker_id = worker["worker_id"]

                # Update or create shard assignment
                loop.run_until_complete(db.execute(
                    """
                    INSERT INTO task_shards (shard_key, worker_id, task_count)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (shard_key, worker_id) DO UPDATE SET
                        task_count = EXCLUDED.task_count,
                        last_assigned = NOW(),
                        updated_at = NOW()
                    """,
                    shard_key,
                    worker_id,
                    0  # task_count will be updated separately
                ))

                assignments.append({
                    "shard_key": shard_key,
                    "worker_id": worker_id,
                    "worker_index": worker_index
                })

        return {
            "assignments": assignments,
            "total_workers": len(workers),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }

    except Exception as e:
        print(f"Update task shards failed: {e}")
        return {
            "assignments": [],
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error"
        }


@current_app.task(bind=True, base=current_app.Task)
def collect_performance_metrics(self) -> Dict[str, Any]:
    """
    Collect performance metrics for distributed task processing.

    Returns:
        Performance metrics
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Get task completion rate (last hour)
        completion_rate = loop.run_until_complete(db.fetch_one(
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
        ))

        # Get worker utilization
        worker_utilization = loop.run_until_complete(db.fetch_one(
            """
            SELECT
                AVG(active_tasks::float / NULLIF(max_tasks, 0)) as avg_utilization,
                COUNT(*) as total_workers,
                COUNT(CASE WHEN status = 'online' THEN 1 END) as online_workers
            FROM task_workers
            """
        ))

        # Get queue statistics
        queue_stats = loop.run_until_complete(db.fetch_one(
            """
            SELECT
                AVG(queued_tasks) as avg_queue_depth,
                MAX(queued_tasks) as max_queue_depth,
                COUNT(*) as samples
            FROM task_queue_stats
            WHERE sampled_at > NOW() - INTERVAL '1 hour'
            """
        ))

        # Store metrics
        metrics = {
            "task_completion_rate": completion_rate["rate"] if completion_rate else 0,
            "tasks_completed": completion_rate["completed"] if completion_rate else 0,
            "tasks_total": completion_rate["total"] if completion_rate else 0,
            "worker_utilization": worker_utilization["avg_utilization"] if worker_utilization else 0,
            "online_workers": worker_utilization["online_workers"] if worker_utilization else 0,
            "total_workers": worker_utilization["total_workers"] if worker_utilization else 0,
            "avg_queue_depth": queue_stats["avg_queue_depth"] if queue_stats else 0,
            "max_queue_depth": queue_stats["max_queue_depth"] if queue_stats else 0,
        }

        # Insert into metrics table
        for metric_name, metric_value in metrics.items():
            loop.run_until_complete(db.execute(
                """
                INSERT INTO distributed_task_metrics
                (metric_type, metric_name, metric_value, labels, sampled_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                "performance",
                metric_name,
                float(metric_value),
                {"source": "celery_beat"},
                datetime.utcnow()
            ))

        return {
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }

    except Exception as e:
        print(f"Collect performance metrics failed: {e}")
        return {
            "metrics": {},
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error"
        }