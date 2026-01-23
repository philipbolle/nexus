"""
NEXUS Distributed Task Processing - Agent Tasks

Celery tasks for agent operations and tool execution.
"""

import asyncio
import uuid
from typing import Dict, Any, Optional
from celery import current_app

from ..database import db
from ..agents.registry import agent_registry
from ..agents.tools import ToolRegistry


# Create task class using current_app
@current_app.task(bind=True, base=current_app.Task)
def execute_agent_tool(self, agent_id: str, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute an agent tool as a distributed task.

    Args:
        agent_id: ID of the agent to execute the tool
        tool_name: Name of the tool to execute
        tool_args: Arguments for the tool

    Returns:
        Tool execution result
    """
    task_id = str(uuid.uuid4())

    try:
        # Update task status in database
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Create task record if not exists
        loop.run_until_complete(db.execute(
            """
            INSERT INTO tasks
            (id, agent_id, task_type, status, parameters, use_distributed, queue_name, celery_task_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                celery_task_id = EXCLUDED.celery_task_id,
                updated_at = NOW()
            """,
            task_id,
            agent_id,
            f"tool_execution:{tool_name}",
            "processing",
            tool_args,
            True,
            "agent_tasks",
            self.request.id
        ))

        # Get agent and execute tool
        agent = agent_registry.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        tool_registry = ToolRegistry()
        tool = tool_registry.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        # Execute tool (async)
        async def execute():
            return await tool.execute(agent_id=agent_id, **tool_args)

        result = loop.run_until_complete(execute())

        # Update task completion
        loop.run_until_complete(db.execute(
            """
            UPDATE tasks
            SET status = 'completed', result = $1, completed_at = NOW()
            WHERE id = $2
            """,
            result,
            task_id
        ))

        return {
            "task_id": task_id,
            "agent_id": agent_id,
            "tool_name": tool_name,
            "result": result,
            "status": "success"
        }

    except Exception as e:
        # Update task failure
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(db.execute(
            """
            UPDATE tasks
            SET status = 'failed', last_error = $1, completed_at = NOW()
            WHERE id = $2
            """,
            str(e),
            task_id
        ))

        raise  # Re-raise for Celery error handling


@current_app.task(bind=True, base=current_app.Task)
def process_agent_task(self, task_id: str) -> Dict[str, Any]:
    """
    Process a generic agent task from the tasks table.

    Args:
        task_id: ID of the task to process

    Returns:
        Task processing result
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Get task from database
        task = loop.run_until_complete(db.fetch_one(
            "SELECT * FROM tasks WHERE id = $1",
            task_id
        ))

        if not task:
            raise ValueError(f"Task not found: {task_id}")

        # Update task with Celery ID
        loop.run_until_complete(db.execute(
            """
            UPDATE tasks
            SET celery_task_id = $1, status = 'processing', started_at = NOW()
            WHERE id = $2
            """,
            self.request.id,
            task_id
        ))

        # Parse task type and parameters
        task_type = task["task_type"]
        parameters = task["parameters"] or {}

        # Route to appropriate handler
        if task_type.startswith("tool_execution:"):
            # Extract tool name from task_type
            tool_name = task_type.split(":", 1)[1]
            agent_id = task["agent_id"]

            # Execute tool
            result = execute_agent_tool.apply(
                args=[agent_id, tool_name, parameters],
                task_id=self.request.id  # Use same task ID
            ).get()

        elif task_type == "email_processing":
            # Import email processor
            from ..agents.email_intelligence import EmailIntelligenceAgent
            agent = EmailIntelligenceAgent()
            result = loop.run_until_complete(agent.process_email_batch(parameters))

        elif task_type == "ai_analysis":
            # Import AI service
            from ..services.ai import AIProviderRouter
            router = AIProviderRouter()
            result = loop.run_until_complete(router.process_analysis(parameters))

        else:
            # Generic task - try to find agent by capability
            from ..agents.orchestrator import OrchestratorEngine
            orchestrator = OrchestratorEngine()
            result = loop.run_until_complete(orchestrator.process_task(task_type, parameters))

        # Update task completion
        loop.run_until_complete(db.execute(
            """
            UPDATE tasks
            SET status = 'completed', result = $1, completed_at = NOW()
            WHERE id = $2
            """,
            result,
            task_id
        ))

        return {
            "task_id": task_id,
            "result": result,
            "status": "success"
        }

    except Exception as e:
        # Update task failure
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(db.execute(
            """
            UPDATE tasks
            SET status = 'failed', last_error = $1, completed_at = NOW()
            WHERE id = $2
            """,
            str(e),
            task_id
        ))

        raise  # Re-raise for Celery error handling


@current_app.task(bind=True, base=current_app.Task)
def delegate_to_agent(self, source_agent_id: str, target_agent_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Delegate a task from one agent to another as a distributed task.

    Args:
        source_agent_id: ID of the agent delegating the task
        target_agent_id: ID of the agent receiving the task
        task_data: Task data including task_type and parameters

    Returns:
        Delegation result
    """
    task_id = str(uuid.uuid4())

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Create delegation task
        loop.run_until_complete(db.execute(
            """
            INSERT INTO tasks
            (id, agent_id, task_type, status, parameters, parent_task_id, use_distributed, queue_name, celery_task_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            task_id,
            target_agent_id,
            task_data.get("task_type", "delegated"),
            "processing",
            task_data.get("parameters", {}),
            task_data.get("parent_task_id"),
            True,
            "agent_tasks",
            self.request.id
        ))

        # Log delegation
        loop.run_until_complete(db.execute(
            """
            INSERT INTO agent_delegations
            (id, source_agent_id, target_agent_id, task_id, task_data, status)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            str(uuid.uuid4()),
            source_agent_id,
            target_agent_id,
            task_id,
            task_data,
            "processing"
        ))

        # Process the task (could be recursive)
        result = process_agent_task.apply(
            args=[task_id],
            task_id=self.request.id  # Use same task ID
        ).get()

        # Update delegation status
        loop.run_until_complete(db.execute(
            """
            UPDATE agent_delegations
            SET status = 'completed', completed_at = NOW(), result = $1
            WHERE task_id = $2
            """,
            result,
            task_id
        ))

        return {
            "task_id": task_id,
            "delegation": {
                "from": source_agent_id,
                "to": target_agent_id
            },
            "result": result,
            "status": "success"
        }

    except Exception as e:
        # Update delegation failure
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(db.execute(
            """
            UPDATE agent_delegations
            SET status = 'failed', completed_at = NOW(), error = $1
            WHERE task_id = $2
            """,
            str(e),
            task_id
        ))

        raise