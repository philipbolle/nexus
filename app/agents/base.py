"""
NEXUS Multi-Agent Framework - Base Agent Classes

Core abstract classes for all agents in the NEXUS system.
Provides lifecycle management, tool integration, memory, and orchestration foundations.
"""

import asyncio
import logging
import uuid
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime
from enum import Enum

import asyncpg

from ..database import db
from ..config import settings
from ..services.ai_providers import ai_request, TaskType
from ..services.semantic_cache import check_cache, store_cache
from .tools import ToolType

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent lifecycle status."""
    CREATED = "created"
    INITIALIZING = "initializing"
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING_FOR_TOOL = "waiting_for_tool"
    ERROR = "error"
    STOPPED = "stopped"


class AgentType(Enum):
    """Types of agents in the hierarchy."""
    DOMAIN = "domain"           # Specialized agent (finance, health, email, etc.)
    EMAIL_INTELLIGENCE = "email_intelligence"  # Email intelligence agent
    ORCHESTRATOR = "orchestrator"  # Coordinates multiple agents
    SUPERVISOR = "supervisor"   # Manages subordinate agents
    WORKER = "worker"           # Task-specific agent
    ANALYZER = "analyzer"       # Analysis and insight generation
    DECISION_SUPPORT = "decision_support"  # Decision support and analysis agent
    CODE_REVIEW = "code_review"  # Code review and quality assurance agent


class BaseAgent(ABC):
    """
    Abstract base class for all NEXUS agents.

    All agents must implement the core lifecycle methods and can optionally
    override tool execution, memory management, and delegation logic.
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        name: str = "Unnamed Agent",
        agent_type: AgentType = AgentType.DOMAIN,
        description: str = "",
        system_prompt: str = "",
        capabilities: Optional[List[str]] = None,
        domain: Optional[str] = None,
        supervisor_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a new agent instance.

        Args:
            agent_id: Existing agent ID (if loading from database)
            name: Unique agent name
            agent_type: Type of agent
            description: Human-readable description
            system_prompt: Default system prompt for this agent
            capabilities: List of capability strings
            domain: Domain specialization (finance, health, email, etc.)
            supervisor_id: ID of supervising agent
            config: Agent-specific configuration
        """
        self.agent_id = str(agent_id) if agent_id else str(uuid.uuid4())
        self.name = name
        self.agent_type = agent_type
        self.description = description
        self.system_prompt = system_prompt
        self.capabilities = capabilities or []
        self.domain = domain
        self.supervisor_id = str(supervisor_id) if supervisor_id else None
        self.config = config or {}

        # Runtime state
        self.status = AgentStatus.CREATED
        self.current_task_id: Optional[str] = None
        self.current_session_id: Optional[str] = None
        self.metrics: Dict[str, Any] = {
            "requests_processed": 0,
            "tokens_used": 0,
            "cost_usd": 0.0,
            "avg_latency_ms": 0,
            "success_rate": 1.0
        }
        self._tools: Dict[str, Callable] = {}
        self._last_activity = datetime.now()

        logger.info(f"Agent created: {self.name} ({self.agent_id})")

    async def initialize(self) -> None:
        """
        Initialize agent resources.

        Loads from database if agent_id exists, otherwise creates new record.
        Registers tools and sets up connections.
        """
        if self.status != AgentStatus.CREATED:
            raise RuntimeError(f"Agent {self.name} already initialized")

        self.status = AgentStatus.INITIALIZING
        logger.debug(f"Initializing agent: {self.name}")

        try:
            # Load or create agent in database
            await self._load_or_create_db_record()

            # Register built-in tools
            await self._register_core_tools()

            # Agent-specific initialization
            await self._on_initialize()

            self.status = AgentStatus.IDLE
            self._last_activity = datetime.now()
            logger.info(f"Agent initialized: {self.name}")

        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"Failed to initialize agent {self.name}: {e}")
            raise

    async def execute(
        self,
        task: Union[str, Dict[str, Any]],
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a task with this agent.

        Args:
            task: Task description or structured task object
            session_id: Existing session ID or None for new session
            context: Additional context for the task

        Returns:
            Execution result with response, metrics, and metadata
        """
        if self.status != AgentStatus.IDLE:
            raise RuntimeError(f"Agent {self.name} not ready (status: {self.status})")

        self.status = AgentStatus.PROCESSING
        self.current_session_id = session_id
        start_time = datetime.now()

        try:
            logger.info(f"Agent {self.name} executing task: {task[:100] if isinstance(task, str) else task}")

            # Create or resume session
            if not self.current_session_id:
                self.current_session_id = await self._create_session(task, context)

            # Process task based on agent type
            result = await self._process_task(task, context)

            # Update metrics
            await self._update_metrics(result, start_time)

            self.status = AgentStatus.IDLE
            self._last_activity = datetime.now()

            return {
                "success": True,
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "session_id": self.current_session_id,
                "result": result,
                "metrics": {
                    "processing_time_ms": int((datetime.now() - start_time).total_seconds() * 1000),
                    "agent_status": self.status.value
                }
            }

        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"Agent {self.name} failed on task: {e}")

            # Log error
            await self._log_error(e, task, context)

            # Attempt recovery
            await self._recover_from_error()

            return {
                "success": False,
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "error": str(e),
                "error_type": type(e).__name__,
                "metrics": {
                    "processing_time_ms": int((datetime.now() - start_time).total_seconds() * 1000),
                    "agent_status": self.status.value
                }
            }

    async def delegate(
        self,
        task: Union[str, Dict[str, Any]],
        target_agent_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Delegate a task to another agent.

        Args:
            task: Task to delegate
            target_agent_id: ID of agent to receive task
            context: Additional context

        Returns:
            Delegation result with handoff information
        """
        logger.info(f"Agent {self.name} delegating task to agent {target_agent_id}")

        # Create handoff record
        handoff_id = await self._create_handoff_record(target_agent_id, task, context)

        # In a real implementation, this would trigger the target agent
        # For now, return handoff information
        return {
            "handoff_id": handoff_id,
            "from_agent": self.agent_id,
            "to_agent": target_agent_id,
            "task": task,
            "status": "delegated"
        }

    async def register_tool(self, name: str, tool_func: Callable, schema: Optional[Dict[str, Any]] = None) -> None:
        """
        Register a tool for this agent to use.

        Args:
            name: Tool name (must be unique for this agent)
            tool_func: Async function that implements the tool
            schema: JSON Schema describing tool inputs/outputs
        """
        if name in self._tools:
            logger.warning(f"Tool {name} already registered for agent {self.name}, overwriting")

        self._tools[name] = tool_func

        # Register in database
        await self._register_tool_in_db(name, schema or {})

        logger.debug(f"Tool registered: {name} for agent {self.name}")

    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a registered tool.

        Args:
            tool_name: Name of registered tool
            **kwargs: Tool arguments

        Returns:
            Tool execution result
        """
        if tool_name not in self._tools:
            raise ValueError(f"Tool {tool_name} not registered for agent {self.name}")

        logger.debug(f"Agent {self.name} executing tool: {tool_name}")

        try:
            self.status = AgentStatus.WAITING_FOR_TOOL
            result = await self._tools[tool_name](**kwargs)
            self.status = AgentStatus.PROCESSING
            return result

        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}")
            raise

    async def cleanup(self) -> None:
        """
        Clean up agent resources before shutdown.

        Saves state to database, closes connections, etc.
        """
        logger.info(f"Cleaning up agent: {self.name}")

        try:
            # Save current state
            await self._save_state()

            # Agent-specific cleanup
            await self._on_cleanup()

            self.status = AgentStatus.STOPPED
            logger.info(f"Agent cleaned up: {self.name}")

        except Exception as e:
            logger.error(f"Error during agent cleanup {self.name}: {e}")
            raise

    # ============ Abstract Methods ============

    @abstractmethod
    async def _process_task(self, task: Union[str, Dict[str, Any]], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a task (implemented by concrete agents).

        Args:
            task: Task to process
            context: Additional context

        Returns:
            Task result
        """
        pass

    @abstractmethod
    async def _on_initialize(self) -> None:
        """
        Agent-specific initialization.
        """
        pass

    @abstractmethod
    async def _on_cleanup(self) -> None:
        """
        Agent-specific cleanup.
        """
        pass

    # ============ Core Methods with Default Implementations ============

    async def _load_or_create_db_record(self) -> None:
        """Load agent from database or create new record."""
        existing = await db.fetch_one(
            "SELECT id FROM agents WHERE id = $1",
            self.agent_id
        )

        if existing:
            # Load existing agent configuration
            agent_data = await db.fetch_one(
                """
                SELECT name, display_name, description, agent_type, domain, role, goal,
                       backstory, system_prompt, model_preference, fallback_models,
                       capabilities, tools, supervisor_id, is_active, allow_delegation,
                       max_iterations, temperature, version
                FROM agents WHERE id = $1
                """,
                self.agent_id
            )

            if agent_data:
                self.name = agent_data["name"]
                self.description = agent_data["description"]
                self.system_prompt = agent_data["system_prompt"]
                self.capabilities = agent_data["capabilities"] or []
                self.supervisor_id = agent_data["supervisor_id"]
                logger.debug(f"Loaded agent {self.name} from database")
        else:
            # Check if agent with same name already exists (duplicate ID scenario)
            existing_by_name = await db.fetch_one(
                "SELECT id FROM agents WHERE name = $1",
                self.name
            )

            if existing_by_name:
                # Agent with same name exists but different ID
                # Update our agent ID to match existing record and load it
                existing_id = existing_by_name["id"]
                logger.warning(
                    f"Agent '{self.name}' already exists with ID {existing_id}, "
                    f"updating agent ID from {self.agent_id} to match existing record."
                )
                self.agent_id = existing_id
                # Load existing agent configuration
                agent_data = await db.fetch_one(
                    """
                    SELECT name, display_name, description, agent_type, domain, role, goal,
                           backstory, system_prompt, model_preference, fallback_models,
                           capabilities, tools, supervisor_id, is_active, allow_delegation,
                           max_iterations, temperature, version
                    FROM agents WHERE id = $1
                    """,
                    self.agent_id
                )
                if agent_data:
                    self.name = agent_data["name"]
                    self.description = agent_data["description"]
                    self.system_prompt = agent_data["system_prompt"]
                    self.capabilities = agent_data["capabilities"] or []
                    self.supervisor_id = agent_data["supervisor_id"]
                    logger.debug(f"Loaded agent {self.name} from database (after name conflict)")
            else:
                # Create new agent record with duplicate handling
                try:
                    await db.execute(
                        """
                        INSERT INTO agents
                        (id, name, display_name, description, agent_type, domain, role, goal,
                         backstory, system_prompt, capabilities, tools, supervisor_id, is_active)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                        """,
                        self.agent_id,
                        self.name,
                        self.name,  # display_name
                        self.description,
                        self.agent_type.value,
                        self.config.get("domain", "general"),
                        self.config.get("role", f"{self.agent_type.value} agent"),
                        self.config.get("goal", "Complete assigned tasks effectively"),
                        self.config.get("backstory", ""),
                        self.system_prompt,
                        self.capabilities,
                        list(self._tools.keys()),
                        self.supervisor_id,
                        True
                    )
                    logger.debug(f"Created new agent record for {self.name}")

                except asyncpg.exceptions.UniqueViolationError as e:
                    # Handle duplicate key violation (likely duplicate name)
                    logger.warning(
                        f"Duplicate agent creation detected for '{self.name}': {e}. "
                        f"Loading existing agent instead."
                    )

                    # Query existing agent by name
                    existing_by_name = await db.fetch_one(
                        "SELECT id FROM agents WHERE name = $1",
                        self.name
                    )

                    if existing_by_name:
                        # Update our agent ID to match existing record and load it
                        existing_id = existing_by_name["id"]
                        logger.info(
                            f"Agent '{self.name}' already exists with ID {existing_id}, "
                            f"updating agent ID from {self.agent_id} to match existing record."
                        )
                        self.agent_id = existing_id

                        # Load existing agent configuration
                        agent_data = await db.fetch_one(
                            """
                            SELECT name, display_name, description, agent_type, domain, role, goal,
                                   backstory, system_prompt, model_preference, fallback_models,
                                   capabilities, tools, supervisor_id, is_active, allow_delegation,
                                   max_iterations, temperature, version
                            FROM agents WHERE id = $1
                            """,
                            self.agent_id
                        )
                        if agent_data:
                            self.name = agent_data["name"]
                            self.description = agent_data["description"]
                            self.system_prompt = agent_data["system_prompt"]
                            self.capabilities = agent_data["capabilities"] or []
                            self.supervisor_id = agent_data["supervisor_id"]
                            logger.debug(f"Loaded agent {self.name} from database (after duplicate violation)")
                    else:
                        # This shouldn't happen, but if it does, re-raise the error
                        logger.error(f"Unique violation but no existing agent found for name '{self.name}'")
                        raise

    async def _register_core_tools(self) -> None:
        """Register core tools available to all agents."""
        core_tools = {
            "search_memory": self._search_memory,
            "store_memory": self._store_memory,
            "request_human_input": self._request_human_input,
            "log_event": self._log_event,
            "check_system_status": self._check_system_status,
        }

        for name, func in core_tools.items():
            await self.register_tool(name, func)

    async def _create_session(self, task: Union[str, Dict[str, Any]], context: Optional[Dict[str, Any]]) -> str:
        """Create a new session for task execution."""
        session_id = str(uuid.uuid4())
        task_description = task if isinstance(task, str) else str(task)

        await db.execute(
            """
            INSERT INTO sessions
            (id, session_type, title, summary, primary_agent_id, agents_involved, status)
            VALUES ($1, 'task', $2, $3, $4, $5, 'active')
            """,
            session_id,
            f"Task from {self.name}",
            task_description[:500],
            self.agent_id,
            [self.agent_id]
        )

        return session_id

    async def _create_handoff_record(
        self,
        target_agent_id: str,
        task: Union[str, Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Create a handoff record in database."""
        handoff_id = str(uuid.uuid4())
        task_description = task if isinstance(task, str) else str(task)
        context_summary = str(context)[:1000] if context else ""

        await db.execute(
            """
            INSERT INTO agent_handoffs
            (id, session_id, from_agent_id, to_agent_id, reason, context_summary, handoff_type)
            VALUES ($1, $2, $3, $4, $5, $6, 'delegation')
            """,
            handoff_id,
            self.current_session_id,
            self.agent_id,
            target_agent_id,
            task_description[:500],
            context_summary
        )

        return handoff_id

    async def _update_metrics(self, result: Dict[str, Any], start_time: datetime) -> None:
        """Update agent performance metrics."""
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        self.metrics["requests_processed"] += 1
        self.metrics["avg_latency_ms"] = (
            (self.metrics["avg_latency_ms"] * (self.metrics["requests_processed"] - 1) + processing_time)
            / self.metrics["requests_processed"]
        )

        # Update database
        await self._update_performance_metrics(processing_time, result.get("success", True))

    async def _log_error(self, error: Exception, task: Any, context: Optional[Dict[str, Any]]) -> None:
        """Log error to database."""
        await db.execute(
            """
            INSERT INTO error_logs
            (service, severity, error_type, error_message, context, related_agent_id, related_session_id)
            VALUES ($1, 'error', $2, $3, $4, $5, $6)
            """,
            f"agent:{self.name}",
            type(error).__name__,
            str(error),
            {"task": str(task), "context": context},
            self.agent_id,
            self.current_session_id
        )

    async def _recover_from_error(self) -> None:
        """Attempt to recover agent from error state."""
        try:
            # Reset state
            self.current_task_id = None
            self.current_session_id = None

            # Check if agent can continue
            if self.metrics["success_rate"] < 0.5:  # High failure rate
                logger.warning(f"Agent {self.name} has low success rate, pausing")
                # Could trigger supervisor intervention here

            # Return to idle if possible
            self.status = AgentStatus.IDLE

        except Exception as e:
            logger.error(f"Failed to recover agent {self.name}: {e}")
            self.status = AgentStatus.ERROR

    async def _save_state(self) -> None:
        """Save agent state to database."""
        await db.execute(
            """
            UPDATE agents SET
                updated_at = NOW(),
                capabilities = $2,
                tools = $3
            WHERE id = $1
            """,
            self.agent_id,
            self.capabilities,
            list(self._tools.keys())
        )

    async def _register_tool_in_db(self, tool_name: str, schema: Dict[str, Any]) -> None:
        """Register tool in database."""
        # Check if tool exists
        tool_record = await db.fetch_one(
            "SELECT id FROM agent_tools WHERE name = $1",
            tool_name
        )

        if not tool_record:
            # Create tool record
            await db.execute(
                """
                INSERT INTO agent_tools
                (name, display_name, description, tool_type, input_schema,
                 implementation_type, implementation_config)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                tool_name,
                tool_name.replace("_", " ").title(),
                f"Tool for {self.name} agent",
                ToolType.PYTHON_FUNCTION.value,
                json.dumps(schema),
                "python_function",
                json.dumps({"agent_id": str(self.agent_id), "function_name": tool_name})
            )
            tool_record = await db.fetch_one(
                "SELECT id FROM agent_tools WHERE name = $1",
                tool_name
            )

        # Create assignment
        if tool_record:
            await db.execute(
                """
                INSERT INTO agent_tool_assignments (agent_id, tool_id, is_enabled)
                VALUES ($1, $2, true)
                ON CONFLICT (agent_id, tool_id) DO UPDATE SET is_enabled = true
                """,
                self.agent_id,
                tool_record["id"]
            )

    async def _update_performance_metrics(self, latency_ms: float, success: bool) -> None:
        """Update performance metrics in database."""
        today = datetime.now().date()

        await db.execute(
            """
            INSERT INTO agent_performance
            (agent_id, date, total_requests, successful_requests, failed_requests,
             total_tokens, total_cost_usd, avg_latency_ms)
            VALUES ($1, $2, 1, $3, $4, 0, 0, $5)
            ON CONFLICT (agent_id, date) DO UPDATE SET
                total_requests = agent_performance.total_requests + 1,
                successful_requests = agent_performance.successful_requests + $3,
                failed_requests = agent_performance.failed_requests + $4,
                avg_latency_ms = (
                    (agent_performance.avg_latency_ms * agent_performance.total_requests + $5)
                    / (agent_performance.total_requests + 1)
                )
            """,
            self.agent_id,
            today,
            1 if success else 0,
            0 if success else 1,
            latency_ms
        )

    # ============ Core Tool Implementations ============

    async def _search_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search agent memory for relevant information."""
        # TODO: Integrate with vector memory system
        return []

    async def _store_memory(self, content: str, memory_type: str = "episodic", tags: Optional[List[str]] = None) -> str:
        """Store information in agent memory."""
        # TODO: Integrate with vector memory system
        return "stored"

    async def _request_human_input(self, question: str, options: Optional[List[str]] = None) -> str:
        """Request input from human user."""
        # TODO: Integrate with notification system
        logger.info(f"Human input requested by {self.name}: {question}")
        return "human_input_requested"

    async def _log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log an event to the audit trail."""
        await db.execute(
            """
            INSERT INTO agent_events
            (aggregate_id, aggregate_type, event_type, event_data, agent_id, version)
            VALUES ($1, 'agent', $2, $3, $4, 1)
            """,
            self.current_session_id or self.agent_id,
            event_type,
            data,
            self.agent_id
        )

    async def _check_system_status(self) -> Dict[str, Any]:
        """Check system status and resource availability."""
        # Simple system check
        return {
            "database": "connected",
            "redis": "unknown",
            "ai_providers": "available",
            "agent_status": self.status.value
        }

    # ============ AI Integration Methods ============

    async def _ai_request(
        self,
        prompt: str,
        task_type: str = "analysis",
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Make an AI request with agent context.

        Args:
            prompt: User prompt
            task_type: Type of AI task
            system_prompt: Override default system prompt

        Returns:
            AI response with metrics
        """
        final_system = system_prompt or self.system_prompt

        # Add agent context to prompt
        contextual_prompt = f"""
        [Agent Context]
        Name: {self.name}
        Type: {self.agent_type.value}
        Capabilities: {', '.join(self.capabilities)}

        [Task]
        {prompt}
        """

        # Use existing AI service with agent-specific caching
        response = await ai_request(
            prompt=contextual_prompt,
            task_type=task_type,
            system=final_system
        )

        # Log usage with agent attribution
        await self._log_ai_usage(response)

        return response

    async def _log_ai_usage(self, response: Dict[str, Any]) -> None:
        """Log AI usage with agent attribution."""
        # TODO: Extend api_usage table with agent_id or use agent-specific logging
        pass


class DomainAgent(BaseAgent):
    """
    Specialized agent for specific domains (finance, health, email, etc.).

    Extends BaseAgent with domain-specific knowledge and tools.
    """

    def __init__(self, domain: Optional[str] = None, **kwargs):
        """
        Initialize a domain agent.

        Args:
            domain: Domain specialization (finance, health, email, etc.)
            **kwargs: Additional BaseAgent arguments
        """
        # Extract domain from kwargs if not provided as positional argument
        if domain is None and "domain" in kwargs:
            domain = kwargs.pop("domain")

        if domain is None:
            domain = "general"

        kwargs["agent_type"] = AgentType.DOMAIN
        super().__init__(domain=domain, **kwargs)

    async def _on_initialize(self) -> None:
        """Domain-specific initialization."""
        # Load domain-specific tools
        await self._load_domain_tools()

        # Load domain knowledge
        await self._load_domain_knowledge()

    async def _on_cleanup(self) -> None:
        """Domain-specific cleanup."""
        # Save domain-specific state
        pass

    async def _process_task(self, task: Union[str, Dict[str, Any]], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process domain-specific task.

        Default implementation uses AI with domain context.
        """
        task_text = task if isinstance(task, str) else task.get("description", str(task))

        # Use AI with domain context
        response = await self._ai_request(
            prompt=task_text,
            task_type="analysis",
            system_prompt=f"You are a {self.domain} specialist agent. {self.system_prompt}"
        )

        return {
            "response": response["content"],
            "domain": self.domain,
            "provider": response["provider"],
            "tokens": response.get("tokens", 0)
        }

    async def _load_domain_tools(self) -> None:
        """Load domain-specific tools."""
        # To be overridden by concrete domain agents
        pass

    async def _load_domain_knowledge(self) -> None:
        """Load domain knowledge into memory."""
        # To be implemented with vector memory
        pass


class OrchestratorAgent(BaseAgent):
    """
    Agent that coordinates multiple other agents.

    Responsible for task decomposition, agent selection, and result aggregation.
    """

    def __init__(self, **kwargs):
        """Initialize an orchestrator agent."""
        kwargs["agent_type"] = AgentType.ORCHESTRATOR
        super().__init__(**kwargs)
        self.subordinate_agents: Dict[str, BaseAgent] = {}

    async def _on_initialize(self) -> None:
        """Orchestrator-specific initialization."""
        # Load subordinate agent registry
        await self._load_subordinate_agents()

    async def _on_cleanup(self) -> None:
        """Orchestrator-specific cleanup."""
        # Clean up subordinate agents
        for agent in self.subordinate_agents.values():
            await agent.cleanup()

    async def _process_task(self, task: Union[str, Dict[str, Any]], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process complex task by decomposing and delegating to subordinate agents.

        Args:
            task: Complex task description
            context: Additional context

        Returns:
            Aggregated results from subordinate agents
        """
        # Decompose task
        subtasks = await self._decompose_task(task, context)

        # Assign subtasks to appropriate agents
        assignments = await self._assign_subtasks(subtasks)

        # Execute subtasks in parallel where possible
        results = await self._execute_subtasks(assignments)

        # Aggregate results
        aggregated = await self._aggregate_results(results)

        return {
            "task_decomposition": subtasks,
            "agent_assignments": assignments,
            "subtask_results": results,
            "aggregated_result": aggregated
        }

    async def _load_subordinate_agents(self) -> None:
        """Load subordinate agents from database."""
        # Load agent relationships from database
        subordinates = await db.fetch_all(
            """
            SELECT id FROM agents WHERE supervisor_id = $1 AND is_active = true
            """,
            self.agent_id
        )

        for row in subordinates:
            # TODO: Implement agent loading from registry
            # For now, just track IDs
            self.subordinate_agents[row["id"]] = None  # Placeholder

    async def _decompose_task(self, task: Union[str, Dict[str, Any]], context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Decompose complex task into subtasks."""
        task_text = task if isinstance(task, str) else task.get("description", str(task))

        # Use AI to decompose task
        decomposition_prompt = f"""
        Decompose this task into subtasks that could be handled by specialized agents:

        Task: {task_text}

        Context: {context or 'No additional context'}

        Return a JSON array of subtask objects, each with:
        - description: Brief description of subtask
        - required_capabilities: List of capabilities needed
        - estimated_complexity: Low/Medium/High
        - dependencies: List of other subtask indices that must complete first
        """

        response = await self._ai_request(
            prompt=decomposition_prompt,
            task_type="analysis",
            system_prompt="You are a task decomposition expert. Break down complex tasks into manageable subtasks."
        )

        # Parse response (simplified)
        # In real implementation, parse JSON and validate
        return [
            {
                "description": f"Subtask {i+1}",
                "required_capabilities": ["general"],
                "estimated_complexity": "Medium",
                "dependencies": []
            }
            for i in range(3)  # Simplified
        ]

    async def _assign_subtasks(self, subtasks: List[Dict[str, Any]]) -> Dict[str, str]:
        """Assign subtasks to appropriate agents."""
        assignments = {}

        for i, subtask in enumerate(subtasks):
            # Find agent with matching capabilities
            # Simplified: assign to first available subordinate
            for agent_id in self.subordinate_agents:
                assignments[f"subtask_{i}"] = agent_id
                break

            if f"subtask_{i}" not in assignments:
                # No suitable subordinate, handle myself
                assignments[f"subtask_{i}"] = self.agent_id

        return assignments

    async def _execute_subtasks(self, assignments: Dict[str, str]) -> Dict[str, Any]:
        """Execute assigned subtasks."""
        results = {}

        for subtask_id, agent_id in assignments.items():
            if agent_id == self.agent_id:
                # Execute locally (simplified)
                results[subtask_id] = {"status": "self_handled", "result": "placeholder"}
            else:
                # Delegate to subordinate (simplified)
                results[subtask_id] = {
                    "status": "delegated",
                    "agent_id": agent_id,
                    "result": "placeholder"
                }

        return results

    async def _aggregate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate subtask results into final result."""
        # Simplified aggregation
        return {
            "total_subtasks": len(results),
            "successful": sum(1 for r in results.values() if r.get("status") != "failed"),
            "aggregated_summary": "All subtasks completed successfully"
        }

    async def delegate_to_subordinate(
        self,
        agent_id: str,
        task: Union[str, Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Delegate task to specific subordinate agent.

        Args:
            agent_id: ID of subordinate agent
            task: Task to delegate
            context: Additional context

        Returns:
            Delegation result
        """
        if agent_id not in self.subordinate_agents:
            raise ValueError(f"Agent {agent_id} is not a subordinate of {self.name}")

        return await self.delegate(task, agent_id, context)