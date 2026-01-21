"""
NEXUS Multi-Agent Framework - Orchestrator Engine

Task decomposition, agent delegation, load balancing, and coordination engine.
Provides intelligent routing of complex tasks to appropriate agents.
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional, Tuple, Set, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from .base import BaseAgent, AgentType
from .registry import AgentRegistry, registry
from ..database import db
from app.services.ai import chat

logger = logging.getLogger(__name__)


class DecompositionStrategy(Enum):
    """Strategies for task decomposition."""
    HIERARCHICAL = "hierarchical"      # Break into tree structure
    SEQUENTIAL = "sequential"          # Break into linear steps
    PARALLEL = "parallel"              # Break into independent subtasks
    DIVIDE_CONQUER = "divide_conquer"  # Divide problem, solve, combine


class DelegationStrategy(Enum):
    """Strategies for agent delegation."""
    CAPABILITY_MATCH = "capability_match"  # Match by capabilities
    DOMAIN_EXPERT = "domain_expert"        # Domain specialist
    LOAD_BALANCED = "load_balanced"        # Distribute workload
    COST_OPTIMIZED = "cost_optimized"      # Minimize cost
    PERFORMANCE_OPTIMIZED = "performance_optimized"  # Maximize performance


@dataclass
class Subtask:
    """Represents a decomposed subtask."""

    id: str
    description: str
    required_capabilities: List[str]
    estimated_complexity: str  # "low", "medium", "high"
    dependencies: List[str]  # IDs of dependent subtasks
    assigned_agent_id: Optional[str] = None
    status: str = "pending"  # "pending", "assigned", "in_progress", "completed", "failed"
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class TaskDecomposition:
    """Result of task decomposition."""

    task_id: str
    original_task: str
    strategy: DecompositionStrategy
    subtasks: List[Subtask]
    estimated_total_complexity: int
    max_parallelism: int
    critical_path: List[str]  # Subtask IDs on critical path


@dataclass
class DelegationPlan:
    """Plan for delegating subtasks to agents."""

    task_id: str
    strategy: DelegationStrategy
    assignments: Dict[str, str]  # subtask_id -> agent_id
    estimated_cost: float
    estimated_duration_ms: int
    load_distribution: Dict[str, int]  # agent_id -> subtask_count


class OrchestratorEngine:
    """
    Core orchestrator engine for the NEXUS multi-agent system.

    Responsible for:
    - Task decomposition and analysis
    - Agent selection and delegation
    - Load balancing and resource management
    - Result aggregation and error handling
    """

    def __init__(self):
        """Initialize the orchestrator engine."""
        self.registry = registry
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.task_queue = asyncio.Queue()
        self._running = False
        self._task_processor_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """
        Initialize the orchestrator engine.

        Starts the background task processor.
        """
        if self._running:
            logger.warning("Orchestrator already initialized")
            return

        logger.info("Initializing orchestrator engine...")

        # Ensure registry is initialized
        if self.registry.status.value != "running":
            await self.registry.initialize()

        # Start background task processor
        self._running = True
        self._task_processor_task = asyncio.create_task(self._process_tasks())

        logger.info("Orchestrator engine initialized")

    async def shutdown(self) -> None:
        """
        Shutdown the orchestrator engine.

        Stops the background task processor and cleans up.
        """
        if not self._running:
            return

        logger.info("Shutting down orchestrator engine...")

        self._running = False

        # Cancel task processor
        if self._task_processor_task:
            self._task_processor_task.cancel()
            try:
                await self._task_processor_task
            except asyncio.CancelledError:
                pass

        # Clean up active tasks
        self.active_tasks.clear()

        logger.info("Orchestrator engine shut down")

    async def submit_task(
        self,
        task: Union[str, Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        decomposition_strategy: DecompositionStrategy = DecompositionStrategy.HIERARCHICAL,
        delegation_strategy: DelegationStrategy = DelegationStrategy.CAPABILITY_MATCH,
        priority: int = 1
    ) -> str:
        """
        Submit a new task for orchestration.

        Args:
            task: Task description or structured task
            context: Additional context
            decomposition_strategy: How to decompose the task
            delegation_strategy: How to delegate subtasks
            priority: Task priority (1-5, higher is more urgent)

        Returns:
            Task ID for tracking
        """
        task_id = str(uuid.uuid4())
        task_description = task if isinstance(task, str) else str(task)

        # Create task record
        task_record = {
            "id": task_id,
            "description": task_description,
            "context": context or {},
            "decomposition_strategy": decomposition_strategy,
            "delegation_strategy": delegation_strategy,
            "priority": priority,
            "status": "submitted",
            "submitted_at": datetime.now(),
            "subtasks": [],
            "results": None,
            "error": None
        }

        self.active_tasks[task_id] = task_record

        # Add to processing queue
        await self.task_queue.put(task_id)

        logger.info(f"Task submitted: {task_id} ({task_description[:100]}...)")
        return task_id

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a task.

        Args:
            task_id: Task ID

        Returns:
            Task status information or None if not found
        """
        task = self.active_tasks.get(task_id)
        if not task:
            return None

        # Calculate progress
        subtasks = task.get("subtasks", [])
        total = len(subtasks)
        completed = sum(1 for st in subtasks if st.get("status") == "completed")
        failed = sum(1 for st in subtasks if st.get("status") == "failed")

        return {
            "task_id": task_id,
            "description": task["description"],
            "status": task["status"],
            "progress": {
                "total": total,
                "completed": completed,
                "failed": failed,
                "percent": (completed / total * 100) if total > 0 else 0
            },
            "subtasks": subtasks,
            "submitted_at": task["submitted_at"],
            "started_at": task.get("started_at"),
            "completed_at": task.get("completed_at"),
            "error": task.get("error")
        }

    async def decompose_task(
        self,
        task: Union[str, Dict[str, Any]],
        strategy: DecompositionStrategy = DecompositionStrategy.HIERARCHICAL
    ) -> TaskDecomposition:
        """
        Decompose a complex task into subtasks.

        Args:
            task: Task to decompose
            strategy: Decomposition strategy

        Returns:
            Task decomposition result
        """
        task_description = task if isinstance(task, str) else str(task)
        task_id = str(uuid.uuid4())

        logger.debug(f"Decomposing task using {strategy.value} strategy: {task_description[:200]}")

        # Use AI to decompose task
        subtasks = await self._ai_decompose_task(task_description, strategy)

        # Calculate complexity and dependencies
        estimated_complexity = self._calculate_total_complexity(subtasks)
        max_parallelism = self._calculate_max_parallelism(subtasks)
        critical_path = self._find_critical_path(subtasks)

        decomposition = TaskDecomposition(
            task_id=task_id,
            original_task=task_description,
            strategy=strategy,
            subtasks=subtasks,
            estimated_total_complexity=estimated_complexity,
            max_parallelism=max_parallelism,
            critical_path=critical_path
        )

        logger.info(f"Task decomposed into {len(subtasks)} subtasks, complexity: {estimated_complexity}")
        return decomposition

    async def create_delegation_plan(
        self,
        decomposition: TaskDecomposition,
        strategy: DelegationStrategy = DelegationStrategy.CAPABILITY_MATCH
    ) -> DelegationPlan:
        """
        Create a delegation plan for subtasks.

        Args:
            decomposition: Task decomposition
            strategy: Delegation strategy

        Returns:
            Delegation plan
        """
        logger.debug(f"Creating delegation plan using {strategy.value} strategy")

        assignments = {}
        agent_loads: Dict[str, int] = {}

        # Assign each subtask to an agent
        for subtask in decomposition.subtasks:
            agent_id = await self._select_agent_for_subtask(subtask, strategy, agent_loads)

            if not agent_id:
                # No suitable agent found
                raise ValueError(f"No suitable agent found for subtask: {subtask.description}")

            assignments[subtask.id] = agent_id
            agent_loads[agent_id] = agent_loads.get(agent_id, 0) + 1

        # Estimate cost and duration
        estimated_cost = await self._estimate_delegation_cost(assignments, decomposition.subtasks)
        estimated_duration = await self._estimate_delegation_duration(assignments, decomposition.subtasks)

        plan = DelegationPlan(
            task_id=decomposition.task_id,
            strategy=strategy,
            assignments=assignments,
            estimated_cost=estimated_cost,
            estimated_duration_ms=estimated_duration,
            load_distribution=agent_loads
        )

        logger.info(f"Delegation plan created: {len(assignments)} assignments, "
                   f"estimated cost: ${estimated_cost:.4f}, duration: {estimated_duration}ms")
        return plan

    async def execute_delegation_plan(
        self,
        decomposition: TaskDecomposition,
        plan: DelegationPlan
    ) -> Dict[str, Any]:
        """
        Execute a delegation plan.

        Args:
            decomposition: Task decomposition
            plan: Delegation plan

        Returns:
            Aggregated results
        """
        task_id = decomposition.task_id
        logger.info(f"Executing delegation plan for task {task_id}")

        # Update task status
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["status"] = "executing"
            self.active_tasks[task_id]["started_at"] = datetime.now()
            self.active_tasks[task_id]["subtasks"] = [
                {
                    "id": st.id,
                    "description": st.description,
                    "assigned_agent": plan.assignments.get(st.id),
                    "status": "assigned"
                }
                for st in decomposition.subtasks
            ]

        # Execute subtasks according to dependencies
        results = await self._execute_subtasks_with_dependencies(
            decomposition.subtasks, plan.assignments
        )

        # Aggregate results
        aggregated = await self._aggregate_results(results, decomposition)

        # Update task status
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["status"] = "completed"
            self.active_tasks[task_id]["completed_at"] = datetime.now()
            self.active_tasks[task_id]["results"] = aggregated

            # Update subtask statuses
            for i, subtask in enumerate(decomposition.subtasks):
                if task_id in self.active_tasks:
                    self.active_tasks[task_id]["subtasks"][i]["status"] = (
                        "completed" if subtask.id in results and results[subtask.id].get("success")
                        else "failed"
                    )
                    self.active_tasks[task_id]["subtasks"][i]["result"] = results.get(subtask.id)

        logger.info(f"Delegation plan executed for task {task_id}, "
                   f"{len([r for r in results.values() if r.get('success')])}/{len(results)} successful")
        return aggregated

    # ============ Internal Methods ============

    async def _process_tasks(self) -> None:
        """Background task processor."""
        logger.info("Task processor started")

        while self._running:
            try:
                # Get next task from queue
                task_id = await self.task_queue.get()

                # Process task
                await self._process_task(task_id)

                # Mark task as done
                self.task_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in task processor: {e}")
                await asyncio.sleep(1)  # Prevent tight loop on errors

        logger.info("Task processor stopped")

    async def _process_task(self, task_id: str) -> None:
        """Process a single task."""
        task = self.active_tasks.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return

        try:
            # 1. Decompose task
            decomposition = await self.decompose_task(
                task["description"],
                task["decomposition_strategy"]
            )

            # 2. Create delegation plan
            plan = await self.create_delegation_plan(
                decomposition,
                task["delegation_strategy"]
            )

            # 3. Execute plan
            results = await self.execute_delegation_plan(decomposition, plan)

            # Store results
            task["results"] = results
            task["status"] = "completed"

            logger.info(f"Task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"Failed to process task {task_id}: {e}")
            task["status"] = "failed"
            task["error"] = str(e)

            # Log error
            await self._log_task_error(task_id, e)

    async def _ai_decompose_task(
        self,
        task_description: str,
        strategy: DecompositionStrategy
    ) -> List[Subtask]:
        """Use AI to decompose a task into subtasks."""
        # Prompt based on strategy
        strategy_prompts = {
            DecompositionStrategy.HIERARCHICAL: "Decompose hierarchically into main tasks and subtasks",
            DecompositionStrategy.SEQUENTIAL: "Decompose into sequential steps",
            DecompositionStrategy.PARALLEL: "Decompose into independent parallel tasks",
            DecompositionStrategy.DIVIDE_CONQUER: "Divide problem, identify subproblems, conquer independently"
        }

        prompt = f"""
        {strategy_prompts[strategy]}:

        Task: {task_description}

        Return a JSON array of subtask objects with:
        - id: Unique identifier (short string)
        - description: Clear description of subtask
        - required_capabilities: List of required capabilities (e.g., ["analysis", "database", "api"])
        - estimated_complexity: "low", "medium", or "high"
        - dependencies: List of other subtask IDs that must complete first

        Example:
        [
          {{
            "id": "research",
            "description": "Research the topic",
            "required_capabilities": ["research", "web_search"],
            "estimated_complexity": "medium",
            "dependencies": []
          }}
        ]

        Return ONLY valid JSON. No additional text.
        """

        try:
            # Use AI service to decompose task
            logger.info(f"Using AI to decompose task with {strategy.value} strategy")
            response = await chat(prompt, agent_id=None, session_id=None)

            # Parse JSON response
            import json
            subtasks_data = json.loads(response.content)

            # Create Subtask objects
            subtasks = []
            for item in subtasks_data:
                subtask = Subtask(
                    id=item["id"],
                    description=item["description"],
                    required_capabilities=item.get("required_capabilities", []),
                    estimated_complexity=item.get("estimated_complexity", "medium"),
                    dependencies=item.get("dependencies", [])
                )
                subtasks.append(subtask)

            logger.info(f"AI decomposition successful: {len(subtasks)} subtasks")
            return subtasks

        except Exception as e:
            logger.error(f"AI task decomposition failed: {e}. Using fallback decomposition.")
            # Fallback to simple decomposition
            return [
                Subtask(
                    id="analyze",
                    description=f"Analyze task: {task_description[:100]}",
                    required_capabilities=["analysis"],
                    estimated_complexity="medium",
                    dependencies=[]
                ),
                Subtask(
                    id="execute",
                    description="Execute analysis results",
                    required_capabilities=["execution"],
                    estimated_complexity="low",
                    dependencies=["analyze"]
                )
            ]

    async def _select_agent_for_subtask(
        self,
        subtask: Subtask,
        strategy: DelegationStrategy,
        current_loads: Dict[str, int]
    ) -> Optional[str]:
        """Select agent for a subtask based on strategy."""
        # Get candidate agents
        candidates = await self.registry.find_agents_by_capability(
            subtask.required_capabilities[0] if subtask.required_capabilities else "general"
        )

        if not candidates:
            logger.warning(f"No agents found for capabilities: {subtask.required_capabilities}")
            return None

        # Score candidates based on strategy
        scored_candidates = []
        for agent in candidates:
            score = await self._score_agent_for_subtask(agent, subtask, strategy, current_loads)
            scored_candidates.append((score, agent))

        # Select highest scoring agent
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return scored_candidates[0][1].agent_id if scored_candidates else None

    async def _score_agent_for_subtask(
        self,
        agent: BaseAgent,
        subtask: Subtask,
        strategy: DelegationStrategy,
        current_loads: Dict[str, int]
    ) -> float:
        """Score agent for a subtask based on strategy."""
        base_score = 1.0

        # Strategy-specific scoring
        if strategy == DelegationStrategy.CAPABILITY_MATCH:
            # Maximize capability match
            capability_match = len(set(agent.capabilities) & set(subtask.required_capabilities))
            base_score += capability_match * 0.5

        elif strategy == DelegationStrategy.DOMAIN_EXPERT:
            # Prefer domain experts
            if hasattr(agent, 'domain') and agent.domain:
                # TODO: Match domain with task domain
                base_score += 0.3

        elif strategy == DelegationStrategy.LOAD_BALANCED:
            # Prefer less loaded agents
            current_load = current_loads.get(agent.agent_id, 0)
            base_score += 1.0 / (current_load + 1)

        elif strategy == DelegationStrategy.COST_OPTIMIZED:
            # Prefer low-cost agents
            cost_per_request = agent.metrics.get("cost_per_request", 0.01)
            base_score += 1.0 / (cost_per_request + 0.001)

        elif strategy == DelegationStrategy.PERFORMANCE_OPTIMIZED:
            # Prefer high-performance agents
            success_rate = agent.metrics.get("success_rate", 0.5)
            avg_latency = agent.metrics.get("avg_latency_ms", 1000)
            base_score += success_rate * 0.5
            base_score += 1000 / (avg_latency + 1) * 0.2

        # Penalize agents with errors
        if agent.status.value == "error":
            base_score -= 0.5

        return max(0.1, base_score)

    async def _estimate_delegation_cost(
        self,
        assignments: Dict[str, str],
        subtasks: List[Subtask]
    ) -> float:
        """Estimate total cost of delegation plan."""
        total_cost = 0.0

        for subtask_id, agent_id in assignments.items():
            # Find subtask
            subtask = next((st for st in subtasks if st.id == subtask_id), None)
            if not subtask:
                continue

            # Get agent
            agent = await self.registry.get_agent(agent_id)
            if not agent:
                continue

            # Estimate cost based on complexity
            complexity_cost = {
                "low": 0.001,
                "medium": 0.005,
                "high": 0.02
            }

            cost = complexity_cost.get(subtask.estimated_complexity, 0.005)
            total_cost += cost

        return total_cost

    async def _estimate_delegation_duration(
        self,
        assignments: Dict[str, str],
        subtasks: List[Subtask]
    ) -> int:
        """Estimate total duration of delegation plan in milliseconds."""
        # Simple estimation based on complexity and dependencies
        complexity_duration = {
            "low": 1000,    # 1 second
            "medium": 5000,  # 5 seconds
            "high": 15000   # 15 seconds
        }

        # Calculate critical path duration
        max_duration = 0
        for subtask in subtasks:
            duration = complexity_duration.get(subtask.estimated_complexity, 5000)
            max_duration = max(max_duration, duration)

        # Add some overhead for coordination
        return int(max_duration * 1.2)

    async def _execute_subtasks_with_dependencies(
        self,
        subtasks: List[Subtask],
        assignments: Dict[str, str]
    ) -> Dict[str, Any]:
        """Execute subtasks respecting dependencies."""
        results = {}
        completed = set()
        in_progress = set()

        # Create dependency graph
        dependency_graph = {st.id: set(st.dependencies) for st in subtasks}
        reverse_graph = {st.id: set() for st in subtasks}

        for st in subtasks:
            for dep in st.dependencies:
                reverse_graph[dep].add(st.id)

        # Execute until all subtasks done
        while len(completed) < len(subtasks):
            # Find ready subtasks (dependencies satisfied)
            ready = []
            for st in subtasks:
                if (st.id not in completed and
                    st.id not in in_progress and
                    dependency_graph[st.id].issubset(completed)):
                    ready.append(st)

            if not ready:
                # Deadlock detection
                if not in_progress:
                    logger.error("Deadlock detected in subtask dependencies")
                    break
                # Wait for in-progress tasks
                await asyncio.sleep(0.1)
                continue

            # Execute ready subtasks in parallel
            execution_tasks = []
            for subtask in ready:
                agent_id = assignments.get(subtask.id)
                if not agent_id:
                    results[subtask.id] = {"success": False, "error": "No agent assigned"}
                    completed.add(subtask.id)
                    continue

                in_progress.add(subtask.id)
                execution_tasks.append(
                    self._execute_subtask(subtask, agent_id)
                )

            # Wait for batch to complete
            batch_results = await asyncio.gather(*execution_tasks, return_exceptions=True)

            for i, result in enumerate(batch_results):
                subtask = ready[i]
                if isinstance(result, Exception):
                    results[subtask.id] = {
                        "success": False,
                        "error": str(result)
                    }
                else:
                    results[subtask.id] = result

                in_progress.remove(subtask.id)
                completed.add(subtask.id)

                # Update subtask status
                subtask.status = "completed" if results[subtask.id].get("success") else "failed"
                subtask.result = results[subtask.id].get("result")
                subtask.error = results[subtask.id].get("error")

        return results

    async def _execute_subtask(self, subtask: Subtask, agent_id: str) -> Dict[str, Any]:
        """Execute a single subtask with assigned agent."""
        agent = await self.registry.get_agent(agent_id)
        if not agent:
            return {"success": False, "error": f"Agent {agent_id} not found"}

        try:
            result = await agent.execute(
                task=subtask.description,
                context={"subtask_id": subtask.id}
            )

            return {
                "success": True,
                "agent_id": agent_id,
                "subtask_id": subtask.id,
                "result": result,
                "execution_time": result.get("metrics", {}).get("processing_time_ms", 0)
            }

        except Exception as e:
            logger.error(f"Failed to execute subtask {subtask.id} with agent {agent_id}: {e}")
            return {
                "success": False,
                "agent_id": agent_id,
                "subtask_id": subtask.id,
                "error": str(e),
                "error_type": type(e).__name__
            }

    async def _aggregate_results(
        self,
        results: Dict[str, Any],
        decomposition: TaskDecomposition
    ) -> Dict[str, Any]:
        """Aggregate subtask results into final result."""
        successful = [r for r in results.values() if r.get("success")]
        failed = [r for r in results.values() if not r.get("success")]

        # Simple aggregation - in practice, this would be task-specific
        aggregated = {
            "summary": f"Task decomposed into {len(decomposition.subtasks)} subtasks",
            "subtasks_total": len(decomposition.subtasks),
            "subtasks_successful": len(successful),
            "subtasks_failed": len(failed),
            "success_rate": len(successful) / len(decomposition.subtasks) if decomposition.subtasks else 0,
            "failed_subtasks": [
                {
                    "id": subtask_id,
                    "error": result.get("error"),
                    "agent": result.get("agent_id")
                }
                for subtask_id, result in results.items()
                if not result.get("success")
            ],
            "results_by_subtask": {
                subtask_id: {
                    "success": result.get("success"),
                    "agent": result.get("agent_id"),
                    "execution_time_ms": result.get("execution_time", 0)
                }
                for subtask_id, result in results.items()
            }
        }

        # If all subtasks succeeded, create combined result
        if not failed:
            combined_results = []
            for subtask in decomposition.subtasks:
                if subtask.id in results:
                    result = results[subtask.id].get("result", {})
                    if isinstance(result, dict) and "result" in result:
                        combined_results.append(result["result"])

            aggregated["combined_results"] = combined_results

        return aggregated

    async def _log_task_error(self, task_id: str, error: Exception) -> None:
        """Log task execution error to database."""
        task = self.active_tasks.get(task_id)
        if not task:
            return

        await db.execute(
            """
            INSERT INTO error_logs
            (service, severity, error_type, error_message, context)
            VALUES ($1, 'error', $2, $3, $4)
            """,
            "orchestrator",
            type(error).__name__,
            str(error),
            {"task_id": task_id, "task_description": task.get("description", "")}
        )

    def _calculate_total_complexity(self, subtasks: List[Subtask]) -> int:
        """Calculate total complexity score for subtasks."""
        complexity_scores = {"low": 1, "medium": 3, "high": 10}
        total = 0

        for subtask in subtasks:
            total += complexity_scores.get(subtask.estimated_complexity, 3)

        return total

    def _calculate_max_parallelism(self, subtasks: List[Subtask]) -> int:
        """Calculate maximum possible parallelism."""
        if not subtasks:
            return 1

        # Count subtasks with no dependencies
        independent = sum(1 for st in subtasks if not st.dependencies)
        return max(1, independent)

    def _find_critical_path(self, subtasks: List[Subtask]) -> List[str]:
        """Find critical path through subtask dependencies using longest path algorithm."""
        if not subtasks:
            return []

        # Build adjacency list and reverse adjacency list
        adj = {st.id: [] for st in subtasks}
        rev_adj = {st.id: [] for st in subtasks}
        indegree = {st.id: 0 for st in subtasks}

        for st in subtasks:
            for dep in st.dependencies:
                adj[dep].append(st.id)
                rev_adj[st.id].append(dep)
                indegree[st.id] += 1

        # Topological sort using Kahn's algorithm
        zero_indegree = [st.id for st in subtasks if indegree[st.id] == 0]
        topo_order = []

        while zero_indegree:
            node = zero_indegree.pop(0)
            topo_order.append(node)
            for neighbor in adj[node]:
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    zero_indegree.append(neighbor)

        # If not all nodes processed, there's a cycle
        if len(topo_order) != len(subtasks):
            logger.warning("Cycle detected in subtask dependencies, returning empty critical path")
            return []

        # Compute longest path distances (each edge has weight 1)
        dist = {node: 0 for node in topo_order}
        prev = {node: None for node in topo_order}

        # Process nodes in topological order
        for node in topo_order:
            for neighbor in adj[node]:
                if dist[neighbor] < dist[node] + 1:
                    dist[neighbor] = dist[node] + 1
                    prev[neighbor] = node

        # Find node with maximum distance
        end_node = max(dist, key=dist.get)
        max_dist = dist[end_node]

        # Reconstruct path from end_node backwards
        path = []
        current = end_node
        while current is not None:
            path.append(current)
            current = prev[current]
        path.reverse()

        logger.debug(f"Critical path found: {path} (length: {max_dist + 1})")
        return path


# Global orchestrator instance
orchestrator = OrchestratorEngine()


async def get_orchestrator() -> OrchestratorEngine:
    """Dependency for FastAPI routes."""
    return orchestrator