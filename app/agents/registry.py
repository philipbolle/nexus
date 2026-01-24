"""
NEXUS Multi-Agent Framework - Agent Registry

Central registry for agent discovery, lifecycle management, and capability matching.
Provides singleton access to all agents in the system.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Type, Any, Set, Tuple
from enum import Enum
import uuid
from uuid import UUID

from .base import BaseAgent, AgentType, AgentStatus
from ..database import db

logger = logging.getLogger(__name__)


class RegistryStatus(Enum):
    """Registry operational status."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class AgentRegistry:
    """
    Central registry for all agents in the NEXUS system.

    Manages agent lifecycle, provides discovery services, and handles
    capability-based agent selection.
    """

    _instance = None

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super(AgentRegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the registry (singleton)."""
        if self._initialized:
            return

        self.status = RegistryStatus.INITIALIZING
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_types: Dict[str, Type[BaseAgent]] = {}
        self.capability_index: Dict[str, Set[str]] = {}  # capability -> agent_ids
        self.domain_index: Dict[str, Set[str]] = {}      # domain -> agent_ids

        self._initialized = True
        logger.info("Agent registry initialized")

    async def initialize(self) -> None:
        """
        Initialize the registry.

        Loads existing agents from database and registers built-in agent types.
        """
        if self.status != RegistryStatus.INITIALIZING:
            raise RuntimeError(f"Registry already initialized (status: {self.status})")

        logger.info("Initializing agent registry...")

        try:
            # Register built-in agent types
            await self._register_builtin_types()

            # Load active agents from database
            await self._load_agents_from_db()

            # Initialize all agents
            await self._initialize_all_agents()

            self.status = RegistryStatus.RUNNING
            logger.info(f"Agent registry running with {len(self.agents)} agents")

        except Exception as e:
            self.status = RegistryStatus.ERROR
            logger.error(f"Failed to initialize agent registry: {e}")
            raise

    async def shutdown(self) -> None:
        """
        Shutdown the registry.

        Gracefully stops all agents and cleans up resources.
        """
        if self.status != RegistryStatus.RUNNING:
            logger.warning(f"Registry not running (status: {self.status}), skipping shutdown")
            return

        self.status = RegistryStatus.STOPPING
        logger.info("Shutting down agent registry...")

        try:
            # Stop all agents
            await self._stop_all_agents()

            # Clear indexes
            self.agents.clear()
            self.capability_index.clear()
            self.domain_index.clear()

            self.status = RegistryStatus.STOPPED
            logger.info("Agent registry shut down successfully")

        except Exception as e:
            self.status = RegistryStatus.ERROR
            logger.error(f"Error during registry shutdown: {e}")
            raise

    async def register_agent_type(self, agent_type: str, agent_class: Type[BaseAgent]) -> None:
        """
        Register a new agent type.

        Args:
            agent_type: Unique type identifier
            agent_class: Agent class (subclass of BaseAgent)
        """
        if agent_type in self.agent_types:
            logger.warning(f"Agent type {agent_type} already registered, overwriting")

        self.agent_types[agent_type] = agent_class
        logger.debug(f"Registered agent type: {agent_type}")

    async def create_agent(
        self,
        agent_type: str,
        name: str,
        **kwargs
    ) -> BaseAgent:
        """
        Create a new agent instance.

        Args:
            agent_type: Registered agent type
            name: Unique agent name
            **kwargs: Additional agent configuration

        Returns:
            Created agent instance
        """
        if agent_type not in self.agent_types:
            raise ValueError(f"Unknown agent type: {agent_type}")

        # Check for duplicate name (in memory and database)
        for agent in self.agents.values():
            if agent.name == name:
                raise ValueError(f"Agent with name '{name}' already exists")

        # Also check database for duplicate name
        try:
            existing_agent = await db.fetch_one(
                "SELECT id FROM agents WHERE name = $1 AND is_active = true",
                name
            )
            if existing_agent:
                raise ValueError(f"Agent with name '{name}' already exists in database")
        except Exception as e:
            logger.warning(f"Failed to check database for duplicate agent name '{name}': {e}")
            # Continue anyway - database constraint will catch it if it's a duplicate

        # Create agent instance
        agent_class = self.agent_types[agent_type]
        agent = agent_class(name=name, **kwargs)

        # Generate agent ID if not provided
        if not agent.agent_id:
            agent.agent_id = str(uuid.uuid4())

        # Register in registry
        await self._register_agent(agent)

        # Store in database (non-blocking, don't fail creation if DB fails)
        try:
            await self._store_agent_in_db(agent)
        except Exception as e:
            logger.warning(f"Failed to store agent {name} in database, continuing with in-memory only: {e}")

        # Initialize agent
        await agent.initialize()

        logger.info(f"Created agent: {name} ({agent.agent_id}) of type {agent_type}")
        return agent

    async def register_agent(
        self,
        name: str,
        agent_type: str,
        description: str = "",
        system_prompt: str = "",
        capabilities: List[str] = None,
        domain: Optional[str] = None,
        supervisor_id: Optional[UUID] = None,
        config: Dict[str, Any] = None
    ) -> BaseAgent:
        """
        Register a new agent (alias for create_agent with expanded parameters).

        This method provides the interface expected by the API router.
        """
        if capabilities is None:
            capabilities = []
        if config is None:
            config = {}

        return await self.create_agent(
            agent_type=agent_type,
            name=name,
            description=description,
            system_prompt=system_prompt,
            capabilities=capabilities,
            domain=domain,
            supervisor_id=supervisor_id,
            config=config
        )

    async def update_agent(
        self,
        agent_id: UUID,
        **kwargs
    ) -> Optional[BaseAgent]:
        """
        Update an existing agent's configuration.

        Args:
            agent_id: Agent ID to update
            **kwargs: Fields to update (name, description, system_prompt, capabilities, etc.)

        Returns:
            Updated agent or None if not found
        """
        agent_id_str = str(agent_id)
        agent = self.agents.get(agent_id_str)
        if not agent:
            return None

        # Update allowed fields
        allowed_fields = {'name', 'description', 'system_prompt', 'capabilities', 'domain', 'config'}
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(agent, field):
                setattr(agent, field, value)

        # Update indexes if capabilities or domain changed
        if 'capabilities' in kwargs or 'domain' in kwargs:
            await self._update_indexes(agent)

        # Update database
        try:
            await self._store_agent_in_db(agent)
        except Exception as e:
            logger.warning(f"Failed to update agent {agent.name} in database: {e}")

        logger.info(f"Updated agent: {agent.name} ({agent_id})")
        return agent

    async def delete_agent(self, agent_id: UUID) -> bool:
        """
        Delete an agent (remove from registry).

        Args:
            agent_id: Agent ID to delete

        Returns:
            True if deleted, False if not found
        """
        agent_id_str = str(agent_id)
        if agent_id_str not in self.agents:
            return False

        agent = self.agents[agent_id_str]

        # Stop agent if running
        if agent.status != AgentStatus.STOPPED:
            await agent.cleanup()

        # Remove from registry
        del self.agents[agent_id_str]

        # Remove from indexes
        for capability_set in self.capability_index.values():
            capability_set.discard(agent_id_str)

        if agent.domain and agent.domain in self.domain_index:
            self.domain_index[agent.domain].discard(agent_id_str)

        # Mark as inactive in database (soft delete)
        try:
            await db.execute(
                "UPDATE agents SET is_active = false, updated_at = NOW() WHERE id = $1",
                agent_id
            )
        except Exception as e:
            logger.warning(f"Failed to mark agent {agent.name} as inactive in database: {e}")

        logger.info(f"Deleted agent: {agent.name} ({agent_id})")
        return True

    async def get_registry_status(self) -> Dict[str, Any]:
        """
        Get registry status information.

        Returns:
            Dictionary with registry status, counts, and metrics
        """
        from .base import AgentStatus

        # Count agents by status
        status_counts = {
            AgentStatus.IDLE: 0,
            AgentStatus.PROCESSING: 0,
            AgentStatus.ERROR: 0,
            AgentStatus.STOPPED: 0,
            AgentStatus.CREATED: 0,
            AgentStatus.INITIALIZING: 0,
            AgentStatus.WAITING_FOR_TOOL: 0
        }

        for agent in self.agents.values():
            status_counts[agent.status] = status_counts.get(agent.status, 0) + 1

        # Active agents are those not ERROR or STOPPED
        active_agents = sum(
            count for status, count in status_counts.items()
            if status not in (AgentStatus.ERROR, AgentStatus.STOPPED)
        )

        return {
            "status": self.status.value,
            "total_agents": len(self.agents),
            "active_agents": active_agents,
            "idle_agents": status_counts[AgentStatus.IDLE],
            "processing_agents": status_counts[AgentStatus.PROCESSING],
            "error_agents": status_counts[AgentStatus.ERROR],
            "capabilities_available": list(self.capability_index.keys()),
            "domains_available": list(self.domain_index.keys())
        }

    async def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """
        Get agent by ID.

        Args:
            agent_id: Agent ID (string or UUID)

        Returns:
            Agent instance or None if not found
        """
        if isinstance(agent_id, UUID):
            agent_id = str(agent_id)

        # Check in-memory agents first
        agent = self.agents.get(agent_id)
        if agent:
            return agent

        # If not found in memory, try to load from database
        try:
            agent_data = await db.fetch_one(
                """
                SELECT id, name, agent_type, domain, description, system_prompt,
                       capabilities, supervisor_id, config
                FROM agents WHERE id = $1 AND is_active = true
                """,
                UUID(agent_id)
            )
            if agent_data:
                # Load agent from database data
                return await self._load_agent_from_db_data(agent_data)
        except Exception as e:
            logger.warning(f"Failed to load agent {agent_id} from database: {e}")

        return None

    async def get_agent_by_name(self, name: str) -> Optional[BaseAgent]:
        """
        Get agent by name.

        Args:
            name: Agent name

        Returns:
            Agent instance or None if not found
        """
        # First check in-memory agents
        for agent in self.agents.values():
            if agent.name == name:
                return agent

        # If not found in memory, check database
        try:
            agent_data = await db.fetch_one(
                """
                SELECT id, name, agent_type, domain, description, system_prompt,
                       capabilities, supervisor_id, config
                FROM agents WHERE name = $1 AND is_active = true
                """,
                name
            )
            if agent_data:
                # Agent exists in database but not in memory
                # Load it from database
                return await self._load_agent_from_db_data(agent_data)
        except Exception as e:
            logger.warning(f"Failed to check database for agent with name '{name}': {e}")

        return None

    async def find_agents_by_capability(self, capability: str) -> List[BaseAgent]:
        """
        Find agents with a specific capability.

        Args:
            capability: Capability to search for

        Returns:
            List of agents with the capability
        """
        agent_ids = self.capability_index.get(capability, set())
        agents = []

        for agent_id in agent_ids:
            agent = self.agents.get(agent_id)
            if agent and agent.status == AgentStatus.IDLE:
                agents.append(agent)

        return agents

    async def find_agents_by_domain(self, domain: str) -> List[BaseAgent]:
        """
        Find agents specialized in a domain.

        Args:
            domain: Domain to search for

        Returns:
            List of agents in the domain
        """
        agent_ids = self.domain_index.get(domain, set())
        agents = []

        for agent_id in agent_ids:
            agent = self.agents.get(agent_id)
            if agent and agent.status == AgentStatus.IDLE:
                agents.append(agent)

        return agents

    async def select_agent_for_task(
        self,
        task_description: str,
        required_capabilities: Optional[List[str]] = None,
        preferred_domain: Optional[str] = None,
        exclude_agent_ids: Optional[List[UUID]] = None
    ) -> Tuple[Optional[BaseAgent], float]:
        """
        Select the best agent for a task.

        Args:
            task_description: Description of the task
            required_capabilities: Required capabilities
            preferred_domain: Preferred domain specialization

        Returns:
            Selected agent or None if no suitable agent found
        """
        candidates = []

        # Filter by capabilities if specified
        if required_capabilities:
            capability_sets = [self.capability_index.get(cap, set()) for cap in required_capabilities]
            if capability_sets:
                # Intersection of all required capabilities
                candidate_ids = set.intersection(*capability_sets) if len(capability_sets) > 1 else capability_sets[0]
            else:
                candidate_ids = set()
        else:
            candidate_ids = set(self.agents.keys())

        # Filter by domain if specified
        if preferred_domain and preferred_domain in self.domain_index:
            domain_ids = self.domain_index[preferred_domain]
            candidate_ids = candidate_ids.intersection(domain_ids)

        # Exclude specified agents
        if exclude_agent_ids:
            exclude_ids = {str(agent_id) for agent_id in exclude_agent_ids}
            candidate_ids = candidate_ids - exclude_ids

        # Convert to agent objects and filter by status
        for agent_id in candidate_ids:
            agent = self.agents.get(agent_id)
            if agent and agent.status == AgentStatus.IDLE:
                candidates.append(agent)

        if not candidates:
            logger.warning(f"No suitable agents found for task: {task_description[:100]}")
            return None, 0.0

        # Score candidates (simplified)
        scored_candidates = []
        for agent in candidates:
            score = await self._score_agent_for_task(agent, task_description)
            scored_candidates.append((score, agent))

        # Select highest scoring agent
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        selected = scored_candidates[0][1]
        selected_score = scored_candidates[0][0]

        logger.debug(f"Selected agent {selected.name} for task: {task_description[:100]}")
        return selected, selected_score

    async def start_agent(self, agent_id: str) -> bool:
        """
        Start an agent (if stopped).

        Args:
            agent_id: Agent ID

        Returns:
            True if successful
        """
        agent = await self.get_agent(agent_id)
        if not agent:
            logger.error(f"Cannot start agent: {agent_id} not found")
            return False

        if agent.status == AgentStatus.STOPPED:
            try:
                await agent.initialize()
                logger.info(f"Started agent: {agent.name}")
                return True
            except Exception as e:
                logger.error(f"Failed to start agent {agent.name}: {e}")
                return False
        else:
            logger.warning(f"Agent {agent.name} already in state: {agent.status}")
            return True

    async def stop_agent(self, agent_id: str) -> bool:
        """
        Stop an agent.

        Args:
            agent_id: Agent ID

        Returns:
            True if successful
        """
        agent = await self.get_agent(agent_id)
        if not agent:
            logger.error(f"Cannot stop agent: {agent_id} not found")
            return False

        try:
            await agent.cleanup()
            logger.info(f"Stopped agent: {agent.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop agent {agent.name}: {e}")
            return False

    async def list_agents(self, include_status: bool = False) -> List[BaseAgent]:
        """
        List all registered agents.

        Args:
            include_status: Include agent status and metrics (always included in BaseAgent)

        Returns:
            List of BaseAgent instances
        """
        return list(self.agents.values())

    # ============ Internal Methods ============

    async def _register_builtin_types(self) -> None:
        """Register built-in agent types."""
        from .base import DomainAgent, OrchestratorAgent
        from .email_intelligence import EmailIntelligenceAgent
        from .swarm.agent import SwarmAgent
        from .decision_support import DecisionSupportAgent
        from .code_review import CodeReviewAgent
        from .schema_guardian import SchemaGuardianAgent
        from .test_synchronizer import TestSynchronizerAgent
        from .finance_agent import FinanceAgent

        builtin_types = {
            "domain": DomainAgent,
            "orchestrator": OrchestratorAgent,
            "email_intelligence": EmailIntelligenceAgent,
            "finance": FinanceAgent,
            "worker": SwarmAgent,  # Task-specific agents with swarm capabilities
            "supervisor": SwarmAgent,  # Manager agents with swarm capabilities
            "analyzer": DomainAgent,  # Analysis agents (default to DomainAgent)
            "decision_support": DecisionSupportAgent,
            "code_review": CodeReviewAgent,
            "schema_guardian": SchemaGuardianAgent,
            "test_synchronizer": TestSynchronizerAgent,
        }

        for type_name, agent_class in builtin_types.items():
            await self.register_agent_type(type_name, agent_class)

    async def _load_agents_from_db(self) -> None:
        """Load active agents from database."""
        try:
            # Try to load with config column (may not exist in older schemas)
            try:
                active_agents = await db.fetch_all(
                    """
                    SELECT id, name, agent_type, domain, description, system_prompt,
                           capabilities, supervisor_id, config
                    FROM agents WHERE is_active = true
                    """
                )
            except Exception as e:
                if 'column "config" does not exist' in str(e):
                    logger.warning("config column not found in agents table, using default empty config")
                    active_agents = await db.fetch_all(
                        """
                        SELECT id, name, agent_type, domain, description, system_prompt,
                               capabilities, supervisor_id
                        FROM agents WHERE is_active = true
                        """
                    )
                    # Add empty config to each agent data
                    for agent_data in active_agents:
                        agent_data["config"] = {}
                else:
                    raise

            logger.info(f"Found {len(active_agents)} active agents in database")

            for agent_data in active_agents:
                try:
                    # Determine agent type
                    agent_type = agent_data["agent_type"]
                    if agent_type not in self.agent_types:
                        logger.warning(f"Unknown agent type '{agent_type}' for agent {agent_data['name']}, skipping")
                        continue

                    # Create agent instance
                    agent_class = self.agent_types[agent_type]

                    # Convert agent_type string to AgentType enum
                    try:
                        agent_type_enum = AgentType(agent_type)
                    except ValueError:
                        logger.warning(f"Unknown AgentType enum value '{agent_type}' for agent {agent_data['name']}, defaulting to DOMAIN")
                        agent_type_enum = AgentType.DOMAIN

                    kwargs = {
                        "agent_id": str(agent_data["id"]),
                        "name": agent_data["name"],
                        "agent_type": agent_type_enum,
                        "description": agent_data["description"],
                        "system_prompt": agent_data["system_prompt"],
                        "capabilities": agent_data["capabilities"] or [],
                        "supervisor_id": str(agent_data["supervisor_id"]) if agent_data["supervisor_id"] else None,
                        "config": self._normalize_config(agent_data.get("config"))
                    }
                    if agent_type == "domain":
                        kwargs["domain"] = agent_data["domain"] if agent_data["domain"] else "general"

                    # Handle swarm-specific parameters for SwarmAgent classes
                    try:
                        from .swarm.agent import SwarmAgent
                        if issubclass(agent_class, SwarmAgent):
                            config = kwargs["config"]
                            if config:
                                # Extract swarm_id and swarm_role from config if present
                                if "swarm_id" in config:
                                    kwargs["swarm_id"] = config.get("swarm_id")
                                if "swarm_role" in config:
                                    kwargs["swarm_role"] = config.get("swarm_role", "member")
                    except ImportError:
                        # Swarm module not available, skip swarm parameter extraction
                        pass

                    agent = agent_class(**kwargs)

                    # Register but don't initialize yet
                    await self._register_agent(agent, skip_init=True)

                    logger.debug(f"Loaded agent from DB: {agent_data['name']}")

                except Exception as e:
                    logger.error(f"Failed to load agent {agent_data.get('name', 'unknown')}: {e}")

        except Exception as e:
            logger.error(f"Failed to load agents from database: {e}")
            raise

    async def _initialize_all_agents(self) -> None:
        """Initialize all loaded agents."""
        # Initialize in parallel with limit
        semaphore = asyncio.Semaphore(5)  # Limit concurrent initializations

        async def init_with_semaphore(agent):
            async with semaphore:
                try:
                    await agent.initialize()
                except Exception as e:
                    logger.error(f"Failed to initialize agent {agent.name}: {e}")

        await asyncio.gather(*[init_with_semaphore(agent) for agent in self.agents.values()])

    async def _stop_all_agents(self) -> None:
        """Stop all agents."""
        stop_tasks = []

        for agent in self.agents.values():
            if agent.status != AgentStatus.STOPPED:
                stop_tasks.append(agent.cleanup())

        # Stop in parallel with limit
        semaphore = asyncio.Semaphore(5)

        async def stop_with_semaphore(agent):
            async with semaphore:
                try:
                    await agent.cleanup()
                except Exception as e:
                    logger.error(f"Failed to stop agent {agent.name}: {e}")

        await asyncio.gather(*[stop_with_semaphore(agent) for agent in self.agents.values()])

    async def _register_agent(self, agent: BaseAgent, skip_init: bool = False) -> None:
        """
        Register an agent in the registry.

        Args:
            agent: Agent instance
            skip_init: Skip initialization (for loading from DB)
        """
        if agent.agent_id in self.agents:
            raise ValueError(f"Agent with ID {agent.agent_id} already registered")

        # Add to agents dictionary
        self.agents[agent.agent_id] = agent

        # Update capability index
        for capability in agent.capabilities:
            if capability not in self.capability_index:
                self.capability_index[capability] = set()
            self.capability_index[capability].add(agent.agent_id)

        # Update domain index if agent has a domain
        if hasattr(agent, 'domain') and agent.domain:
            domain = agent.domain
            if domain not in self.domain_index:
                self.domain_index[domain] = set()
            self.domain_index[domain].add(agent.agent_id)

        logger.debug(f"Registered agent: {agent.name}")

    async def _store_agent_in_db(self, agent: BaseAgent) -> None:
        """
        Store agent metadata in database.

        Creates or updates agent record with current configuration.
        """
        try:
            result = await db.fetch_one(
                """
                INSERT INTO agents (
                    id, name, display_name, description, agent_type, domain,
                    role, goal, backstory, system_prompt, capabilities,
                    supervisor_id, is_active, allow_delegation, max_iterations,
                    temperature, version, config, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, NOW(), NOW()
                ) ON CONFLICT (name) DO UPDATE SET
                    name = EXCLUDED.name,
                    display_name = EXCLUDED.display_name,
                    description = EXCLUDED.description,
                    agent_type = EXCLUDED.agent_type,
                    domain = EXCLUDED.domain,
                    role = EXCLUDED.role,
                    goal = EXCLUDED.goal,
                    backstory = EXCLUDED.backstory,
                    system_prompt = EXCLUDED.system_prompt,
                    capabilities = EXCLUDED.capabilities,
                    supervisor_id = EXCLUDED.supervisor_id,
                    is_active = EXCLUDED.is_active,
                    allow_delegation = EXCLUDED.allow_delegation,
                    max_iterations = EXCLUDED.max_iterations,
                    temperature = EXCLUDED.temperature,
                    version = EXCLUDED.version,
                    config = EXCLUDED.config,
                    updated_at = NOW()
                RETURNING id
                """,
                UUID(agent.agent_id),
                agent.name,
                agent.name,  # display_name same as name
                getattr(agent, 'description', ''),
                agent.agent_type.value if hasattr(agent.agent_type, 'value') else str(agent.agent_type),
                getattr(agent, 'domain', None),
                getattr(agent, 'role', 'assistant'),
                getattr(agent, 'goal', ''),
                getattr(agent, 'backstory', ''),
                getattr(agent, 'system_prompt', ''),
                getattr(agent, 'capabilities', []),
                UUID(getattr(agent, 'supervisor_id', None)) if getattr(agent, 'supervisor_id', None) else None,
                True,  # is_active
                True,  # allow_delegation
                getattr(agent, 'max_iterations', 10),
                getattr(agent, 'temperature', 0.7),
                1,  # version
                getattr(agent, 'config', {})  # config
            )

            # Check if the ID in database differs from agent's ID (name conflict occurred)
            db_agent_id = str(result["id"])
            if db_agent_id != agent.agent_id:
                logger.warning(
                    f"Agent name conflict: Agent '{agent.name}' already exists in database with ID {db_agent_id}. "
                    f"Updating agent ID from {agent.agent_id} to match existing database record."
                )
                # Update agent ID and registry mappings to match existing database record
                old_id = agent.agent_id

                # Remove old ID from registry
                if old_id in self.agents:
                    del self.agents[old_id]

                # Remove old ID from capability index
                for capability_set in self.capability_index.values():
                    capability_set.discard(old_id)

                # Remove old ID from domain index
                if hasattr(agent, 'domain') and agent.domain:
                    domain = agent.domain
                    if domain in self.domain_index:
                        self.domain_index[domain].discard(old_id)

                # Update agent ID
                agent.agent_id = db_agent_id

                # Re-register with new ID
                self.agents[agent.agent_id] = agent

                # Add to capability index with new ID
                for capability in agent.capabilities:
                    if capability not in self.capability_index:
                        self.capability_index[capability] = set()
                    self.capability_index[capability].add(agent.agent_id)

                # Add to domain index with new ID
                if hasattr(agent, 'domain') and agent.domain:
                    domain = agent.domain
                    if domain not in self.domain_index:
                        self.domain_index[domain] = set()
                    self.domain_index[domain].add(agent.agent_id)

            logger.debug(f"Stored agent {agent.name} in database (ID in DB: {db_agent_id})")
        except Exception as e:
            logger.error(f"Failed to store agent {agent.name} in database: {e}")
            # Don't raise - agent can still function in memory

    async def _score_agent_for_task(self, agent: BaseAgent, task_description: str) -> float:
        """
        Score an agent for a specific task.

        Simplified scoring algorithm:
        - Base score: 1.0
        - Bonus for high success rate
        - Bonus for low latency
        - Penalty for recent errors

        Args:
            agent: Agent to score
            task_description: Task description

        Returns:
            Score (higher is better)
        """
        score = 1.0

        # Success rate bonus
        success_rate = agent.metrics.get("success_rate", 1.0)
        score += success_rate * 0.5

        # Low latency bonus (inverse)
        avg_latency = agent.metrics.get("avg_latency_ms", 1000)
        if avg_latency > 0:
            score += 1000 / avg_latency * 0.1

        # Penalize recent errors
        if agent.status == AgentStatus.ERROR:
            score -= 0.5

        # TODO: Add semantic matching with task description
        # TODO: Consider agent workload

        return max(0.1, score)  # Ensure minimum score

    async def _update_indexes(self, agent: BaseAgent) -> None:
        """
        Update indexes for an agent.

        Called when agent capabilities or domain change.
        """
        # Remove old entries
        for capability_set in self.capability_index.values():
            capability_set.discard(agent.agent_id)

        if hasattr(agent, 'domain') and agent.domain:
            for domain_set in self.domain_index.values():
                domain_set.discard(agent.agent_id)

        # Add new entries
        for capability in agent.capabilities:
            if capability not in self.capability_index:
                self.capability_index[capability] = set()
            self.capability_index[capability].add(agent.agent_id)

        if hasattr(agent, 'domain') and agent.domain:
            domain = agent.domain
            if domain not in self.domain_index:
                self.domain_index[domain] = set()
            self.domain_index[domain].add(agent.agent_id)

    def _normalize_config(self, config_value):
        """
        Normalize config value to a dictionary.

        Handles:
        - None -> empty dict
        - String -> JSON parse
        - Dict -> return as-is
        - Other -> empty dict with warning
        """
        import json

        if config_value is None:
            return {}

        if isinstance(config_value, dict):
            return config_value

        if isinstance(config_value, str):
            try:
                return json.loads(config_value)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse config string as JSON: {config_value[:100]}")
                return {}

        # Unexpected type
        logger.warning(f"Unexpected config type {type(config_value)}, using empty dict")
        return {}

    async def _load_agent_from_db_data(self, agent_data: dict) -> Optional[BaseAgent]:
        """
        Load an agent from database data.

        Args:
            agent_data: Agent data from database query

        Returns:
            Agent instance or None if failed to load
        """
        try:
            # Determine agent type
            agent_type = agent_data["agent_type"]
            if agent_type not in self.agent_types:
                logger.warning(f"Unknown agent type '{agent_type}' for agent {agent_data['name']}, skipping")
                return None

            # Create agent instance
            agent_class = self.agent_types[agent_type]

            # Convert agent_type string to AgentType enum
            try:
                agent_type_enum = AgentType(agent_type)
            except ValueError:
                logger.warning(f"Unknown AgentType enum value '{agent_type}' for agent {agent_data['name']}, defaulting to DOMAIN")
                agent_type_enum = AgentType.DOMAIN

            kwargs = {
                "agent_id": str(agent_data["id"]),
                "name": agent_data["name"],
                "agent_type": agent_type_enum,
                "description": agent_data["description"],
                "system_prompt": agent_data["system_prompt"],
                "capabilities": agent_data["capabilities"] or [],
                "supervisor_id": str(agent_data["supervisor_id"]) if agent_data["supervisor_id"] else None,
                "config": self._normalize_config(agent_data.get("config"))
            }
            if agent_type == "domain":
                kwargs["domain"] = agent_data["domain"] if agent_data["domain"] else "general"

            # Handle swarm-specific parameters for SwarmAgent classes
            try:
                from .swarm.agent import SwarmAgent
                if issubclass(agent_class, SwarmAgent):
                    config = kwargs["config"]
                    if config:
                        # Extract swarm_id and swarm_role from config if present
                        if "swarm_id" in config:
                            kwargs["swarm_id"] = config.get("swarm_id")
                        if "swarm_role" in config:
                            kwargs["swarm_role"] = config.get("swarm_role", "member")
            except ImportError:
                # Swarm module not available, skip swarm parameter extraction
                pass

            agent = agent_class(**kwargs)

            # Register but don't initialize yet
            await self._register_agent(agent, skip_init=True)

            # Initialize the agent
            await agent.initialize()

            logger.debug(f"Loaded agent from DB: {agent_data['name']}")
            return agent

        except Exception as e:
            logger.error(f"Failed to load agent {agent_data.get('name', 'unknown')} from database data: {e}")
            return None


# Global registry instance
registry = AgentRegistry()


async def get_registry() -> AgentRegistry:
    """Dependency for FastAPI routes."""
    return registry