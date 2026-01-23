"""
NEXUS Swarm Communication Layer - Swarm-Enabled Orchestrator Agent

Orchestrator agent with swarm capabilities for distributed task coordination.
Extends SwarmAgent with orchestrator functionality for multi-agent coordination.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
import uuid

from .agent import SwarmAgent
from ..base import AgentType
from ...database import db

logger = logging.getLogger(__name__)


class SwarmOrchestratorAgent(SwarmAgent):
    """
    Orchestrator agent with swarm communication capabilities.

    Combines SwarmAgent's communication features with orchestrator's
    task decomposition and delegation capabilities.
    """

    def __init__(
        self,
        swarm_id: Optional[str] = None,
        swarm_role: str = "leader",  # Orchestrators typically lead
        **kwargs
    ):
        """
        Initialize a swarm-enabled orchestrator agent.

        Args:
            swarm_id: ID of swarm to join automatically
            swarm_role: Role within swarm (defaults to 'leader')
            **kwargs: Additional SwarmAgent arguments
        """
        kwargs["agent_type"] = AgentType.ORCHESTRATOR
        super().__init__(swarm_id=swarm_id, swarm_role=swarm_role, **kwargs)

        # Orchestrator-specific state
        self.subordinate_agents: Dict[str, SwarmAgent] = {}
        self.task_registry: Dict[str, Dict[str, Any]] = {}

        logger.debug(f"SwarmOrchestratorAgent created: {self.name}")

    async def _on_initialize(self) -> None:
        """Swarm orchestrator initialization."""
        await super()._on_initialize()

        # Load subordinate agents
        await self._load_subordinate_agents()

        # Register orchestrator-specific tools
        await self._register_orchestrator_tools()

        logger.info(f"SwarmOrchestratorAgent initialized: {self.name}")

    async def _on_cleanup(self) -> None:
        """Swarm orchestrator cleanup."""
        # Clean up subordinate agents
        for agent in self.subordinate_agents.values():
            await agent.cleanup()

        await super()._on_cleanup()

    async def _register_orchestrator_tools(self) -> None:
        """Register orchestrator-specific tools."""
        orchestrator_tools = {
            "decompose_task": self._tool_decompose_task,
            "assign_subtask": self._tool_assign_subtask,
            "coordinate_swarm": self._tool_coordinate_swarm,
            "swarm_performance_report": self._tool_swarm_performance_report,
        }

        for name, func in orchestrator_tools.items():
            await self.register_tool(name, func)

    async def _load_subordinate_agents(self) -> None:
        """Load subordinate agents from database and initialize swarm connections."""
        # Load subordinate agents from database (using supervisor_id in agents table)
        subordinates = await db.fetch_all(
            """
            SELECT a.id, a.name, a.agent_type, a.domain, a.capabilities
            FROM agents a
            WHERE a.supervisor_id = $1 AND a.is_active = true
            ORDER BY a.name
            """,
            self.agent_id
        )

        for row in subordinates:
            agent_id = row["id"]
            agent_name = row["name"]

            # Create a SwarmAgent proxy for each subordinate
            # In a real implementation, we'd load the actual agent instance
            # For now, create a minimal SwarmAgent representation
            subordinate = SwarmAgent(
                agent_id=agent_id,
                name=agent_name,
                swarm_id=self.swarm_id,
                swarm_role="member"
            )

            await subordinate.initialize()
            self.subordinate_agents[agent_id] = subordinate

            logger.debug(f"Loaded subordinate agent: {agent_name}")

    # ===== Swarm Coordination =====

    async def coordinate_swarm(
        self,
        task: Union[str, Dict[str, Any]],
        coordination_strategy: str = "broadcast",
        timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """
        Coordinate a swarm to complete a task.

        Args:
            task: Task to coordinate
            coordination_strategy: Strategy for coordination ('broadcast', 'delegation', 'consensus')
            timeout_seconds: Maximum time to wait for completion

        Returns:
            Coordination results
        """
        if not self.swarm_id:
            raise ValueError("Orchestrator not in a swarm")

        coordination_id = str(uuid.uuid4())
        start_time = asyncio.get_event_loop().time()

        # Announce coordination start
        await self.publish_swarm_event(
            event_type="coordination_started",
            event_data={
                "coordination_id": coordination_id,
                "task": task,
                "strategy": coordination_strategy,
                "orchestrator_id": self.agent_id
            },
            is_global=True
        )

        # Execute based on strategy
        if coordination_strategy == "broadcast":
            result = await self._coordinate_via_broadcast(task, coordination_id, timeout_seconds)
        elif coordination_strategy == "delegation":
            result = await self._coordinate_via_delegation(task, coordination_id, timeout_seconds)
        elif coordination_strategy == "consensus":
            result = await self._coordinate_via_consensus(task, coordination_id, timeout_seconds)
        else:
            raise ValueError(f"Unknown coordination strategy: {coordination_strategy}")

        # Announce coordination completion
        await self.publish_swarm_event(
            event_type="coordination_completed",
            event_data={
                "coordination_id": coordination_id,
                "result": result,
                "duration_seconds": asyncio.get_event_loop().time() - start_time
            },
            is_global=True
        )

        return {
            "coordination_id": coordination_id,
            "strategy": coordination_strategy,
            "result": result,
            "duration_seconds": asyncio.get_event_loop().time() - start_time
        }

    async def _coordinate_via_broadcast(
        self,
        task: Union[str, Dict[str, Any]],
        coordination_id: str,
        timeout_seconds: int
    ) -> Dict[str, Any]:
        """Coordinate via broadcast to entire swarm."""
        # Broadcast task to swarm
        await self.send_swarm_message(
            message_type="broadcast",
            data={
                "coordination_id": coordination_id,
                "task": task,
                "response_required": True,
                "deadline_seconds": timeout_seconds
            }
        )

        # Collect responses
        responses = []
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
            try:
                async for message in self.receive_swarm_messages():
                    if not self._running:
                        break

                    if message.get("coordination_id") == coordination_id:
                        responses.append(message.get("data", {}))

                    if len(responses) >= len(self.subordinate_agents):
                        break

                if len(responses) >= len(self.subordinate_agents):
                    break

            except asyncio.TimeoutError:
                break

        # Aggregate responses
        aggregated = await self._aggregate_responses(responses)

        return {
            "method": "broadcast",
            "responses_received": len(responses),
            "total_agents": len(self.subordinate_agents),
            "aggregated_result": aggregated
        }

    async def _coordinate_via_delegation(
        self,
        task: Union[str, Dict[str, Any]],
        coordination_id: str,
        timeout_seconds: int
    ) -> Dict[str, Any]:
        """Coordinate via delegation to specific agents."""
        # Decompose task
        subtasks = await self._decompose_task(task)

        # Assign subtasks to agents
        assignments = await self._assign_subtasks(subtasks)

        # Execute subtasks
        results = await self._execute_subtasks(assignments, coordination_id, timeout_seconds)

        # Aggregate results
        aggregated = await self._aggregate_results(results)

        return {
            "method": "delegation",
            "subtasks": len(subtasks),
            "assignments": assignments,
            "results": results,
            "aggregated_result": aggregated
        }

    async def _coordinate_via_consensus(
        self,
        task: Union[str, Dict[str, Any]],
        coordination_id: str,
        timeout_seconds: int
    ) -> Dict[str, Any]:
        """Coordinate via swarm consensus (voting)."""
        # Create vote for task approach
        vote_id = await self.create_vote(
            subject=f"Coordination approach for: {task[:100]}",
            description=f"Determine the best approach to handle: {task}",
            options=["parallel_execution", "sequential_execution", "hierarchical_delegation"],
            voting_strategy="weighted",
            required_quorum=0.67,
            expires_in_hours=1
        )

        # Wait for votes
        await asyncio.sleep(10)  # Simplified: wait for votes

        # Get vote result
        # In a real implementation, we'd check vote status and execute based on result
        # For now, return mock result
        return {
            "method": "consensus",
            "vote_id": vote_id,
            "decision": "parallel_execution",  # Mock
            "note": "Consensus coordination would use actual voting results"
        }

    async def _decompose_task(self, task: Union[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Decompose task into subtasks."""
        task_text = task if isinstance(task, str) else task.get("description", str(task))

        # Use AI to decompose task (simplified)
        # In real implementation, use AI or predefined decomposition rules
        subtasks = [
            {
                "id": str(uuid.uuid4()),
                "description": f"Analyze requirements for: {task_text[:50]}",
                "required_capabilities": ["analysis", "planning"],
                "estimated_complexity": "medium",
                "dependencies": []
            },
            {
                "id": str(uuid.uuid4()),
                "description": f"Execute core task: {task_text[:50]}",
                "required_capabilities": ["execution"],
                "estimated_complexity": "high",
                "dependencies": ["analysis"]
            },
            {
                "id": str(uuid.uuid4()),
                "description": f"Validate results for: {task_text[:50]}",
                "required_capabilities": ["validation", "testing"],
                "estimated_complexity": "low",
                "dependencies": ["execution"]
            }
        ]

        return subtasks

    async def _assign_subtasks(self, subtasks: List[Dict[str, Any]]) -> Dict[str, str]:
        """Assign subtasks to subordinate agents."""
        assignments = {}

        for subtask in subtasks:
            # Find agent with matching capabilities
            for agent_id, agent in self.subordinate_agents.items():
                # Simplified capability matching
                if any(cap in agent.capabilities for cap in subtask["required_capabilities"]):
                    assignments[subtask["id"]] = agent_id
                    break

            # If no suitable agent found, assign to self
            if subtask["id"] not in assignments:
                assignments[subtask["id"]] = self.agent_id

        return assignments

    async def _execute_subtasks(
        self,
        assignments: Dict[str, str],
        coordination_id: str,
        timeout_seconds: int
    ) -> Dict[str, Any]:
        """Execute assigned subtasks."""
        results = {}

        for subtask_id, agent_id in assignments.items():
            if agent_id == self.agent_id:
                # Execute locally
                results[subtask_id] = {
                    "status": "executed_locally",
                    "result": f"Orchestrator executed subtask {subtask_id}",
                    "agent_id": self.agent_id
                }
            else:
                # Delegate to subordinate via swarm message
                await self.send_swarm_message(
                    message_type="direct",
                    data={
                        "coordination_id": coordination_id,
                        "subtask_id": subtask_id,
                        "action": "execute_subtask",
                        "deadline_seconds": timeout_seconds
                    },
                    target_agent_id=agent_id
                )

                results[subtask_id] = {
                    "status": "delegated",
                    "agent_id": agent_id,
                    "coordination_id": coordination_id
                }

        return results

    async def _aggregate_responses(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate broadcast responses."""
        if not responses:
            return {"empty": True}

        # Simple aggregation: combine all responses
        combined = {
            "total_responses": len(responses),
            "successful_responses": sum(1 for r in responses if r.get("success", False)),
            "combined_data": responses
        }

        return combined

    async def _aggregate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate subtask results."""
        total = len(results)
        successful = sum(1 for r in results.values() if r.get("status") in ["executed_locally", "completed"])

        return {
            "total_subtasks": total,
            "successful_subtasks": successful,
            "success_rate": successful / total if total > 0 else 0,
            "summary": f"Completed {successful}/{total} subtasks"
        }

    # ===== Tool Implementations =====

    async def _tool_decompose_task(self, task: str) -> Dict[str, Any]:
        """Tool: Decompose task into subtasks."""
        subtasks = await self._decompose_task(task)
        return {
            "task": task,
            "subtasks": subtasks,
            "count": len(subtasks)
        }

    async def _tool_assign_subtask(self, subtask_id: str, agent_id: str) -> Dict[str, Any]:
        """Tool: Assign subtask to specific agent."""
        if agent_id not in self.subordinate_agents and agent_id != self.agent_id:
            return {"error": f"Agent {agent_id} not found"}

        # Record assignment
        self.task_registry[subtask_id] = {
            "assigned_to": agent_id,
            "assigned_at": asyncio.get_event_loop().time(),
            "status": "assigned"
        }

        return {
            "subtask_id": subtask_id,
            "assigned_to": agent_id,
            "status": "assigned"
        }

    async def _tool_coordinate_swarm(
        self,
        task: str,
        coordination_strategy: str = "broadcast",
        timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """Tool: Coordinate swarm to complete a task."""
        return await self.coordinate_swarm(task, coordination_strategy, timeout_seconds)

    async def _tool_swarm_performance_report(self) -> Dict[str, Any]:
        """Tool: Generate swarm performance report."""
        if not self.swarm_id:
            return {"error": "Not in a swarm"}

        # Get swarm performance metrics from database
        performance = await db.fetch_one(
            """
            SELECT total_messages, total_votes, consensus_decisions,
                   conflicts_detected, conflicts_resolved, avg_decision_time_ms,
                   message_delivery_success_rate, consensus_success_rate,
                   member_activity_rate
            FROM swarm_performance
            WHERE swarm_id = $1
            ORDER BY date DESC
            LIMIT 1
            """,
            self.swarm_id
        )

        # Get member count
        member_count = await db.fetch_one(
            "SELECT COUNT(*) as count FROM swarm_memberships WHERE swarm_id = $1 AND status = 'active'",
            self.swarm_id
        )

        # Get recent activity
        recent_messages = await db.fetch_one(
            "SELECT COUNT(*) as count FROM swarm_messages WHERE swarm_id = $1 AND created_at > NOW() - INTERVAL '1 hour'",
            self.swarm_id
        )

        return {
            "swarm_id": self.swarm_id,
            "member_count": member_count["count"] if member_count else 0,
            "recent_messages": recent_messages["count"] if recent_messages else 0,
            "performance_metrics": dict(performance) if performance else {}
        }


# Convenience function to create a swarm orchestrator
async def create_swarm_orchestrator(
    name: str,
    swarm_id: Optional[str] = None,
    swarm_role: str = "leader",
    **kwargs
) -> SwarmOrchestratorAgent:
    """
    Create and initialize a swarm orchestrator agent.

    Args:
        name: Agent name
        swarm_id: Optional swarm to join
        swarm_role: Role in swarm
        **kwargs: Additional agent configuration

    Returns:
        Initialized swarm orchestrator agent
    """
    agent = SwarmOrchestratorAgent(
        name=name,
        swarm_id=swarm_id,
        swarm_role=swarm_role,
        **kwargs
    )

    await agent.initialize()
    return agent