# NEXUS Agent Framework - Practical Examples

## Real-World Use Cases for Philip

### Example 1: Personal Finance Assistant

**Goal**: Create an agent that helps Philip track expenses, manage budget, and monitor debt repayment.

```python
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from app.agents.base import DomainAgent, AgentType
from app.agents.registry import registry
from app.agents.sessions import session_manager, SessionType
from app.agents.memory import memory_system, MemoryType

class PersonalFinanceAgent(DomainAgent):
    """Philip's personal finance assistant."""

    def __init__(self):
        super().__init__(
            name="Philip's Finance Assistant",
            agent_type=AgentType.DOMAIN,
            domain="personal_finance",
            description="Helps Philip track expenses, manage budget, and monitor debt",
            capabilities=[
                "expense_tracking",
                "budget_analysis",
                "debt_monitoring",
                "financial_advice",
                "savings_planning"
            ],
            system_prompt="""You are Philip's personal finance assistant. Philip is a night shift janitor
            with $9,700 debt to his mom. He's learning programming while building NEXUS.
            Be supportive, practical, and help him make progress on his financial goals."""
        )

    async def _on_initialize(self):
        """Initialize finance-specific tools."""
        await self.register_tool("log_expense", self._log_expense)
        await self.register_tool("check_budget", self._check_budget)
        await self.register_tool("update_debt_progress", self._update_debt_progress)
        await self.register_tool("analyze_spending_patterns", self._analyze_spending_patterns)

        # Load Philip's financial context
        await self._load_financial_context()

    async def _load_financial_context(self):
        """Load Philip's financial information from memory."""
        # Store Philip's financial goals
        await memory_system.store_memory(
            agent_id=self.agent_id,
            content="Philip owes $9,700 to his mom. Goal: Pay off debt while learning programming.",
            memory_type=MemoryType.SEMANTIC,
            importance_score=0.9,
            tags=["debt", "goal", "financial"],
            metadata={"priority": "high", "type": "financial_goal"}
        )

        # Store budget information
        await memory_system.store_memory(
            agent_id=self.agent_id,
            content="Philip's monthly budget: $1,200 income, $800 expenses target, $400 debt repayment.",
            memory_type=MemoryType.SEMANTIC,
            importance_score=0.8,
            tags=["budget", "income", "expenses"],
            metadata={"source": "estimated", "currency": "USD"}
        )

    async def _log_expense(self, amount: float, category: str, description: str = "") -> Dict[str, Any]:
        """Log an expense and update budget tracking."""
        from ..database import db

        # Log to database
        expense_id = await db.execute(
            """
            INSERT INTO expenses (amount, category, description, logged_by_agent)
            VALUES ($1, $2, $3, $4) RETURNING id
            """,
            amount, category, description, self.agent_id
        )

        # Store in memory
        await memory_system.store_memory(
            agent_id=self.agent_id,
            content=f"Expense logged: ${amount} for {category} - {description}",
            memory_type=MemoryType.EPISODIC,
            importance_score=0.6,
            tags=["expense", category.lower(), "logged"],
            metadata={
                "amount": amount,
                "category": category,
                "description": description,
                "timestamp": datetime.now().isoformat()
            }
        )

        # Check if this affects budget
        await self._check_budget_impact(amount, category)

        return {
            "success": True,
            "expense_id": expense_id,
            "message": f"Logged ${amount} expense for {category}"
        }

    async def _check_budget(self, month: str = None) -> Dict[str, Any]:
        """Check current budget status."""
        from ..database import db

        if not month:
            month = datetime.now().strftime("%Y-%m")

        # Get expenses for month
        expenses = await db.fetch_all(
            """
            SELECT SUM(amount) as total, category
            FROM expenses
            WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', $1::timestamp)
            GROUP BY category
            """,
            f"{month}-01"
        )

        total_expenses = sum(row["total"] or 0 for row in expenses)
        budget_status = {
            "month": month,
            "total_expenses": total_expenses,
            "budget_target": 800,  # Philip's target
            "remaining_budget": 800 - total_expenses,
            "over_budget": total_expenses > 800,
            "by_category": {row["category"]: row["total"] for row in expenses}
        }

        # Store budget check in memory
        await memory_system.store_memory(
            agent_id=self.agent_id,
            content=f"Budget check for {month}: Total ${total_expenses}, {'over' if total_expenses > 800 else 'under'} budget",
            memory_type=MemoryType.SEMANTIC,
            importance_score=0.7,
            tags=["budget", "check", month],
            metadata=budget_status
        )

        return budget_status

    async def _update_debt_progress(self, payment_amount: float) -> Dict[str, Any]:
        """Update debt repayment progress."""
        from ..database import db

        # Get current debt
        debt_record = await db.fetch_one(
            "SELECT remaining_amount FROM fin_debts WHERE description LIKE '%mom%' ORDER BY created_at DESC LIMIT 1"
        )

        if not debt_record:
            current_debt = 9700
        else:
            current_debt = debt_record["remaining_amount"] or 9700

        new_debt = max(0, current_debt - payment_amount)

        # Update debt record
        await db.execute(
            """
            INSERT INTO fin_debts (description, original_amount, remaining_amount, priority)
            VALUES ($1, $2, $3, 'high')
            """,
            "Debt to mom - updated by finance agent",
            9700,
            new_debt
        )

        progress = {
            "previous_debt": current_debt,
            "payment": payment_amount,
            "new_debt": new_debt,
            "percent_paid": ((9700 - new_debt) / 9700) * 100,
            "message": f"Great progress! Debt reduced to ${new_debt:,.2f}"
        }

        # Store progress in memory
        await memory_system.store_memory(
            agent_id=self.agent_id,
            content=f"Debt payment: ${payment_amount}. New total: ${new_debt}. {progress['percent_paid']:.1f}% paid.",
            memory_type=MemoryType.EPISODIC,
            importance_score=0.9,
            tags=["debt", "payment", "progress"],
            metadata=progress
        )

        return progress

    async def _analyze_spending_patterns(self, timeframe_days: int = 30) -> Dict[str, Any]:
        """Analyze spending patterns for insights."""
        from ..database import db

        analysis = await db.fetch_all(
            """
            SELECT
                category,
                COUNT(*) as transaction_count,
                SUM(amount) as total_spent,
                AVG(amount) as avg_transaction,
                MIN(created_at) as first_transaction,
                MAX(created_at) as last_transaction
            FROM expenses
            WHERE created_at >= NOW() - INTERVAL '1 day' * $1
            GROUP BY category
            ORDER BY total_spent DESC
            """,
            timeframe_days
        )

        insights = []
        total_spent = sum(row["total_spent"] or 0 for row in analysis)

        for row in analysis:
            percent = (row["total_spent"] / total_spent * 100) if total_spent > 0 else 0
            insights.append({
                "category": row["category"],
                "total_spent": row["total_spent"],
                "percent_of_total": percent,
                "transaction_count": row["transaction_count"],
                "avg_transaction": row["avg_transaction"],
                "suggestion": self._get_spending_suggestion(row["category"], percent, row["total_spent"])
            })

        return {
            "timeframe_days": timeframe_days,
            "total_spent": total_spent,
            "insights": insights,
            "recommendations": self._generate_recommendations(insights)
        }

    def _get_spending_suggestion(self, category: str, percent: float, total: float) -> str:
        """Generate spending suggestions based on category."""
        suggestions = {
            "food": "Consider meal planning to reduce food costs",
            "entertainment": "Look for free entertainment options",
            "transportation": "Can you carpool or use public transit?",
            "shopping": "Implement 24-hour rule for non-essential purchases"
        }

        if percent > 30 and total > 100:
            return f"High spending in {category}. {suggestions.get(category, 'Consider reducing this category.')}"

        return f"Spending in {category} looks reasonable"

    def _generate_recommendations(self, insights: List[Dict]) -> List[str]:
        """Generate personalized recommendations."""
        recommendations = []

        # Check for high spending categories
        high_spending = [i for i in insights if i["percent_of_total"] > 25]
        if high_spending:
            categories = ", ".join([i["category"] for i in high_spending])
            recommendations.append(f"Focus on reducing spending in: {categories}")

        # Check for many small transactions
        many_transactions = [i for i in insights if i["transaction_count"] > 10]
        if many_transactions:
            categories = ", ".join([i["category"] for i in many_transactions])
            recommendations.append(f"Consider consolidating frequent small purchases in: {categories}")

        # General recommendations
        recommendations.append("Set aside $50-100 each month for learning resources")
        recommendations.append("Track every expense for 30 days to identify patterns")
        recommendations.append("Celebrate small debt repayment milestones")

        return recommendations

    async def _check_budget_impact(self, amount: float, category: str):
        """Check if expense impacts budget significantly."""
        budget = await self._check_budget()

        if budget["over_budget"]:
            # Store warning in memory
            await memory_system.store_memory(
                agent_id=self.agent_id,
                content=f"Budget warning: Over budget this month after ${amount} {category} expense",
                memory_type=MemoryType.WORKING,
                importance_score=0.8,
                tags=["budget_warning", "alert"],
                metadata={"amount": amount, "category": category, "budget_status": budget}
            )

# Create and use the finance agent
async def setup_finance_agent():
    """Set up Philip's personal finance agent."""
    agent = PersonalFinanceAgent()
    await agent.initialize()

    # Register with registry
    await registry._register_agent(agent)

    print(f"Finance agent created: {agent.name}")
    return agent

# Example usage
async def daily_finance_check():
    """Daily finance check routine."""
    agent = await setup_finance_agent()

    # Create daily check session
    session_id = await session_manager.create_session(
        title="Daily Finance Check",
        session_type=SessionType.ANALYSIS,
        primary_agent_id=agent.agent_id
    )

    # Run budget check
    budget_result = await agent.execute(
        task="Check today's budget status and provide update",
        session_id=session_id
    )

    # Analyze spending patterns
    analysis_result = await agent.execute(
        task="Analyze spending patterns from last 7 days",
        session_id=session_id,
        context={"timeframe": "7 days"}
    )

    # Generate daily report
    report_result = await agent.execute(
        task="Generate daily finance report with recommendations",
        session_id=session_id,
        context={
            "budget": budget_result,
            "analysis": analysis_result,
            "focus": "debt_reduction"
        }
    )

    # Store report in memory
    if report_result.get("success"):
        await memory_system.store_memory(
            agent_id=agent.agent_id,
            content=f"Daily finance report: {report_result['result'].get('response', '')}",
            memory_type=MemoryType.EPISODIC,
            importance_score=0.7,
            tags=["daily_report", "finance", datetime.now().strftime("%Y-%m-%d")],
            metadata={
                "session_id": session_id,
                "budget_status": budget_result.get("result", {}),
                "analysis": analysis_result.get("result", {})
            }
        )

    await session_manager.end_session(session_id)
    return report_result
```

### Example 2: Learning Progress Tracker

**Goal**: Create an agent that helps Philip track programming learning progress.

```python
class LearningTrackerAgent(DomainAgent):
    """Tracks Philip's programming learning progress."""

    def __init__(self):
        super().__init__(
            name="Learning Progress Tracker",
            agent_type=AgentType.DOMAIN,
            domain="education",
            description="Tracks Philip's programming learning journey and progress",
            capabilities=[
                "progress_tracking",
                "skill_assessment",
                "resource_recommendation",
                "motivation",
                "goal_setting"
            ],
            system_prompt="""You are Philip's learning companion. Philip is learning programming
            while working night shifts and building NEXUS. Be encouraging, practical,
            and help him make consistent progress."""
        )

    async def _on_initialize(self):
        """Initialize learning tracking tools."""
        await self.register_tool("log_study_session", self._log_study_session)
        await self.register_tool("assess_current_skills", self._assess_current_skills)
        await self.register_tool("recommend_resources", self._recommend_resources)
        await self.register_tool("set_learning_goal", self._set_learning_goal)

        # Load Philip's learning context
        await self._load_learning_context()

    async def _load_learning_context(self):
        """Load Philip's learning information."""
        await memory_system.store_memory(
            agent_id=self.agent_id,
            content="Philip is learning Python, FastAPI, PostgreSQL, and Docker while building NEXUS.",
            memory_type=MemoryType.SEMANTIC,
            importance_score=0.9,
            tags=["learning", "programming", "skills"],
            metadata={
                "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "async/await"],
                "current_focus": "NEXUS development",
                "learning_style": "project_based"
            }
        )

    async def _log_study_session(self,
                                duration_minutes: int,
                                topic: str,
                                resources_used: List[str] = None,
                                accomplishments: str = "") -> Dict[str, Any]:
        """Log a study session."""
        from ..database import db

        session_id = await db.execute(
            """
            INSERT INTO learning_sessions (duration_minutes, topic, resources_used, accomplishments)
            VALUES ($1, $2, $3, $4) RETURNING id
            """,
            duration_minutes, topic, resources_used or [], accomplishments
        )

        # Calculate total study time
        total_time = await db.fetch_one(
            "SELECT SUM(duration_minutes) as total FROM learning_sessions WHERE topic = $1",
            topic
        )

        result = {
            "session_id": session_id,
            "duration_minutes": duration_minutes,
            "topic": topic,
            "total_study_time_minutes": total_time["total"] or 0,
            "total_study_time_hours": (total_time["total"] or 0) / 60,
            "message": f"Logged {duration_minutes}min study session on {topic}"
        }

        # Store in memory
        await memory_system.store_memory(
            agent_id=self.agent_id,
            content=f"Study session: {duration_minutes}min on {topic}. {accomplishments}",
            memory_type=MemoryType.EPISODIC,
            importance_score=0.7,
            tags=["study", "learning", topic.lower().replace(" ", "_")],
            metadata=result
        )

        return result

    async def _assess_current_skills(self) -> Dict[str, Any]:
        """Assess current programming skill levels."""
        # This would integrate with Philip's actual progress
        # For now, return structured assessment

        assessment = {
            "python": {
                "level": "intermediate",
                "confidence": 0.7,
                "projects": ["NEXUS backend", "API endpoints", "async programming"],
                "next_steps": ["Advanced async patterns", "Testing", "Performance optimization"]
            },
            "fastapi": {
                "level": "intermediate",
                "confidence": 0.6,
                "projects": ["NEXUS API", "Agent framework", "Database integration"],
                "next_steps": ["WebSockets", "Advanced middleware", "Background tasks"]
            },
            "postgresql": {
                "level": "beginner",
                "confidence": 0.5,
                "projects": ["NEXUS database schema", "Agent tables", "Performance monitoring"],
                "next_steps": ["Query optimization", "Indexing", "Advanced SQL features"]
            },
            "docker": {
                "level": "beginner",
                "confidence": 0.4,
                "projects": ["NEXUS containers", "Service orchestration"],
                "next_steps": ["Docker Compose advanced features", "Container optimization", "Networking"]
            }
        }

        # Store assessment in memory
        await memory_system.store_memory(
            agent_id=self.agent_id,
            content="Current skill assessment completed",
            memory_type=MemoryType.SEMANTIC,
            importance_score=0.8,
            tags=["skill_assessment", "progress"],
            metadata=assessment
        )

        return assessment

    async def _recommend_resources(self,
                                  skill: str = None,
                                  level: str = "intermediate") -> Dict[str, Any]:
        """Recommend learning resources based on skill and level."""
        resources = {
            "python": {
                "beginner": [
                    "Python Crash Course book",
                    "freeCodeCamp Python tutorial",
                    "Automate the Boring Stuff with Python"
                ],
                "intermediate": [
                    "Fluent Python book",
                    "Real Python tutorials",
                    "Python async/await documentation"
                ],
                "advanced": [
                    "Advanced Python Mastery course",
                    "CPython internals documentation",
                    "Python performance optimization guides"
                ]
            },
            "fastapi": {
                "beginner": [
                    "FastAPI official tutorial",
                    "TestDriven.io FastAPI course",
                    "FastAPI documentation"
                ],
                "intermediate": [
                    "FastAPI advanced features guide",
                    "Async database patterns",
                    "API security best practices"
                ]
            },
            "postgresql": {
                "beginner": [
                    "PostgreSQL tutorial",
                    "PostgreSQL Exercises website",
                    "Use The Index, Luke guide"
                ]
            }
        }

        if skill and skill in resources:
            recommendations = resources[skill].get(level, [])
        else:
            # General recommendations
            recommendations = [
                "Philip's current focus: Complete NEXUS agent framework",
                "Practice: Build small projects with each new concept",
                "Community: Join Python Discord for help and motivation"
            ]

        return {
            "skill": skill or "general",
            "level": level,
            "recommendations": recommendations,
            "note": "Focus on practical application within NEXUS project"
        }

    async def _set_learning_goal(self,
                                goal: str,
                                timeframe: str,
                                milestones: List[str] = None) -> Dict[str, Any]:
        """Set a learning goal with milestones."""
        from ..database import db

        goal_id = await db.execute(
            """
            INSERT INTO learning_goals (goal, timeframe, milestones, status)
            VALUES ($1, $2, $3, 'active') RETURNING id
            """,
            goal, timeframe, milestones or []
        )

        result = {
            "goal_id": goal_id,
            "goal": goal,
            "timeframe": timeframe,
            "milestones": milestones,
            "status": "active",
            "created_at": datetime.now().isoformat()
        }

        # Store goal in memory
        await memory_system.store_memory(
            agent_id=self.agent_id,
            content=f"Learning goal set: {goal} ({timeframe})",
            memory_type=MemoryType.SEMANTIC,
            importance_score=0.9,
            tags=["learning_goal", "planning"],
            metadata=result
        )

        return result

# Weekly learning review
async def weekly_learning_review():
    """Weekly learning progress review."""
    agent = LearningTrackerAgent()
    await agent.initialize()

    session_id = await session_manager.create_session(
        title="Weekly Learning Review",
        session_type=SessionType.ANALYSIS,
        primary_agent_id=agent.agent_id
    )

    # Assess progress
    assessment = await agent.execute(
        task="Assess this week's learning progress and skill development",
        session_id=session_id
    )

    # Get recommendations
    recommendations = await agent.execute(
        task="Provide learning recommendations for next week based on progress",
        session_id=session_id,
        context={"assessment": assessment}
    )

    # Set goals for next week
    goals = await agent.execute(
        task="Set specific, achievable learning goals for next week",
        session_id=session_id,
        context={
            "current_progress": assessment,
            "recommendations": recommendations,
            "available_time": "10-15 hours (night shifts schedule)"
        }
    )

    # Store weekly review
    if goals.get("success"):
        await memory_system.store_memory(
            agent_id=agent.agent_id,
            content=f"Weekly learning review completed. Goals set for next week.",
            memory_type=MemoryType.EPISODIC,
            importance_score=0.8,
            tags=["weekly_review", "learning", "planning"],
            metadata={
                "session_id": session_id,
                "assessment": assessment.get("result", {}),
                "goals": goals.get("result", {})
            }
        )

    await session_manager.end_session(session_id)
    return goals
```

### Example 3: NEXUS Development Assistant

**Goal**: Create an agent that helps Philip with NEXUS development tasks.

```python
class NexusDevelopmentAgent(DomainAgent):
    """Assists with NEXUS development tasks."""

    def __init__(self):
        super().__init__(
            name="NEXUS Development Assistant",
            agent_type=AgentType.DOMAIN,
            domain="nexus_development",
            description="Helps Philip with NEXUS AI Operating System development",
            capabilities=[
                "code_review",
                "architecture_advice",
                "bug_diagnosis",
                "feature_planning",
                "documentation"
            ],
            system_prompt="""You are Philip's NEXUS development assistant. NEXUS is Philip's
            AI operating system - his second brain and everything to him. Help him build
            robust, maintainable code while learning best practices."""
        )

    async def _on_initialize(self):
        """Initialize development tools."""
        await self.register_tool("review_code_changes", self._review_code_changes)
        await self.register_tool("suggest_architecture", self._suggest_architecture)
        await self.register_tool("diagnose_bug", self._diagnose_bug)
        await self.register_tool("plan_feature", self._plan_feature)

        # Load NEXUS project context
        await self._load_nexus_context()

    async def _load_nexus_context(self):
        """Load NEXUS project information."""
        await memory_system.store_memory(
            agent_id=self.agent_id,
            content="""NEXUS is Philip's AI operating system built with Python 3.12 + FastAPI,
            PostgreSQL 16, ChromaDB, Redis, and Docker Compose (8 services).
            Key features: Multi-agent orchestration, Privacy Shield, Cost cascade routing,
            Semantic caching (60-70% cost reduction).""",
            memory_type=MemoryType.SEMANTIC,
            importance_score=1.0,
            tags=["nexus", "project", "architecture"],
            metadata={
                "tech_stack": ["Python 3.12", "FastAPI", "PostgreSQL 16", "ChromaDB", "Redis", "Docker"],
                "current_phase": "Phase 5 - Multi-agent framework implementation",
                "key_features": ["Multi-agent orchestration", "Semantic caching", "Cost optimization"]
            }
        )

    async def _review_code_changes(self,
                                  file_path: str,
                                  changes: str,
                                  context: str = "") -> Dict[str, Any]:
        """Review code changes for best practices."""
        # This would integrate with actual code review
        # For now, provide template response

        review = {
            "file": file_path,
            "changes_reviewed": True,
            "suggestions": [
                "Add type hints for all function parameters",
                "Include docstrings for public functions",
                "Consider error handling for edge cases",
                "Follow existing NEXUS code conventions"
            ],
            "best_practices": [
                "Use async/await for I/O operations",
                "Log operations with context",
                "Validate inputs with Pydantic",
                "Handle database connection errors gracefully"
            ],
            "nexus_specific": [
                "Use app.database.db connection pool",
                "Log AI usage to api_usage table",
                "Implement semantic caching where applicable",
                "Follow agent framework patterns if relevant"
            ]
        }

        return review

    async def _suggest_architecture(self,
                                   feature: str,
                                   requirements: List[str]) -> Dict[str, Any]:
        """Suggest architecture for a new feature."""
        suggestions = {
            "database": {
                "tables_needed": [],
                "indexes_suggested": [],
                "relationships": []
            },
            "api": {
                "endpoints": [],
                "request_models": [],
                "response_models": []
            },
            "agents": {
                "agent_types": [],
                "tools_needed": [],
                "integration_points": []
            },
            "considerations": [
                "Cost optimization through semantic caching",
                "Privacy Shield compliance",
                "Integration with existing services",
                "Philip's learning progression"
            ]
        }

        # Customize based on feature
        if "agent" in feature.lower():
            suggestions["agents"]["agent_types"].append("DomainAgent or specialized agent")
            suggestions["agents"]["tools_needed"].append("Task-specific tools")
            suggestions["agents"]["integration_points"].append("Agent registry, memory system")

        if "api" in feature.lower():
            suggestions["api"]["endpoints"].append(f"POST /{feature.replace(' ', '-')}")
            suggestions["api"]["endpoints"].append(f"GET /{feature.replace(' ', '-')}/{{id}}")

        return {
            "feature": feature,
            "architecture_suggestions": suggestions,
            "implementation_priority": "medium",
            "estimated_complexity": "moderate",
            "learning_opportunities": ["Async patterns", "Database design", "API structure"]
        }

    async def _diagnose_bug(self,
                           error_message: str,
                           context: Dict[str, Any]) -> Dict[str, Any]:
        """Help diagnose bugs in NEXUS."""
        common_issues = {
            "database": [
                "Check database connection pool",
                "Verify table schemas match code",
                "Check for JSONB decoding issues",
                "Verify asyncpg connection handling"
            ],
            "agents": [
                "Check agent registry initialization",
                "Verify agent capabilities match requirements",
                "Check memory system integration",
                "Verify session management"
            ],
            "api": [
                "Check FastAPI dependency injection",
                "Verify Pydantic model validation",
                "Check async/await pattern consistency",
                "Verify error handling middleware"
            ]
        }

        diagnosis = {
            "error_message": error_message,
            "likely_causes": [],
            "debugging_steps": [
                "Check application logs: journalctl -u nexus-api -f",
                "Test API endpoint directly",
                "Verify database connectivity",
                "Check Redis connection"
            ],
            "quick_fixes": [
                "Restart nexus-api service: sudo systemctl restart nexus-api",
                "Check .env configuration",
                "Verify Docker containers are running"
            ]
        }

        # Add specific suggestions based on error
        if "database" in error_message.lower() or "postgres" in error_message.lower():
            diagnosis["likely_causes"].extend(common_issues["database"])
        elif "agent" in error_message.lower():
            diagnosis["likely_causes"].extend(common_issues["agents"])
        elif "api" in error_message.lower() or "http" in error_message.lower():
            diagnosis["likely_causes"].extend(common_issues["api"])

        return diagnosis

    async def _plan_feature(self,
                           feature_name: str,
                           description: str,
                           priority: str = "medium") -> Dict[str, Any]:
        """Plan implementation of a new feature."""
        plan = {
            "feature": feature_name,
            "description": description,
            "priority": priority,
            "phases": [
                {
                    "phase": "Design",
                    "tasks": [
                        "Define requirements and scope",
                        "Design database schema",
                        "Plan API endpoints",
                        "Design agent integration if needed"
                    ],
                    "estimated_time": "2-4 hours"
                },
                {
                    "phase": "Implementation",
                    "tasks": [
                        "Create database migrations",
                        "Implement core logic",
                        "Add API endpoints",
                        "Write tests"
                    ],
                    "estimated_time": "4-8 hours"
                },
                {
                    "phase": "Integration",
                    "tasks": [
                        "Integrate with existing services",
                        "Add monitoring and logging",
                        "Update documentation",
                        "Test end-to-end"
                    ],
                    "estimated_time": "2-4 hours"
                }
            ],
            "dependencies": [
                "Running NEXUS services",
                "Existing agent framework",
                "Database schema understanding"
            ],
            "learning_focus": [
                "Practical application of concepts",
                "Following NEXUS conventions",
                "Async Python patterns",
                "Error handling and robustness"
            ]
        }

        return plan

# Development session helper
async def development_session_helper(task: str, context: Dict[str, Any]):
    """Helper for development sessions."""
    agent = NexusDevelopmentAgent()
    await agent.initialize()

    session_id = await session_manager.create_session(
        title=f"Development: {task}",
        session_type=SessionType.COLLABORATION,
        primary_agent_id=agent.agent_id
    )

    # Get help based on task
    if "bug" in task.lower() or "error" in task.lower():
        result = await agent.execute(
            task=f"Help diagnose and fix: {task}",
            session_id=session_id,
            context=context
        )
    elif "implement" in task.lower() or "build" in task.lower():
        result = await agent.execute(
            task=f"Help plan implementation: {task}",
            session_id=session_id,
            context=context
        )
    else:
        result = await agent.execute(
            task=task,
            session_id=session_id,
            context=context
        )

    # Store development session
    if result.get("success"):
        await memory_system.store_memory(
            agent_id=agent.agent_id,
            content=f"Development session: {task}",
            memory_type=MemoryType.EPISODIC,
            importance_score=0.8,
            tags=["development", "session", task.lower().replace(" ", "_")],
            metadata={
                "session_id": session_id,
                "task": task,
                "result": result.get("result", {})
            }
        )

    await session_manager.end_session(session_id)
    return result
```

## Integration Examples

### Integrating All Agents
```python
async def integrated_daily_routine():
    """Philip's integrated daily routine with all agents."""

    # Initialize all agents
    finance_agent = PersonalFinanceAgent()
    learning_agent = LearningTrackerAgent()
    dev_agent = NexusDevelopmentAgent()

    for agent in [finance_agent, learning_agent, dev_agent]:
        await agent.initialize()
        await registry._register_agent(agent)

    # Morning routine
    morning_session = await session_manager.create_session(
        title="Morning Routine",
        session_type=SessionType.COLLABORATION
    )

    # Add all agents to session
    for agent in [finance_agent, learning_agent, dev_agent]:
        await session_manager.add_agent_to_session(morning_session, agent.agent_id)

    # Parallel tasks
    tasks = [
        finance_agent.execute(
            "Check daily budget and expenses",
            session_id=morning_session,
            context={"time": "morning"}
        ),
        learning_agent.execute(
            "Plan today's learning session",
            session_id=morning_session,
            context={"available_time": "2 hours before work"}
        ),
        dev_agent.execute(
            "Review today's NEXUS development priorities",
            session_id=morning_session,
            context={"focus": "agent framework improvements"}
        )
    ]

    results = await asyncio.gather(*tasks)

    # Generate integrated summary
    summary = {
        "finance": results[0].get("result", {}),
        "learning": results[1].get("result", {}),
        "development": results[2].get("result", {})
    }

    # Store integrated summary
    await memory_system.store_memory(
        agent_id=finance_agent.agent_id,  # Use finance agent as primary
        content="Daily integrated routine completed",
        memory_type=MemoryType.EPISODIC,
        importance_score=0.9,
        tags=["daily_routine", "integrated", "morning"],
        metadata=summary
    )

    await session_manager.end_session(morning_session)
    return summary
```

## Usage Tips for Philip

1. **Start Simple**: Begin with one agent (Finance Assistant) and expand gradually
2. **Regular Sessions**: Schedule daily/weekly sessions with each agent
3. **Integration**: Connect agents to share context (e.g., finance status affects learning budget)
4. **Feedback Loop**: Provide feedback to agents to improve their assistance
5. **Documentation**: Keep notes on what works well for your learning style

## Next Steps

1. **Implement Finance Agent**: Start with the PersonalFinanceAgent example
2. **Create Database Tables**: Add necessary tables for expenses, learning sessions, etc.
3. **Test Integration**: Ensure agents work with existing NEXUS services
4. **Add UI**: Create simple web interface for agent interactions
5. **Schedule Automation**: Set up automated daily/weekly agent sessions

These practical examples provide a foundation for building agents that directly help Philip with his specific goals: paying off debt, learning programming, and building NEXUS.