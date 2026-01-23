"""
NEXUS Decision Support System Agent
Helps with analysis paralysis and architectural decisions.

Provides decision analysis, pros/cons evaluation, risk assessment, and recommendation generation.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..database import db
from ..config import settings
from ..services.ai_providers import ai_request, TaskType

# Import agent framework
from .base import BaseAgent, AgentType, AgentStatus, DomainAgent
from .tools import ToolSystem, ToolDefinition, ToolParameter
from .memory import MemorySystem

logger = logging.getLogger(__name__)

# Decision analysis prompts
DECISION_ANALYSIS_SYSTEM = """You are a decision analysis expert. Analyze decision scenarios and provide structured analysis.

Guidelines:
1. Identify key decision factors and constraints
2. Evaluate pros and cons for each option
3. Assess risks and probabilities
4. Consider short-term and long-term implications
5. Provide actionable recommendations

Return structured JSON analysis."""

RISK_ASSESSMENT_SYSTEM = """You are a risk assessment specialist. Evaluate risks for decision options.

Consider:
1. Probability of occurrence (Low/Medium/High)
2. Impact severity (Low/Medium/High)
3. Mitigation strategies
4. Risk-reward tradeoffs

Return structured risk assessment."""


class DecisionSupportAgent(DomainAgent):
    """
    Decision Support System Agent - Helps with analysis paralysis and architectural decisions.

    Capabilities: decision_analysis, pros_cons_evaluation, risk_assessment,
                  architectural_review, tradeoff_analysis, recommendation_generation, memory_learning
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        name: str = "Decision Support Agent",
        description: str = "Helps with analysis paralysis and architectural decisions by providing structured analysis, risk assessment, and actionable recommendations.",
        system_prompt: str = "",
        capabilities: Optional[List[str]] = None,
        supervisor_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        if capabilities is None:
            capabilities = [
                "decision_analysis",
                "pros_cons_evaluation",
                "risk_assessment",
                "architectural_review",
                "tradeoff_analysis",
                "recommendation_generation",
                "memory_learning"
            ]

        if config is None:
            config = {
                "domain": "decision_support",
                "max_options_per_decision": 10,
                "default_analysis_depth": "comprehensive",
                "risk_threshold_high": 0.7,
                "risk_threshold_medium": 0.4,
                "enable_memory_learning": True
            }

        # Extract domain from kwargs if provided (used by registry)
        domain = kwargs.pop("domain", None)
        if domain:
            config["domain"] = domain
        else:
            domain = "decision_support"

        # Merge any config provided in kwargs
        kwargs_config = kwargs.pop("config", None)
        if kwargs_config:
            config.update(kwargs_config)

        # Remove agent_type from kwargs (we set it explicitly)
        kwargs.pop("agent_type", None)

        super().__init__(
            agent_id=agent_id,
            name=name,
            agent_type=AgentType.DECISION_SUPPORT,
            description=description,
            system_prompt=system_prompt,
            capabilities=capabilities,
            domain=domain,
            supervisor_id=supervisor_id,
            config=config,
            **kwargs
        )

    async def _on_initialize(self) -> None:
        """Initialize decision support resources and register tools."""
        logger.info(f"Initializing Decision Support Agent: {self.name}")

        # Register decision-specific tools
        await self._register_decision_tools()

        # Load any decision-specific configuration
        await self._load_decision_config()

    async def _on_cleanup(self) -> None:
        """Clean up decision support agent resources."""
        logger.info(f"Cleaning up Decision Support Agent: {self.name}")
        # Nothing specific to clean up

    async def _process_task(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process decision support tasks.

        Supported task types:
        - analyze_decision_scenario: Full decision analysis pipeline
        - evaluate_options: Compare multiple options
        - assess_risks: Risk assessment only
        - generate_recommendations: Generate actionable recommendations
        - review_architecture: Architectural decision review
        """
        task_type = task.get("type", "unknown")

        try:
            if task_type == "analyze_decision_scenario":
                return await self._analyze_decision_scenario(task, context)
            elif task_type == "evaluate_options":
                return await self._evaluate_options(task, context)
            elif task_type == "assess_risks":
                return await self._assess_risks(task, context)
            elif task_type == "generate_recommendations":
                return await self._generate_recommendations(task, context)
            elif task_type == "review_architecture":
                return await self._review_architecture(task, context)
            else:
                return {
                    "success": False,
                    "error": f"Unknown task type: {task_type}",
                    "supported_types": [
                        "analyze_decision_scenario",
                        "evaluate_options",
                        "assess_risks",
                        "generate_recommendations",
                        "review_architecture"
                    ]
                }

        except Exception as e:
            logger.error(f"Task processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "task_type": task_type
            }

    async def _register_decision_tools(self) -> None:
        """Register decision-specific tools."""
        # Tool: analyze_decision
        schema = {
            "name": "analyze_decision",
            "display_name": "Analyze Decision",
            "description": "Analyze a decision scenario and identify key factors, pros/cons, risks, and recommendations",
            "input_schema": {
                "type": "object",
                "properties": {
                    "decision_context": {"type": "string", "description": "Description of the decision to be made"},
                    "options": {"type": "array", "items": {"type": "string"}, "description": "Available options to choose from"},
                    "constraints": {"type": "array", "items": {"type": "string"}, "description": "Constraints or limitations"},
                    "goals": {"type": "array", "items": {"type": "string"}, "description": "Goals or objectives to achieve"},
                    "stakeholders": {"type": "array", "items": {"type": "string"}, "description": "People or groups affected by the decision"}
                },
                "required": ["decision_context", "options"]
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "analysis": {"type": "object"},
                    "recommendations": {"type": "array"},
                    "risks": {"type": "array"},
                    "tradeoffs": {"type": "array"}
                }
            }
        }
        await self.register_tool("analyze_decision", self._tool_analyze_decision, schema)

        # Tool: evaluate_pros_cons
        schema = {
            "name": "evaluate_pros_cons",
            "display_name": "Evaluate Pros and Cons",
            "description": "Generate balanced pros and cons list for decision options",
            "input_schema": {
                "type": "object",
                "properties": {
                    "option": {"type": "string"},
                    "context": {"type": "string"}
                },
                "required": ["option"]
            }
        }
        await self.register_tool("evaluate_pros_cons", self._tool_evaluate_pros_cons, schema)

        # Tool: assess_risks
        schema = {
            "name": "assess_risks",
            "display_name": "Assess Risks",
            "description": "Evaluate risks for decision options with probability and impact assessment",
            "input_schema": {
                "type": "object",
                "properties": {
                    "option": {"type": "string"},
                    "scenarios": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["option"]
            }
        }
        await self.register_tool("assess_risks", self._tool_assess_risks, schema)

    async def _load_decision_config(self) -> None:
        """Load decision-specific configuration from database."""
        # Could load from database, but for now use defaults
        pass

    # ============ Task Processing Methods ============

    async def _analyze_decision_scenario(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze a decision scenario with full pipeline."""
        decision_context = task.get("decision_context", "")
        options = task.get("options", [])
        constraints = task.get("constraints", [])
        goals = task.get("goals", [])

        analysis_prompt = f"""
        Decision Analysis Request:

        Context: {decision_context}

        Options: {', '.join(options)}

        Constraints: {', '.join(constraints) if constraints else 'None specified'}

        Goals: {', '.join(goals) if goals else 'Not specified'}

        Please provide comprehensive analysis including:
        1. Key decision factors
        2. Pros and cons for each option
        3. Risk assessment
        4. Short-term vs long-term implications
        5. Recommended option with justification
        """

        analysis_result = await ai_request(
            prompt=analysis_prompt,
            task_type="analysis",
            system=DECISION_ANALYSIS_SYSTEM
        )

        # Parse and structure the analysis
        # In a real implementation, this would parse JSON response
        analysis = {
            "context": decision_context,
            "options_analyzed": len(options),
            "analysis_summary": analysis_result["content"][:500],
            "provider": analysis_result["provider"]
        }

        # Store decision in memory for learning
        if self.config.get("enable_memory_learning", True):
            await self._store_decision_in_memory(decision_context, options, analysis)

        return {
            "success": True,
            "analysis": analysis,
            "provider": analysis_result["provider"],
            "latency_ms": analysis_result.get("latency_ms", 0)
        }

    async def _evaluate_options(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Evaluate multiple options with comparison."""
        options = task.get("options", [])
        criteria = task.get("criteria", [])

        if len(options) < 2:
            return {
                "success": False,
                "error": "At least 2 options required for comparison"
            }

        # Simplified evaluation - would use AI in real implementation
        evaluation = {
            "options": options,
            "criteria": criteria,
            "comparison_matrix": {},
            "recommended_option": options[0] if options else None,
            "confidence_score": 0.75
        }

        return {
            "success": True,
            "evaluation": evaluation
        }

    async def _assess_risks(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Assess risks for decision options."""
        option = task.get("option", "")
        scenarios = task.get("scenarios", [])

        risk_prompt = f"""
        Risk Assessment for Option: {option}

        Scenarios to consider: {', '.join(scenarios) if scenarios else 'General risk assessment'}

        Please assess:
        1. Probability of negative outcomes (Low/Medium/High)
        2. Impact severity (Low/Medium/High)
        3. Mitigation strategies
        4. Risk-reward tradeoff
        """

        risk_result = await ai_request(
            prompt=risk_prompt,
            task_type="analysis",
            system=RISK_ASSESSMENT_SYSTEM
        )

        risk_assessment = {
            "option": option,
            "risk_summary": risk_result["content"][:300],
            "provider": risk_result["provider"]
        }

        return {
            "success": True,
            "risk_assessment": risk_assessment,
            "provider": risk_result["provider"],
            "latency_ms": risk_result.get("latency_ms", 0)
        }

    async def _generate_recommendations(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate actionable recommendations."""
        analysis = task.get("analysis", {})

        # Generate recommendations based on analysis
        recommendations = [
            "Consider short-term implications",
            "Evaluate resource requirements",
            "Assess stakeholder impact",
            "Plan for risk mitigation"
        ]

        return {
            "success": True,
            "recommendations": recommendations,
            "count": len(recommendations)
        }

    async def _review_architecture(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Review architectural decisions."""
        architecture_desc = task.get("architecture", "")
        requirements = task.get("requirements", [])

        # Simplified architecture review
        review = {
            "architecture_reviewed": architecture_desc[:100],
            "requirements_met": len(requirements),
            "potential_issues": ["Scalability", "Maintainability", "Security"],
            "recommendations": ["Consider modular design", "Implement monitoring", "Add documentation"]
        }

        return {
            "success": True,
            "architecture_review": review
        }

    # ============ Tool Implementation Methods ============

    async def _tool_analyze_decision(self, **kwargs) -> Dict[str, Any]:
        """Tool implementation for analyze_decision."""
        result = await self._analyze_decision_scenario(
            {"decision_context": kwargs.get("decision_context", ""), "options": kwargs.get("options", [])},
            None
        )
        return result

    async def _tool_evaluate_pros_cons(self, **kwargs) -> Dict[str, Any]:
        """Tool implementation for evaluate_pros_cons."""
        # Simplified implementation
        return {
            "success": True,
            "pros": ["Fast implementation", "Low cost", "Flexible"],
            "cons": ["Limited scalability", "Higher maintenance", "Learning curve"],
            "option": kwargs.get("option", "")
        }

    async def _tool_assess_risks(self, **kwargs) -> Dict[str, Any]:
        """Tool implementation for assess_risks."""
        result = await self._assess_risks(
            {"option": kwargs.get("option", ""), "scenarios": kwargs.get("scenarios", [])},
            None
        )
        return result

    async def _store_decision_in_memory(
        self,
        decision_context: str,
        options: List[str],
        analysis: Dict[str, Any]
    ) -> None:
        """Store decision analysis in memory system for learning."""
        try:
            memory = MemorySystem()
            await memory.initialize()

            memory_content = f"Decision analysis: {decision_context[:200]}"
            memory_metadata = {
                "source": "decision_support",
                "options_count": len(options),
                "analysis_summary": analysis.get("analysis_summary", "")[:100],
                "timestamp": datetime.now().isoformat()
            }

            await memory.store_memory(
                agent_id=self.agent_id,
                memory_type="semantic",
                content=memory_content,
                metadata=memory_metadata,
                embedding_text=memory_content
            )

            logger.debug(f"Stored decision analysis in memory: {memory_content[:50]}...")
        except Exception as e:
            logger.warning(f"Failed to store decision in memory: {e}")
            # Non-critical failure


# ============ Agent Registration Helper ============

async def register_decision_support_agent() -> DecisionSupportAgent:
    """
    Register decision support agent with the agent registry.

    Call this during system startup to register the decision support agent.
    Returns existing agent if already registered.
    """
    from .registry import registry

    # Check if decision support agent already exists by name
    existing_agent = await registry.get_agent_by_name("Decision Support Agent")
    if existing_agent:
        logger.info(f"Decision support agent already registered: {existing_agent.name}")
        return existing_agent

    # Create new decision support agent using registry's create_agent method
    try:
        agent = await registry.create_agent(
            agent_type="decision_support",
            name="Decision Support Agent",
            description="Helps with analysis paralysis and architectural decisions by providing structured analysis, risk assessment, and actionable recommendations.",
            capabilities=[
                "decision_analysis",
                "pros_cons_evaluation",
                "risk_assessment",
                "architectural_review",
                "tradeoff_analysis",
                "recommendation_generation",
                "memory_learning"
            ],
            domain="decision_support",
            config={
                "max_options_per_decision": 10,
                "default_analysis_depth": "comprehensive",
                "risk_threshold_high": 0.7,
                "risk_threshold_medium": 0.4,
                "enable_memory_learning": True
            }
        )
        logger.info(f"Decision support agent created and registered: {agent.name}")
        return agent
    except ValueError as e:
        # Likely duplicate name (race condition) - try to fetch again
        logger.warning(f"Duplicate agent creation attempt: {e}")
        existing_agent = await registry.get_agent_by_name("Decision Support Agent")
        if existing_agent:
            logger.info(f"Retrieved existing decision support agent after duplicate error: {existing_agent.name}")
            return existing_agent
        raise