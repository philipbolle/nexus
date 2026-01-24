"""
NEXUS Finance Agent
Financial tracking, budget analysis, debt progress monitoring.

Integrates with existing finance endpoints and provides intelligent
financial analysis and recommendations.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal

from ..database import db
from ..config import settings
from ..services.ai_providers import ai_request, TaskType

# Import agent framework
from .base import BaseAgent, AgentType, AgentStatus
from .tools import ToolSystem, ToolDefinition, ToolParameter

logger = logging.getLogger(__name__)


class FinanceAgent(BaseAgent):
    """
    Finance Agent - Financial tracking and analysis agent.

    Capabilities: expense_tracking, budget_analysis, debt_monitoring,
                  financial_insights, recommendation_generation.
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        name: str = "Finance Agent",
        description: str = "Tracks expenses, monitors budgets, analyzes debt progress, and provides financial insights.",
        system_prompt: str = "",
        capabilities: Optional[List[str]] = None,
        supervisor_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        if capabilities is None:
            capabilities = [
                "expense_tracking",
                "budget_analysis",
                "debt_monitoring",
                "financial_insights",
                "recommendation_generation"
            ]

        if config is None:
            config = {
                "domain": "finance",
                "default_days_analysis": 30,
                "budget_alert_threshold": 0.9,  # 90% of budget spent
                "debt_progress_update_frequency_days": 7
            }

        # Extract domain from kwargs if provided (used by registry)
        domain = kwargs.pop("domain", None)
        if domain:
            config["domain"] = domain
        else:
            domain = "finance"  # Default domain for finance agent

        # Merge any config provided in kwargs
        kwargs_config = kwargs.pop("config", None)
        if kwargs_config:
            config.update(kwargs_config)

        # Remove agent_type from kwargs (we set it explicitly)
        kwargs.pop("agent_type", None)

        # Pass remaining kwargs to super (should be empty after processing)
        super().__init__(
            agent_id=agent_id,
            name=name,
            agent_type=AgentType.DOMAIN,
            description=description,
            system_prompt=system_prompt,
            capabilities=capabilities,
            domain=domain,
            supervisor_id=supervisor_id,
            config=config,
            **kwargs
        )

    async def _on_initialize(self) -> None:
        """Initialize finance-specific resources and register tools."""
        logger.info(f"Initializing Finance Agent: {self.name}")

        # Register finance-specific tools
        await self._register_finance_tools()

        # Load any finance-specific configuration
        await self._load_finance_config()

    async def _on_cleanup(self) -> None:
        """Clean up finance agent resources."""
        logger.info(f"Cleaning up Finance Agent: {self.name}")
        # Nothing specific to clean up

    async def _process_task(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process finance-related tasks.

        Supported task types:
        - log_expense: Log a new expense
        - get_budget_status: Get current budget status
        - get_debt_progress: Get debt payoff progress
        - analyze_spending: Analyze spending patterns
        - generate_recommendations: Generate financial recommendations
        - forecast_budget: Forecast budget for upcoming period
        """
        task_type = task.get("type", "unknown")

        try:
            if task_type == "log_expense":
                return await self._log_expense(task, context)
            elif task_type == "get_budget_status":
                return await self._get_budget_status(task, context)
            elif task_type == "get_debt_progress":
                return await self._get_debt_progress(task, context)
            elif task_type == "analyze_spending":
                return await self._analyze_spending(task, context)
            elif task_type == "generate_recommendations":
                return await self._generate_recommendations(task, context)
            elif task_type == "forecast_budget":
                return await self._forecast_budget(task, context)
            else:
                return {
                    "success": False,
                    "error": f"Unknown task type: {task_type}",
                    "supported_types": [
                        "log_expense", "get_budget_status", "get_debt_progress",
                        "analyze_spending", "generate_recommendations", "forecast_budget"
                    ]
                }

        except Exception as e:
            logger.error(f"Task processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "task_type": task_type
            }

    async def _register_finance_tools(self) -> None:
        """Register finance-specific tools."""
        # Tool: log_expense
        schema = {
            "name": "log_expense",
            "display_name": "Log Expense",
            "description": "Log a new expense transaction",
            "input_schema": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "Expense amount in dollars"},
                    "category": {"type": "string", "description": "Expense category"},
                    "merchant": {"type": "string", "description": "Merchant/store name"},
                    "description": {"type": "string", "description": "Description of the expense"},
                    "transaction_date": {"type": "string", "format": "date", "description": "Date of transaction (YYYY-MM-DD)"}
                },
                "required": ["amount", "category"]
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "transaction_id": {"type": "string"},
                    "amount": {"type": "number"},
                    "category": {"type": "string"},
                    "budget_remaining": {"type": "number"},
                    "message": {"type": "string"}
                }
            }
        }
        await self.register_tool("log_expense", self._tool_log_expense, schema)

        # Tool: get_budget_status
        schema = {
            "name": "get_budget_status",
            "display_name": "Get Budget Status",
            "description": "Get current month's budget status by category",
            "input_schema": {
                "type": "object",
                "properties": {
                    "month": {"type": "string", "description": "Month to analyze (YYYY-MM), defaults to current month"}
                },
                "required": []
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "month": {"type": "string"},
                    "total_budget": {"type": "number"},
                    "total_spent": {"type": "number"},
                    "remaining": {"type": "number"},
                    "percent_used": {"type": "number"},
                    "categories": {"type": "array"}
                }
            }
        }
        await self.register_tool("get_budget_status", self._tool_get_budget_status, schema)

        # Tool: get_debt_progress
        schema = {
            "name": "get_debt_progress",
            "display_name": "Get Debt Progress",
            "description": "Get debt payoff progress summary",
            "input_schema": {
                "type": "object",
                "properties": {
                    "include_inactive": {"type": "boolean", "description": "Include inactive debts"}
                },
                "required": []
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "total_original": {"type": "number"},
                    "total_current": {"type": "number"},
                    "total_paid": {"type": "number"},
                    "percent_paid": {"type": "number"},
                    "debts": {"type": "array"}
                }
            }
        }
        await self.register_tool("get_debt_progress", self._tool_get_debt_progress, schema)

        # Tool: analyze_spending
        schema = {
            "name": "analyze_spending",
            "display_name": "Analyze Spending",
            "description": "Analyze spending patterns over time",
            "input_schema": {
                "type": "object",
                "properties": {
                    "days": {"type": "number", "description": "Number of days to analyze, defaults to 30"},
                    "category": {"type": "string", "description": "Specific category to analyze"}
                },
                "required": []
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "period": {"type": "string"},
                    "total_spent": {"type": "number"},
                    "average_daily": {"type": "number"},
                    "by_category": {"type": "object"},
                    "trend": {"type": "string"},
                    "insights": {"type": "array"}
                }
            }
        }
        await self.register_tool("analyze_spending", self._tool_analyze_spending, schema)

        # Tool: generate_recommendations
        schema = {
            "name": "generate_recommendations",
            "display_name": "Generate Recommendations",
            "description": "Generate financial recommendations based on current status",
            "input_schema": {
                "type": "object",
                "properties": {
                    "focus_area": {"type": "string", "description": "Focus area (budget, debt, savings, general)"}
                },
                "required": []
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "focus_area": {"type": "string"},
                    "recommendations": {"type": "array"},
                    "priority": {"type": "string"}
                }
            }
        }
        await self.register_tool("generate_recommendations", self._tool_generate_recommendations, schema)

    async def _load_finance_config(self) -> None:
        """Load finance-specific configuration from database."""
        # Could load from database, but for now use defaults
        pass

    # ============ Task Processing Methods ============

    async def _log_expense(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Log a new expense transaction."""
        from ..routers.finance import log_expense

        expense_data = task.get("expense", {})

        # Prepare expense create schema
        class ExpenseCreate:
            def __init__(self, data):
                self.amount = data.get("amount")
                self.category = data.get("category", "Uncategorized")
                self.merchant = data.get("merchant", "")
                self.description = data.get("description", "")
                self.transaction_date = data.get("transaction_date")

        expense = ExpenseCreate(expense_data)

        try:
            # Use the existing finance router function
            result = await log_expense(expense, db)

            return {
                "success": True,
                "transaction_id": str(result.id),
                "amount": result.amount,
                "category": result.category,
                "budget_remaining": result.budget_remaining,
                "message": result.message
            }

        except Exception as e:
            logger.error(f"Failed to log expense: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_budget_status(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get current month's budget status."""
        from ..routers.finance import get_budget_status

        try:
            # Use the existing finance router function
            result = await get_budget_status(db)

            # Convert Decimal to float for JSON serialization
            return {
                "success": True,
                "month": result.month,
                "total_budget": float(result.total_budget),
                "total_spent": float(result.total_spent),
                "remaining": float(result.remaining),
                "percent_used": result.percent_used,
                "categories": result.categories
            }

        except Exception as e:
            logger.error(f"Failed to get budget status: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_debt_progress(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get debt payoff progress."""
        from ..routers.finance import get_debt_progress

        try:
            # Use the existing finance router function
            result = await get_debt_progress(db)

            # Convert Decimal to float for JSON serialization
            return {
                "success": True,
                "total_original": float(result.total_original),
                "total_current": float(result.total_current),
                "total_paid": float(result.total_paid),
                "percent_paid": result.percent_paid,
                "debts": result.debts
            }

        except Exception as e:
            logger.error(f"Failed to get debt progress: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _analyze_spending(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze spending patterns."""
        days = task.get("days", self.config.get("default_days_analysis", 30))
        category = task.get("category")

        try:
            # Calculate date range
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            # Build query
            query_params = [start_date, end_date]
            category_filter = ""
            if category:
                category_filter = "AND c.name = $3"
                query_params.append(category)

            # Get spending data
            spending = await db.fetch_all(f"""
                SELECT
                    c.name as category,
                    DATE_TRUNC('day', t.transaction_date) as day,
                    SUM(t.amount) as daily_spent
                FROM fin_transactions t
                JOIN fin_categories c ON t.category_id = c.id
                WHERE t.transaction_date BETWEEN $1 AND $2
                    AND t.transaction_type = 'expense'
                    {category_filter}
                GROUP BY c.name, DATE_TRUNC('day', t.transaction_date)
                ORDER BY day, category
            """, *query_params)

            # Calculate totals
            total_spent = sum(Decimal(str(row["daily_spent"])) for row in spending)
            avg_daily = total_spent / days if days > 0 else Decimal(0)

            # Group by category
            by_category = {}
            for row in spending:
                cat = row["category"]
                if cat not in by_category:
                    by_category[cat] = Decimal(0)
                by_category[cat] += Decimal(str(row["daily_spent"]))

            # Convert to float for response
            by_category_float = {cat: float(amount) for cat, amount in by_category.items()}

            # Simple trend analysis (comparing first half vs second half of period)
            midpoint = days // 2
            if spending and midpoint > 0:
                # This is simplified - in real implementation would compare spending periods
                trend = "stable"
            else:
                trend = "insufficient_data"

            # Generate AI insights if data exists
            insights = []
            if spending:
                insight_prompt = f"""
                Spending analysis for {days} days:
                Total: ${total_spent:.2f}
                Average daily: ${avg_daily:.2f}
                By category: {json.dumps(by_category_float)}

                Provide 2-3 actionable insights.
                """

                try:
                    insight_result = await ai_request(
                        prompt=insight_prompt,
                        task_type="analysis",
                        system="You are a financial advisor. Provide concise, actionable insights based on spending data."
                    )
                    insights = [insight.strip() for insight in insight_result["content"].split('\n') if insight.strip()]
                except Exception as e:
                    logger.warning(f"Failed to generate AI insights: {e}")
                    insights = ["Enable AI insights by checking API configuration"]

            return {
                "success": True,
                "period": f"{start_date} to {end_date}",
                "total_spent": float(total_spent),
                "average_daily": float(avg_daily),
                "by_category": by_category_float,
                "trend": trend,
                "insights": insights
            }

        except Exception as e:
            logger.error(f"Failed to analyze spending: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _generate_recommendations(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate financial recommendations."""
        focus_area = task.get("focus_area", "general")

        try:
            # Get current financial status
            budget_status = await self._get_budget_status({"type": "get_budget_status"}, None)
            debt_progress = await self._get_debt_progress({"type": "get_debt_progress"}, None)

            if not budget_status.get("success") or not debt_progress.get("success"):
                return {
                    "success": False,
                    "error": "Failed to get financial status data"
                }

            # Prepare data for AI analysis
            analysis_data = {
                "focus_area": focus_area,
                "budget_status": budget_status,
                "debt_progress": debt_progress,
                "current_date": datetime.now().isoformat()
            }

            # Generate recommendations using AI
            recommendation_prompt = f"""
            Financial analysis for {focus_area} focus:

            Budget Status:
            - Month: {budget_status.get('month', 'Unknown')}
            - Total spent: ${budget_status.get('total_spent', 0):.2f} / ${budget_status.get('total_budget', 0):.2f}
            - Percent used: {budget_status.get('percent_used', 0):.1f}%
            - Remaining: ${budget_status.get('remaining', 0):.2f}

            Debt Progress:
            - Total paid: ${debt_progress.get('total_paid', 0):.2f}
            - Current balance: ${debt_progress.get('total_current', 0):.2f}
            - Percent paid: {debt_progress.get('percent_paid', 0):.1f}%

            Generate 3-5 specific, actionable recommendations for {focus_area}.
            Focus on practical steps the user can take immediately.
            """

            recommendation_result = await ai_request(
                prompt=recommendation_prompt,
                task_type="analysis",
                system="You are a financial advisor. Provide specific, actionable recommendations tailored to the user's financial situation."
            )

            # Parse recommendations
            recommendations = []
            for line in recommendation_result["content"].split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Remove bullet points and numbering
                    clean_line = line.lstrip('•-*0123456789. )')
                    if clean_line:
                        recommendations.append(clean_line)

            # Determine priority based on focus area
            priority_map = {
                "debt": "high",
                "budget": "medium",
                "savings": "medium",
                "general": "low"
            }
            priority = priority_map.get(focus_area, "medium")

            return {
                "success": True,
                "focus_area": focus_area,
                "recommendations": recommendations[:5],  # Limit to 5
                "priority": priority,
                "ai_provider": recommendation_result["provider"]
            }

        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _forecast_budget(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Forecast budget for upcoming period."""
        days_ahead = task.get("days_ahead", 30)

        try:
            # Get recent spending patterns
            recent_spending = await self._analyze_spending(
                {"type": "analyze_spending", "days": min(90, days_ahead * 2)},
                None
            )

            if not recent_spending.get("success"):
                return recent_spending

            avg_daily = recent_spending.get("average_daily", 0)
            forecast_total = avg_daily * days_ahead

            # Get current budget status
            budget_status = await self._get_budget_status({"type": "get_budget_status"}, None)
            if not budget_status.get("success"):
                return budget_status

            remaining = budget_status.get("remaining", 0)
            days_remaining_in_month = 30 - datetime.now().day  # Simplified

            # Calculate projected status
            projected_remaining = remaining - forecast_total
            projected_percent_used = 100 if remaining <= 0 else ((remaining - projected_remaining) / remaining * 100)

            # Determine projection category
            if projected_remaining >= remaining * 0.5:
                projection = "on_track"
                message = f"Projected to stay within budget for next {days_ahead} days"
            elif projected_remaining > 0:
                projection = "at_risk"
                message = f"May exceed budget in next {days_ahead} days"
            else:
                projection = "exceeded"
                message = f"Will exceed budget in next {days_ahead} days"

            return {
                "success": True,
                "forecast_period_days": days_ahead,
                "average_daily_spending": avg_daily,
                "projected_total_spending": forecast_total,
                "current_budget_remaining": remaining,
                "projected_budget_remaining": max(0, projected_remaining),
                "projected_percent_used": projected_percent_used,
                "projection": projection,
                "message": message,
                "recommendation": "Consider adjusting spending if projection is 'at_risk' or 'exceeded'"
            }

        except Exception as e:
            logger.error(f"Failed to forecast budget: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # ============ Tool Implementation Methods ============

    async def _tool_log_expense(self, **kwargs) -> Dict[str, Any]:
        """Tool implementation for log_expense."""
        result = await self._log_expense(
            {"expense": kwargs},
            None
        )
        return result

    async def _tool_get_budget_status(self, **kwargs) -> Dict[str, Any]:
        """Tool implementation for get_budget_status."""
        result = await self._get_budget_status(
            {"type": "get_budget_status", **kwargs},
            None
        )
        return result

    async def _tool_get_debt_progress(self, **kwargs) -> Dict[str, Any]:
        """Tool implementation for get_debt_progress."""
        result = await self._get_debt_progress(
            {"type": "get_debt_progress", **kwargs},
            None
        )
        return result

    async def _tool_analyze_spending(self, **kwargs) -> Dict[str, Any]:
        """Tool implementation for analyze_spending."""
        result = await self._analyze_spending(
            {"type": "analyze_spending", **kwargs},
            None
        )
        return result

    async def _tool_generate_recommendations(self, **kwargs) -> Dict[str, Any]:
        """Tool implementation for generate_recommendations."""
        result = await self._generate_recommendations(
            {"type": "generate_recommendations", **kwargs},
            None
        )
        return result


# ============ Agent Registration Helper ============

async def register_finance_agent() -> FinanceAgent:
    """
    Register finance agent with the agent registry.

    Call this during system startup to register the finance agent.
    Returns existing agent if already registered.
    """
    from .registry import registry

    # Check if finance agent already exists by name
    existing_agent = await registry.get_agent_by_name("Finance Agent")
    if existing_agent:
        logger.info(f"Finance agent already registered: {existing_agent.name}")
        return existing_agent

    # Create new finance agent using registry's create_agent method
    # This ensures proper registration and database storage
    try:
        agent = await registry.create_agent(
            agent_type="finance",  # Finance is a registered agent type
            name="Finance Agent",
            description="Tracks expenses, monitors budgets, analyzes debt progress, and provides financial insights.",
            capabilities=[
                "expense_tracking",
                "budget_analysis",
                "debt_monitoring",
                "financial_insights",
                "recommendation_generation"
            ],
            domain="finance",
            config={
                "default_days_analysis": 30,
                "budget_alert_threshold": 0.9,
                "debt_progress_update_frequency_days": 7
            }
        )
        logger.info(f"Finance agent created and registered: {agent.name}")
        return agent
    except ValueError as e:
        # Likely duplicate name (race condition) - try to fetch again
        logger.warning(f"Duplicate agent creation attempt: {e}")
        existing_agent = await registry.get_agent_by_name("Finance Agent")
        if existing_agent:
            logger.info(f"Retrieved existing finance agent after duplicate error: {existing_agent.name}")
            return existing_agent
        raise