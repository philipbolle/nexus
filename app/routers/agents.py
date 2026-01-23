"""
NEXUS Agent Framework API Endpoints

Agent management, task execution, session management, and performance monitoring.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from typing import List, Optional, Dict, Any
from uuid import UUID
from decimal import Decimal
import logging
import asyncio

from ..database import db, get_db, Database
from ..config import settings
from ..models.agent_schemas import (
    AgentCreate, AgentUpdate, AgentResponse, AgentListResponse,
    TaskRequest, TaskResponse,
    SessionCreate, SessionResponse,
    MessageCreate, MessageResponse,
    ToolCreate, ToolResponse, ToolExecutionRequest, ToolExecutionResponse,
    AgentPerformanceQuery, AgentPerformanceResponse,
    DelegationRequest, DelegationResponse,
    RegistryStatusResponse, AgentSelectionRequest, AgentSelectionResponse,
    AgentError
)

# Import agent framework components
from ..agents.base import AgentStatus
from ..agents.registry import AgentRegistry
from ..agents.tools import ToolSystem
from ..agents.email_intelligence import register_email_agent
from ..agents.decision_support import register_decision_support_agent
from ..agents.code_review import register_code_review_agent
from ..agents.schema_guardian import register_schema_guardian_agent
from ..agents.test_synchronizer import register_test_synchronizer_agent
from ..agents.sessions import SessionManager, SessionConfig
from ..agents.orchestrator import OrchestratorEngine
from ..agents.memory import MemorySystem
from ..agents.monitoring import PerformanceMonitor

router = APIRouter(tags=["agents"])
logger = logging.getLogger(__name__)

# Initialize singleton components
agent_registry = AgentRegistry()
tool_system = ToolSystem()
session_manager = SessionManager()
orchestrator = OrchestratorEngine()
memory_system = MemorySystem()
performance_monitor = PerformanceMonitor()

# Track initialization status
_components_initialized = False


async def initialize_agent_framework() -> None:
    """Initialize all agent framework components."""
    global _components_initialized

    if _components_initialized:
        return

    logger.info("Initializing agent framework components...")

    try:
        # Initialize agent registry
        await agent_registry.initialize()

        # Initialize tool system
        await tool_system.initialize()

        # Initialize performance monitor with registry
        await performance_monitor.initialize(agent_registry)

        # Initialize other components as needed
        # (SessionManager, OrchestratorEngine, MemorySystem may not need explicit initialization)

        # Register email agent
        try:
            await register_email_agent()
            logger.info("Email agent registered successfully")
        except Exception as e:
            logger.warning(f"Failed to register email agent: {e}. System will continue without email agent.")

        # Register decision support agent
        try:
            await register_decision_support_agent()
            logger.info("Decision support agent registered successfully")
        except Exception as e:
            logger.warning(f"Failed to register decision support agent: {e}. System will continue without decision support agent.")

        # Register code review agent
        try:
            await register_code_review_agent()
            logger.info("Code review agent registered successfully")
        except Exception as e:
            logger.warning(f"Failed to register code review agent: {e}. System will continue without code review agent.")

        # Register schema guardian agent
        try:
            await register_schema_guardian_agent()
            logger.info("Schema guardian agent registered successfully")
        except Exception as e:
            logger.warning(f"Failed to register schema guardian agent: {e}. System will continue without schema guardian agent.")

        # Register test synchronizer agent
        try:
            await register_test_synchronizer_agent()
            logger.info("Test synchronizer agent registered successfully")
        except Exception as e:
            logger.warning(f"Failed to register test synchronizer agent: {e}. System will continue without test synchronizer agent.")

        _components_initialized = True
        logger.info("Agent framework components initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize agent framework: {e}")
        raise


# ============ Dependency Injection Functions ============

async def get_agent_registry() -> AgentRegistry:
    """Dependency for agent registry."""
    return agent_registry


async def get_tool_system() -> ToolSystem:
    """Dependency for tool system."""
    return tool_system


async def get_session_manager() -> SessionManager:
    """Dependency for session manager."""
    return session_manager


async def get_orchestrator() -> OrchestratorEngine:
    """Dependency for orchestrator."""
    return orchestrator


async def get_memory_system() -> MemorySystem:
    """Dependency for memory system."""
    return memory_system


async def get_performance_monitor() -> PerformanceMonitor:
    """Dependency for performance monitor."""
    return performance_monitor


async def _agent_to_response(agent: "BaseAgent") -> AgentResponse:
    """Convert BaseAgent instance to AgentResponse."""
    from ..agents.base import BaseAgent, AgentType, AgentStatus
    import json

    def normalize_config(val):
        """Normalize config value to dict."""
        if val is None:
            return {}
        if isinstance(val, dict):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                return {}
        return {}

    # Try to fetch from database first
    agent_data = None
    try:
        agent_data = await db.fetch_one(
            """
            SELECT id, name, agent_type, description, system_prompt, capabilities,
                   domain, supervisor_id, config, created_at, updated_at
            FROM agents WHERE id = $1
            """,
            UUID(agent.agent_id)
        )
    except Exception as e:
        logger.debug(f"Failed to fetch agent {agent.agent_id} from database: {e}")

    if agent_data:
        # Use database data
        return AgentResponse(
            id=agent_data["id"],
            name=agent_data["name"],
            agent_type=AgentType(agent_data["agent_type"]),
            description=agent_data["description"] or "",
            system_prompt=agent_data["system_prompt"] or "",
            capabilities=agent_data["capabilities"] or [],
            domain=agent_data["domain"],
            supervisor_id=agent_data["supervisor_id"],
            config=normalize_config(agent_data.get("config")),
            status=agent.status,
            metrics=agent.metrics,
            created_at=agent_data["created_at"],
            updated_at=agent_data["updated_at"]
        )
    else:
        # Fall back to agent instance attributes
        from datetime import datetime
        return AgentResponse(
            id=UUID(agent.agent_id),
            name=agent.name,
            agent_type=getattr(agent, 'agent_type', AgentType.DOMAIN),
            description=getattr(agent, 'description', ''),
            system_prompt=getattr(agent, 'system_prompt', ''),
            capabilities=getattr(agent, 'capabilities', []),
            domain=getattr(agent, 'domain', None),
            supervisor_id=getattr(agent, 'supervisor_id', None),
            config=agent.config or {},
            status=agent.status,
            metrics=agent.metrics,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )


# ============ Agent Management Endpoints ============

@router.get("/agents", response_model=AgentListResponse)
async def list_agents(
    skip: int = Query(0, ge=0, description="Number of agents to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of agents to return"),
    active_only: bool = Query(False, description="Only return active agents"),
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """List all registered agents with optional filtering."""
    agents = await registry.list_agents()

    # Apply filters
    filtered_agents = agents
    if active_only:
        # Active means not ERROR or STOPPED
        filtered_agents = [a for a in filtered_agents if a.status not in (AgentStatus.ERROR, AgentStatus.STOPPED)]
    if agent_type:
        filtered_agents = [a for a in filtered_agents if a.agent_type.value == agent_type]

    # Apply pagination
    total_count = len(filtered_agents)
    paginated_agents = filtered_agents[skip:skip + limit]

    # Convert to response models
    converted_agents = await asyncio.gather(
        *[_agent_to_response(agent) for agent in paginated_agents]
    )

    return AgentListResponse(
        agents=converted_agents,
        total_count=total_count
    )


@router.post("/agents", response_model=AgentResponse, status_code=201)
async def create_agent(
    agent_data: AgentCreate,
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Create a new agent."""
    try:
        agent = await registry.register_agent(
            name=agent_data.name,
            agent_type=agent_data.agent_type.value,
            description=agent_data.description,
            system_prompt=agent_data.system_prompt,
            capabilities=agent_data.capabilities,
            domain=agent_data.domain,
            supervisor_id=agent_data.supervisor_id,
            config=agent_data.config
        )
        return await _agent_to_response(agent)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============ Registry & Agent Selection Endpoints ============

@router.get("/registry-status", response_model=RegistryStatusResponse)
async def get_registry_status(
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Get the current status of the agent registry."""
    status = await registry.get_registry_status()
    return status


@router.post("/registry-select-agent", response_model=AgentSelectionResponse)
async def select_agent(
    selection_request: AgentSelectionRequest,
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Select the most appropriate agent for a given task."""
    try:
        selection, score = await registry.select_agent_for_task(
            task_description=selection_request.task_description,
            required_capabilities=selection_request.required_capabilities,
            preferred_domain=selection_request.preferred_domain,
            exclude_agent_ids=selection_request.exclude_agent_ids
        )
        if not selection:
            raise HTTPException(status_code=404, detail="No suitable agent found")

        # Convert to response format
        return AgentSelectionResponse(
            selected_agent_id=UUID(selection.agent_id),
            selected_agent_name=selection.name,
            agent_type=selection.agent_type,
            capabilities=selection.capabilities,
            domain=selection.domain,
            score=score,
            alternative_agents=[]
        )
    except Exception as e:
        logger.error(f"Failed to select agent: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Get detailed information about a specific agent."""
    agent = await registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return await _agent_to_response(agent)


@router.put("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    agent_update: AgentUpdate,
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Update an existing agent's configuration."""
    try:
        agent = await registry.update_agent(
            agent_id=agent_id,
            **agent_update.dict(exclude_unset=True)
        )
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return await _agent_to_response(agent)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update agent: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: UUID,
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Delete an agent (marks as inactive, doesn't remove from database)."""
    success = await registry.delete_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.post("/agents/{agent_id}/start", response_model=AgentResponse)
async def start_agent(
    agent_id: UUID,
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Start an agent (activate it for task processing)."""
    try:
        success = await registry.start_agent(agent_id)
        if not success:
            raise HTTPException(status_code=404, detail="Agent not found or already started")
        agent = await registry.get_agent(agent_id)
        return await _agent_to_response(agent)
    except Exception as e:
        logger.error(f"Failed to start agent: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start agent: {e}")


@router.post("/agents/{agent_id}/stop", response_model=AgentResponse)
async def stop_agent(
    agent_id: UUID,
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Stop an agent (deactivate it)."""
    try:
        success = await registry.stop_agent(agent_id)
        if not success:
            raise HTTPException(status_code=404, detail="Agent not found or already stopped")
        agent = await registry.get_agent(agent_id)
        return await _agent_to_response(agent)
    except Exception as e:
        logger.error(f"Failed to stop agent: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop agent: {e}")


@router.get("/agents/{agent_id}/status")
async def get_agent_status(
    agent_id: UUID,
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Get the current status and metrics of an agent."""
    agent = await registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get real-time metrics from performance monitor
    metrics = await performance_monitor.get_agent_metrics(agent_id)

    return {
        "agent_id": agent_id,
        "status": agent.status.value,
        "is_active": agent.status == "active",
        "current_tasks": agent.metrics.get("current_tasks", 0),
        "total_tasks": agent.metrics.get("total_tasks", 0),
        "success_rate": agent.metrics.get("success_rate", 0),
        "metrics": metrics
    }


# ============ Task Execution Endpoints ============

@router.post("/tasks", response_model=TaskResponse)
async def submit_task(
    task_request: TaskRequest,
    background_tasks: BackgroundTasks,
    registry: AgentRegistry = Depends(get_agent_registry),
    orchestrator: OrchestratorEngine = Depends(get_orchestrator)
):
    """Submit a task for execution by the agent framework."""
    try:
        # Validate task
        from ..models.agent_schemas import AgentSchemas
        validated_task = AgentSchemas.validate_task(task_request.task)

        # Select agent if not specified
        agent_id = task_request.agent_id
        if not agent_id:
            # Use agent selection logic
            selected_agent = await registry.select_agent_for_task(
                task_description=validated_task.get("description", ""),
                required_capabilities=task_request.capabilities,
                preferred_domain=task_request.domain
            )
            if not selected_agent:
                raise HTTPException(status_code=404, detail="No suitable agent found")
            agent_id = selected_agent.id

        # Submit task to orchestrator
        task_id = await orchestrator.submit_task(
            task=validated_task,
            context=task_request.context,
            priority=task_request.priority
        )

        # Get task status for response
        task_data = await orchestrator.get_task_status(task_id)
        if not task_data:
            raise HTTPException(status_code=500, detail="Task submission failed")

        # Get agent info
        agent = await registry.get_agent(agent_id)
        agent_name = agent.name if agent else "Unknown"

        # Convert to TaskResponse
        from uuid import UUID
        response_data = {
            "task_id": UUID(task_data["task_id"]),
            "description": task_data["description"],
            "status": task_data["status"],
            "progress": task_data["progress"],
            "subtasks": task_data["subtasks"],
            "submitted_at": task_data["submitted_at"],
            "started_at": task_data.get("started_at"),
            "completed_at": task_data.get("completed_at"),
            "error": task_data.get("error"),
            "success": task_data.get("status") != "failed",
            "agent_id": agent_id,
            "agent_name": agent_name,
            "session_id": task_request.session_id,
            "result": None,
            "error_type": None,
            "metrics": {},
            "processing_time_ms": 0
        }

        return TaskResponse(**response_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit task: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(
    task_id: UUID,
    orchestrator: OrchestratorEngine = Depends(get_orchestrator)
):
    """Get the status and result of a specific task."""
    task_data = await orchestrator.get_task_status(task_id)
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")

    # Convert to TaskResponse
    from uuid import UUID
    response_data = {
        "task_id": UUID(task_data["task_id"]),
        "description": task_data["description"],
        "status": task_data["status"],
        "progress": task_data["progress"],
        "subtasks": task_data["subtasks"],
        "submitted_at": task_data["submitted_at"],
        "started_at": task_data.get("started_at"),
        "completed_at": task_data.get("completed_at"),
        "error": task_data.get("error"),
        "success": task_data.get("status") != "failed",
        "agent_id": None,
        "agent_name": None,
        "session_id": None,
        "result": None,
        "error_type": None,
        "metrics": {},
        "processing_time_ms": 0
    }

    return TaskResponse(**response_data)


@router.post("/tasks/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: UUID,
    orchestrator: OrchestratorEngine = Depends(get_orchestrator)
):
    """Cancel a running task."""
    task = await orchestrator.cancel_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ============ Session Management Endpoints ============

@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_session(
    session_data: SessionCreate,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """Create a new agent session."""
    try:
        # Create session configuration
        config = SessionConfig()
        config.metadata = session_data.metadata
        # session_type is handled by session_mgr.create_session via session_type parameter

        # Convert UUID to string for session manager
        primary_agent_id_str = str(session_data.primary_agent_id) if session_data.primary_agent_id else None

        session_id = await session_mgr.create_session(
            title=session_data.title,
            session_type=session_data.session_type,
            primary_agent_id=primary_agent_id_str,
            config=config
        )
        # Get created session
        session_dict = await session_mgr.get_session(session_id)
        if not session_dict:
            raise HTTPException(status_code=500, detail="Failed to retrieve created session")

        # Convert to SessionResponse
        return SessionResponse(
            id=UUID(session_dict["id"]),
            title=session_dict["title"],
            session_type=session_dict["session_type"],
            summary=session_dict.get("summary", ""),
            primary_agent_id=UUID(session_dict["primary_agent_id"]) if session_dict["primary_agent_id"] else None,
            agents_involved=[UUID(agent_id) for agent_id in session_dict["agents_involved"]],
            total_messages=session_dict.get("message_count", 0),
            total_tokens=session_dict.get("total_tokens", 0),
            total_cost_usd=Decimal(str(session_dict.get("total_cost_usd", 0.0))),
            status=session_dict["status"],
            started_at=session_dict["started_at"],
            last_message_at=session_dict.get("last_message_at", session_dict["started_at"]),
            ended_at=None,
            metadata=session_dict.get("metadata", {})
        )
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """Get detailed information about a session."""
    session = await session_mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    skip: int = Query(0, ge=0, description="Number of sessions to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of sessions to return"),
    session_type: Optional[str] = Query(None, description="Filter by session type"),
    active_only: bool = Query(False, description="Only return active sessions"),
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """List all sessions with optional filtering."""
    sessions = await session_mgr.list_sessions()

    # Apply filters
    filtered_sessions = sessions
    if session_type:
        filtered_sessions = [s for s in filtered_sessions if s.session_type == session_type]
    if active_only:
        filtered_sessions = [s for s in filtered_sessions if s.status == "active"]

    # Apply pagination
    paginated_sessions = filtered_sessions[skip:skip + limit]
    return paginated_sessions


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def add_message(
    session_id: UUID,
    message_data: MessageCreate,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """Add a message to a session."""
    try:
        message = await session_mgr.add_message(
            session_id=session_id,
            content=message_data.content,
            role=message_data.role,
            agent_id=message_data.agent_id,
            parent_message_id=message_data.parent_message_id,
            tool_calls=message_data.tool_calls,
            tool_results=message_data.tool_results
        )
        return message
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    session_id: UUID,
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of messages to return"),
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """Get all messages in a session."""
    messages = await session_mgr.get_messages(session_id)
    if messages is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Apply pagination
    paginated_messages = messages[skip:skip + limit]
    return paginated_messages


@router.post("/sessions/{session_id}/end")
async def end_session(
    session_id: UUID,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """End a session (mark as completed)."""
    success = await session_mgr.end_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "session_ended"}


# ============ Tool Management Endpoints ============

@router.get("/tools", response_model=List[ToolResponse])
async def list_tools(
    enabled_only: bool = Query(True, description="Only return enabled tools"),
    tool_type: Optional[str] = Query(None, description="Filter by tool type"),
    tool_sys: ToolSystem = Depends(get_tool_system)
):
    """List all registered tools."""
    tools = await tool_sys.list_tools()

    # Apply filters - tools are dictionaries from ToolSystem
    filtered_tools = tools
    if enabled_only:
        filtered_tools = [t for t in filtered_tools if t.get("is_enabled", True)]
    if tool_type:
        filtered_tools = [t for t in filtered_tools if str(t.get("tool_type", "")) == tool_type]

    return filtered_tools


@router.post("/tools", response_model=ToolResponse, status_code=201)
async def create_tool(
    tool_data: ToolCreate,
    tool_sys: ToolSystem = Depends(get_tool_system)
):
    """Register a new tool."""
    try:
        tool = await tool_sys.register_tool_from_api(
            name=tool_data.name,
            display_name=tool_data.display_name,
            description=tool_data.description,
            tool_type=tool_data.tool_type,
            input_schema=tool_data.input_schema,
            output_schema=tool_data.output_schema,
            requires_confirmation=tool_data.requires_confirmation
        )
        return tool
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to register tool: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/tools/execute", response_model=ToolExecutionResponse)
async def execute_tool(
    execution_request: ToolExecutionRequest,
    background_tasks: BackgroundTasks,
    tool_sys: ToolSystem = Depends(get_tool_system),
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """Execute a tool directly (bypassing agent)."""
    try:
        result = await tool_sys.execute_tool(
            tool_name=execution_request.tool_name,
            agent_id=execution_request.agent_id,
            session_id=execution_request.session_id,
            **execution_request.parameters
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to execute tool: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============ Performance Monitoring Endpoints ============

@router.get("/agents/{agent_id}/performance", response_model=List[AgentPerformanceResponse])
async def get_agent_performance(
    agent_id: UUID,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    metric: Optional[str] = Query(None, description="Specific metric to retrieve"),
    monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Get performance metrics for a specific agent."""
    try:
        query = AgentPerformanceQuery(
            agent_id=agent_id,
            start_date=start_date,
            end_date=end_date,
            metric=metric
        )
        metrics = await monitor.get_agent_performance_history(query.dict())
        return metrics
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/system/performance")
async def get_system_performance(
    monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Get overall system performance metrics."""
    try:
        metrics = await monitor.get_system_performance()
        return metrics
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/system/alerts")
async def get_system_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    resolved: Optional[bool] = Query(None, description="Filter by resolved status"),
    monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Get active system alerts."""
    alerts = await monitor.get_alerts(severity=severity, resolved=resolved)
    return {"alerts": alerts}


# ============ Delegation Endpoints ============

@router.post("/agents/{agent_id}/delegate", response_model=DelegationResponse)
async def delegate_task(
    agent_id: UUID,
    delegation_request: DelegationRequest,
    registry: AgentRegistry = Depends(get_agent_registry),
    orchestrator: OrchestratorEngine = Depends(get_orchestrator)
):
    """Delegate a task from one agent to another."""
    try:
        # Verify source agent exists
        source_agent = await registry.get_agent(agent_id)
        if not source_agent:
            raise HTTPException(status_code=404, detail="Source agent not found")

        # Verify target agent exists
        target_agent = await registry.get_agent(delegation_request.target_agent_id)
        if not target_agent:
            raise HTTPException(status_code=404, detail="Target agent not found")

        # Create delegation
        delegation = await orchestrator.delegate_task(
            from_agent_id=agent_id,
            to_agent_id=delegation_request.target_agent_id,
            task=delegation_request.task,
            context=delegation_request.context,
            reason=delegation_request.reason
        )

        return delegation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delegate task: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============ Memory System Endpoints ============

@router.get("/memory/{agent_id}")
async def get_agent_memory(
    agent_id: UUID,
    memory_type: Optional[str] = Query(None, description="Filter by memory type"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of memories to return"),
    memory_sys: MemorySystem = Depends(get_memory_system)
):
    """Get memories for a specific agent."""
    try:
        memories = await memory_sys.get_memories(
            agent_id=agent_id,
            memory_type=memory_type,
            limit=limit
        )
        return {"memories": memories}
    except Exception as e:
        logger.error(f"Failed to get agent memories: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/memory/{agent_id}/query")
async def query_memory(
    agent_id: UUID,
    query: Dict[str, Any],
    memory_sys: MemorySystem = Depends(get_memory_system)
):
    """Query agent memory with semantic search."""
    try:
        text = query.get("text", "")
        limit = query.get("limit", 10)
        threshold = query.get("threshold", 0.7)

        results = await memory_sys.query_memory(
            agent_id=agent_id,
            query_text=text,
            limit=limit,
            similarity_threshold=threshold
        )
        return {"results": results}
    except Exception as e:
        logger.error(f"Failed to query memory: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/memory/{agent_id}/store")
async def store_memory(
    agent_id: UUID,
    memory_data: Dict[str, Any],
    memory_sys: MemorySystem = Depends(get_memory_system)
):
    """Store a new memory for an agent."""
    try:
        content = memory_data.get("content", "")
        memory_type_str = memory_data.get("type", "semantic")
        metadata = memory_data.get("metadata", {})
        # Convert string to MemoryType enum
        try:
            from ..agents.memory import MemoryType
            memory_type = MemoryType(memory_type_str)
        except ValueError:
            # Default to SEMANTIC if invalid
            logger.warning(f"Invalid memory type '{memory_type_str}', defaulting to SEMANTIC")
            memory_type = MemoryType.SEMANTIC

        memory_id = await memory_sys.store_memory(
            agent_id=agent_id,
            content=content,
            memory_type=memory_type,
            metadata=metadata
        )
        return {"memory_id": memory_id, "status": "stored"}
    except Exception as e:
        logger.error(f"Failed to store memory: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============ Error Reporting Endpoints ============

@router.get("/agents/{agent_id}/errors")
async def get_agent_errors(
    agent_id: UUID,
    resolved: Optional[bool] = Query(None, description="Filter by resolved status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Get errors for a specific agent."""
    errors = await monitor.get_agent_errors(
        agent_id=agent_id,
        resolved=resolved,
        severity=severity
    )
    return {"errors": errors}


@router.post("/agents/{agent_id}/errors/{error_id}/resolve")
async def resolve_error(
    agent_id: UUID,
    error_id: UUID,
    monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Mark an agent error as resolved."""
    success = await monitor.resolve_error(error_id)
    if not success:
        raise HTTPException(status_code=404, detail="Error not found")
    return {"status": "resolved"}