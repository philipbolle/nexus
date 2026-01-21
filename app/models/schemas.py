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
