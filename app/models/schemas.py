"""
NEXUS Pydantic Models
Request/response schemas for API validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID
from decimal import Decimal


# ============ Chat Models ============

class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    message: str = Field(..., min_length=1, max_length=10000)
    model: Optional[str] = None  # Override default model


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    response: str
    model_used: str
    tokens_used: int
    cost_usd: float
    latency_ms: int
    cached: bool = False


# ============ Finance Models ============

class ExpenseCreate(BaseModel):
    """Create a new expense."""
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    category: str = Field(..., min_length=1)
    description: Optional[str] = None
    merchant: Optional[str] = None
    transaction_date: Optional[date] = None  # Defaults to today


class ExpenseResponse(BaseModel):
    """Response after creating expense."""
    id: UUID
    amount: Decimal
    category: str
    description: Optional[str]
    merchant: Optional[str]
    transaction_date: date
    budget_remaining: Optional[Decimal] = None
    message: str


class BudgetStatus(BaseModel):
    """Current budget status."""
    month: str
    total_budget: Decimal
    total_spent: Decimal
    remaining: Decimal
    percent_used: float
    categories: List[dict]


class DebtProgress(BaseModel):
    """Debt payoff progress."""
    debt_name: str
    creditor: str
    original_amount: Decimal
    current_balance: Decimal
    paid_amount: Decimal
    percent_paid: float
    monthly_payment: Optional[Decimal]
    projected_payoff_date: Optional[date]


class DebtSummary(BaseModel):
    """Summary of all debts."""
    total_original: Decimal
    total_current: Decimal
    total_paid: Decimal
    percent_paid: float
    debts: List[DebtProgress]


# ============ Health Check Models ============

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime


class ServiceStatus(BaseModel):
    """Individual service status."""
    name: str
    status: str
    details: Optional[str] = None


class StatusResponse(BaseModel):
    """System status response."""
    status: str
    services: List[ServiceStatus]
    database_tables: int
    uptime_seconds: Optional[float] = None


# ============ API Usage Models ============

class APIUsageLog(BaseModel):
    """Log entry for API usage."""
    provider: str
    model: str
    endpoint: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None
    query_hash: Optional[str] = None


# ============ Swarm Models ============

class SwarmCreate(BaseModel):
    """Create a new swarm."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    purpose: str = Field(..., min_length=1)
    swarm_type: str = Field(default="collaborative")
    max_members: int = Field(default=10, gt=0)
    auto_scaling: bool = Field(default=True)
    health_check_interval_seconds: int = Field(default=60, gt=0)
    metadata: Optional[dict] = None


class SwarmUpdate(BaseModel):
    """Update swarm configuration."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    purpose: Optional[str] = Field(None, min_length=1)
    swarm_type: Optional[str] = None
    max_members: Optional[int] = Field(None, gt=0)
    auto_scaling: Optional[bool] = None
    health_check_interval_seconds: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None
    metadata: Optional[dict] = None


class SwarmResponse(BaseModel):
    """Swarm response."""
    id: UUID
    name: str
    description: Optional[str]
    purpose: str
    swarm_type: str
    max_members: int
    auto_scaling: bool
    health_check_interval_seconds: int
    is_active: bool
    metadata: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        extra = "ignore"


class SwarmMembershipCreate(BaseModel):
    """Add agent to swarm."""
    agent_id: UUID
    role: str = Field(default="member")
    metadata: Optional[dict] = None
    vote_weight: Optional[float] = None


class SwarmMembershipResponse(BaseModel):
    """Swarm membership response."""
    id: UUID
    swarm_id: UUID
    agent_id: UUID
    agent_name: Optional[str] = None
    agent_type: Optional[str] = None
    role: str
    status: str
    last_seen_at: Optional[datetime]
    metadata: dict
    joined_at: datetime
    contribution_score: float = Field(default=0.0)
    vote_weight: float = Field(default=0.0)


class ConsensusGroupCreate(BaseModel):
    """Create consensus group."""
    group_name: str = Field(..., min_length=1)
    current_term: Optional[int] = Field(default=0, ge=0)
    voted_for: Optional[UUID] = None
    commit_index: Optional[int] = Field(default=0, ge=0)
    last_applied_index: Optional[int] = Field(default=0, ge=0)
    leader_id: Optional[UUID] = None
    state: Optional[str] = Field(default="follower")


class ConsensusGroupResponse(BaseModel):
    """Consensus group response."""
    id: UUID
    swarm_id: UUID
    group_name: str
    current_term: int
    voted_for: Optional[UUID]
    commit_index: int
    last_applied_index: int
    leader_id: Optional[UUID]
    state: str
    created_at: datetime
    updated_at: datetime


class VoteCreate(BaseModel):
    """Create a vote."""
    vote_type: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    options: List[str] = Field(..., min_items=2)
    voting_strategy: str = Field(default="simple_majority")
    required_quorum: float = Field(default=0.5, ge=0.0, le=1.0)
    created_by_agent_id: UUID
    expires_at: Optional[datetime] = None
    metadata: Optional[dict] = None


class VoteResponse(BaseModel):
    """Vote response."""
    id: UUID
    swarm_id: UUID
    vote_type: str
    subject: str
    description: str
    options: List[str]
    voting_strategy: str
    required_quorum: float
    status: str
    created_by_agent_id: UUID
    expires_at: Optional[datetime]
    metadata: dict
    created_at: datetime
    updated_at: datetime


class VoteCast(BaseModel):
    """Cast a vote."""
    agent_id: UUID
    option: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    rationale: Optional[str] = None
    metadata: Optional[dict] = None


class SwarmMessageSend(BaseModel):
    """Send swarm message."""
    sender_agent_id: UUID
    recipient_agent_id: Optional[UUID] = None
    channel: str = Field(default="general")
    message_type: str = Field(default="text")
    content: str = Field(..., min_length=1)
    priority: int = Field(default=1, ge=1, le=5)
    ttl_seconds: Optional[int] = Field(default=3600, gt=0)


class SwarmMessageResponse(BaseModel):
    """Swarm message response."""
    id: UUID
    swarm_id: UUID
    sender_agent_id: UUID
    recipient_agent_id: Optional[UUID]
    channel: str
    message_type: str
    content: str
    priority: int
    ttl_seconds: Optional[int]
    delivered: bool
    created_at: datetime


class SwarmEventQuery(BaseModel):
    """Query swarm events."""
    event_type: Optional[str] = None
    since: Optional[datetime] = None


class SwarmEventResponse(BaseModel):
    """Swarm event response."""
    id: UUID
    swarm_id: UUID
    event_type: str
    event_data: dict
    source_agent_id: UUID
    is_global: bool
    occurred_at: datetime
    created_at: datetime
