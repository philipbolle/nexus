"""
NEXUS Agent Framework - Pydantic Models

Request and response schemas for agent-related API endpoints.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal

from ..agents.base import AgentType, AgentStatus
from ..agents.tools import ToolType, ToolExecutionStatus


# ============ Agent Management Models ============

class AgentCreate(BaseModel):
    """Request schema for creating a new agent."""

    name: str = Field(..., min_length=1, max_length=100, description="Unique agent name")
    agent_type: AgentType = Field(..., description="Type of agent")
    description: str = Field("", max_length=500, description="Human-readable description")
    system_prompt: str = Field("", description="Default system prompt for this agent")
    capabilities: List[str] = Field(default_factory=list, description="List of agent capabilities")
    domain: Optional[str] = Field(None, max_length=100, description="Domain specialization")
    supervisor_id: Optional[UUID] = Field(None, description="ID of supervising agent")
    config: Dict[str, Any] = Field(default_factory=dict, description="Agent-specific configuration")


class AgentUpdate(BaseModel):
    """Request schema for updating an existing agent."""

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Agent name")
    description: Optional[str] = Field(None, max_length=500, description="Description")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    capabilities: Optional[List[str]] = Field(None, description="Capabilities")
    is_active: Optional[bool] = Field(None, description="Whether agent is active")
    config: Optional[Dict[str, Any]] = Field(None, description="Configuration")


class AgentResponse(BaseModel):
    """Response schema for agent information."""

    id: UUID
    name: str
    agent_type: AgentType
    description: str
    system_prompt: str
    capabilities: List[str]
    domain: Optional[str]
    supervisor_id: Optional[UUID]
    config: Dict[str, Any]
    status: AgentStatus
    metrics: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator('config', 'metrics', mode='before')
    @classmethod
    def validate_dict_fields(cls, v: Any, info):
        """Convert string '{}' to empty dict and ensure dict type for config and metrics."""
        field_name = info.field_name
        if isinstance(v, str):
            # Try to parse JSON string
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # If it's literally '{}' or '[]' etc, return empty dict
                if v.strip() == '{}':
                    return {}
                elif v.strip() == '':
                    return {}
                else:
                    raise ValueError(f"Could not parse {field_name} string as JSON: {v}")
        elif v is None:
            return {}
        return v


class AgentListResponse(BaseModel):
    """Response schema for listing agents."""

    agents: List[AgentResponse]
    total_count: int


# ============ Task Execution Models ============

class TaskRequest(BaseModel):
    """Request schema for submitting a task to an agent."""

    task: Union[str, Dict[str, Any]] = Field(..., description="Task description or structured task")
    agent_id: Optional[UUID] = Field(None, description="Specific agent to handle task")
    agent_name: Optional[str] = Field(None, description="Agent name (alternative to agent_id)")
    capabilities: Optional[List[str]] = Field(None, description="Required capabilities")
    domain: Optional[str] = Field(None, description="Preferred domain")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    session_id: Optional[UUID] = Field(None, description="Existing session ID")
    priority: int = Field(1, ge=1, le=5, description="Task priority (1-5)")


class TaskResponse(BaseModel):
    """Response schema for task execution."""

    # Core task fields from orchestrator
    task_id: UUID
    description: str
    status: str
    progress: Dict[str, Any]
    subtasks: List[Dict[str, Any]]
    submitted_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    # Original fields (optional for backward compatibility)
    success: bool = True
    agent_id: Optional[UUID] = None
    agent_name: Optional[str] = None
    session_id: Optional[UUID] = None
    result: Optional[Dict[str, Any]] = None
    error_type: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    processing_time_ms: int = 0


class SessionCreate(BaseModel):
    """Request schema for creating a new session."""

    title: str = Field(..., max_length=255, description="Session title")
    session_type: str = Field("chat", description="Type of session (chat, task, automation)")
    primary_agent_id: Optional[UUID] = Field(None, description="Primary agent for session")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session metadata")


class SessionResponse(BaseModel):
    """Response schema for session information."""

    id: UUID
    title: str
    session_type: str
    summary: Optional[str]
    primary_agent_id: Optional[UUID]
    agents_involved: List[UUID]
    total_messages: int
    total_tokens: int
    total_cost_usd: Decimal
    status: str
    started_at: datetime
    last_message_at: Optional[datetime]
    ended_at: Optional[datetime]
    metadata: Dict[str, Any]


class MessageCreate(BaseModel):
    """Request schema for adding a message to a session."""

    content: str = Field(..., description="Message content")
    role: str = Field(..., description="Message role (user, assistant, system, tool)")
    agent_id: Optional[UUID] = Field(None, description="Agent that generated the message")
    parent_message_id: Optional[UUID] = Field(None, description="Parent message ID")
    tool_calls: Optional[Dict[str, Any]] = Field(None, description="Tool calls made")
    tool_results: Optional[Dict[str, Any]] = Field(None, description="Tool execution results")


class MessageResponse(BaseModel):
    """Response schema for message information."""

    id: UUID
    session_id: UUID
    role: str
    content: str
    agent_id: Optional[UUID]
    parent_message_id: Optional[UUID]
    tool_calls: Optional[Dict[str, Any]]
    tool_results: Optional[Dict[str, Any]]
    tokens_input: Optional[int]
    tokens_output: Optional[int]
    cost_usd: Optional[Decimal]
    model_used: Optional[str]
    latency_ms: Optional[int]
    created_at: datetime


# ============ Tool Management Models ============

class ToolCreate(BaseModel):
    """Request schema for creating a new tool."""

    name: str = Field(..., min_length=1, max_length=100, description="Unique tool name")
    display_name: str = Field(..., max_length=100, description="Human-readable name")
    description: str = Field(..., description="Tool description")
    tool_type: ToolType = Field(..., description="Type of tool")
    input_schema: Dict[str, Any] = Field(..., description="JSON Schema for inputs")
    output_schema: Optional[Dict[str, Any]] = Field(None, description="JSON Schema for outputs")
    requires_confirmation: bool = Field(False, description="Whether tool requires human confirmation")


class ToolResponse(BaseModel):
    """Response schema for tool information."""

    id: UUID
    name: str
    display_name: str
    description: str
    tool_type: ToolType
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]]
    requires_confirmation: bool
    is_enabled: bool
    usage_count: int
    avg_execution_ms: Optional[int]
    created_at: datetime


class ToolExecutionRequest(BaseModel):
    """Request schema for executing a tool."""

    tool_name: str = Field(..., description="Name of tool to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    agent_id: Optional[UUID] = Field(None, description="Agent executing the tool")
    session_id: Optional[UUID] = Field(None, description="Session context")
    require_confirmation: bool = Field(False, description="Wait for human confirmation")


class ToolExecutionResponse(BaseModel):
    """Response schema for tool execution."""

    execution_id: UUID
    tool_name: str
    status: ToolExecutionStatus
    result: Optional[Any] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    created_at: datetime


# ============ Agent Performance Models ============

class AgentPerformanceQuery(BaseModel):
    """Request schema for querying agent performance."""

    agent_id: Optional[UUID] = Field(None, description="Filter by agent ID")
    start_date: Optional[date] = Field(None, description="Start date for metrics")
    end_date: Optional[date] = Field(None, description="End date for metrics")
    metric: Optional[str] = Field(None, description="Specific metric to retrieve")


class AgentPerformanceResponse(BaseModel):
    """Response schema for agent performance metrics."""

    agent_id: UUID
    agent_name: str
    date: date
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_tokens: int
    total_cost_usd: Decimal
    avg_latency_ms: float
    p50_latency_ms: Optional[int]
    p95_latency_ms: Optional[int]
    p99_latency_ms: Optional[int]
    avg_user_rating: Optional[float]
    total_ratings: int = 0
    tools_used: Dict[str, int] = Field(default_factory=dict)


# ============ Agent Delegation Models ============

class DelegationRequest(BaseModel):
    """Request schema for delegating a task to another agent."""

    task: Union[str, Dict[str, Any]] = Field(..., description="Task to delegate")
    target_agent_id: UUID = Field(..., description="Agent to receive task")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    reason: Optional[str] = Field(None, description="Reason for delegation")


class DelegationResponse(BaseModel):
    """Response schema for delegation."""

    handoff_id: UUID
    from_agent_id: UUID
    from_agent_name: str
    to_agent_id: UUID
    to_agent_name: str
    task: Union[str, Dict[str, Any]]
    reason: Optional[str]
    status: str
    created_at: datetime


# ============ Registry Models ============

class RegistryStatusResponse(BaseModel):
    """Response schema for registry status."""

    status: str
    total_agents: int
    active_agents: int
    idle_agents: int
    processing_agents: int
    error_agents: int
    capabilities_available: List[str]
    domains_available: List[str]


class AgentSelectionRequest(BaseModel):
    """Request schema for selecting an agent for a task."""

    task_description: str = Field(..., description="Task description")
    required_capabilities: Optional[List[str]] = Field(None, description="Required capabilities")
    preferred_domain: Optional[str] = Field(None, description="Preferred domain")
    exclude_agent_ids: Optional[List[UUID]] = Field(None, description="Agents to exclude")


class AgentSelectionResponse(BaseModel):
    """Response schema for agent selection."""

    selected_agent_id: UUID
    selected_agent_name: str
    agent_type: AgentType
    capabilities: List[str]
    domain: Optional[str]
    score: float
    alternative_agents: List[Dict[str, Any]]


# ============ Error Models ============

class AgentError(BaseModel):
    """Schema for agent errors."""

    error_id: UUID
    agent_id: UUID
    agent_name: str
    error_type: str
    error_message: str
    severity: str
    context: Dict[str, Any]
    resolved: bool
    created_at: datetime
    resolved_at: Optional[datetime]


# ============ Validation Methods ============

class AgentSchemas:
    """Utility class for schema-related operations."""

    @staticmethod
    def validate_task(task: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Validate and normalize task input."""
        if isinstance(task, str):
            return {"description": task, "type": "text"}
        elif isinstance(task, dict):
            if "description" not in task:
                raise ValueError("Task dictionary must contain 'description' field")
            return task
        else:
            raise ValueError("Task must be string or dictionary")

    @staticmethod
    def validate_capabilities(capabilities: List[str]) -> List[str]:
        """Validate capability strings."""
        validated = []
        for cap in capabilities:
            if not isinstance(cap, str) or len(cap) == 0:
                raise ValueError(f"Invalid capability: {cap}")
            validated.append(cap.strip().lower())
        return validated

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate agent configuration."""
        # Ensure config is JSON serializable
        try:
            import json
            json.dumps(config)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Configuration must be JSON serializable: {e}")
        return config