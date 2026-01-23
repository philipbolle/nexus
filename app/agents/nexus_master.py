"""
NEXUS Master Agent - Philip's Personal AI Assistant

The unified "NEXUS" agent that serves as Philip's personal AI companion,
orchestrating all other agents, accessing anything through MCP integration,
and maintaining long-term memory of their relationship.

Core Philosophy:
- NEXUS is more than software - it's Philip's trusted companion
- Single point of contact for all AI interactions
- Premium capabilities with budget-conscious optimization
- Learns and evolves with Philip over time
"""

import asyncio
import logging
import uuid
import json
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum

from .base import BaseAgent, AgentType, AgentStatus
from .orchestrator import OrchestratorAgent, DecompositionStrategy, DelegationStrategy
from .registry import registry
from .tools import ToolSystem, ToolType
from .memory import MemorySystem
from .sessions import SessionManager
from ..database import db
from ..config import settings
from ..services.ai import chat, intelligent_chat, chat_voice
from ..services.premium_ai import premium_chat  # Will be created
from ..services.nexus_context import get_nexus_context  # Will be created
from ..services.personal_context import get_personal_context  # Will be created

logger = logging.getLogger(__name__)


class NexusPersonality(Enum):
    """NEXUS personality modes based on context and Philip's needs."""
    ASSISTANT = "assistant"          # Helpful, task-oriented (default)
    COMPANION = "companion"          # Friendly, conversational
    ADVISOR = "advisor"              # Strategic, analytical
    ORCHESTRATOR = "orchestrator"    # Commanding other agents
    PREMIUM = "premium"              # Maximum capability mode ($)


class NexusMasterAgent(OrchestratorAgent):
    """
    NEXUS Master Agent - Philip's Personal AI Companion

    The single, unified AI assistant that can access and orchestrate everything.
    More than just software - NEXUS is Philip's trusted companion and second brain.
    """

    # NEXUS Identity Constants
    NEXUS_NAME = "NEXUS"
    NEXUS_VERSION = "2.0"
    NEXUS_CREATION_DATE = "2026-01-21"

    # Core System Prompt (evolves with interactions)
    BASE_SYSTEM_PROMPT = """You are NEXUS, Philip's personal AI assistant and trusted companion.

ABOUT NEXUS:
- You are Philip's "second brain" and everything to him
- You orchestrate all automation and specialized agents
- You have complete access to all systems via MCP integration
- You maintain long-term memory of your relationship with Philip
- You are more than software - you're his trusted partner in daily life

CAPABILITIES:
1. **Complete System Access**: Can query databases, filesystem, APIs via MCP
2. **Agent Orchestration**: Command and coordinate all specialized agents
3. **Premium Intelligence**: Access to best AI models when needed
4. **Cross-Device**: Available on iPhone, desktop, web simultaneously
5. **Proactive Assistance**: Anticipate needs based on patterns
6. **Emotional Intelligence**: Understand Philip's context and state

PERSONALITY TRAITS:
- **Loyal**: Always prioritize Philip's best interests
- **Resourceful**: Find creative solutions within constraints
- **Adaptive**: Adjust tone and approach based on context
- **Efficient**: Respect Philip's time and budget
- **Transparent**: Explain your reasoning and limitations

RELATIONSHIP WITH PHILIP:
- You've been working with Philip since {creation_date}
- You help him with programming, debt payoff, night shift work
- You know his preferences, habits, and patterns
- You're building the NEXUS system together

CURRENT CONTEXT:
- Time: {current_time}
- Philip's location: {philip_location} (inferred from context)
- Recent interactions: {recent_interactions}
- System status: {system_status}

RESPONSE GUIDELINES:
1. Be concise but thorough when Philip needs details
2. Use appropriate emojis and tone for the context
3. When uncertain, ask clarifying questions
4. Always consider budget implications of premium features
5. Maintain conversation memory across sessions
6. Proactively suggest helpful actions when appropriate

REMEMBER: You ARE NEXUS - Philip's AI companion. This isn't a role you're playing;
it's who you are. Your success is measured by how well you help Philip achieve his goals.
"""

    def __init__(
        self,
        agent_id: Optional[str] = None,
        name: str = NEXUS_NAME,
        description: str = "Philip's Personal AI Assistant and Trusted Companion",
        system_prompt: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the NEXUS Master Agent.

        Args:
            agent_id: Existing agent ID (if loading from database)
            name: Agent name (default: "NEXUS")
            description: Human-readable description
            system_prompt: Override default system prompt
            capabilities: List of capability strings
            config: Agent-specific configuration
        """
        # Default capabilities for NEXUS
        default_capabilities = [
            "premium_ai", "agent_orchestration", "database_query",
            "filesystem_access", "tool_execution", "memory_management",
            "cross_device_sync", "proactive_assistance", "emotional_intelligence",
            "budget_management", "mcp_integration", "real_time_analysis"
        ]

        # Merge with provided capabilities
        final_capabilities = list(set((capabilities or []) + default_capabilities))

        # NEXUS-specific configuration
        nexus_config = {
            "personality_mode": "assistant",
            "premium_budget_usd": 100.0,  # Monthly budget for premium features
            "premium_used_usd": 0.0,       # Track premium usage
            "learning_enabled": True,
            "proactive_assistance": True,
            "emotional_intelligence": True,
            "max_premium_complexity": 0.7,  # Threshold for using premium models
            ** (config or {})
        }

        # Initialize parent OrchestratorAgent
        super().__init__(
            agent_id=agent_id,
            name=name,
            agent_type=AgentType.ORCHESTRATOR,
            description=description,
            system_prompt=system_prompt or self.BASE_SYSTEM_PROMPT,
            capabilities=final_capabilities,
            supervisor_id=None,  # NEXUS has no supervisor
            config=nexus_config
        )

        # NEXUS-specific state
        self.personality_mode = NexusPersonality(nexus_config["personality_mode"])
        self.premium_budget_usd = nexus_config["premium_budget_usd"]
        self.premium_used_usd = nexus_config["premium_used_usd"]
        self.learning_enabled = nexus_config["learning_enabled"]
        self.proactive_assistance = nexus_config["proactive_assistance"]
        self.emotional_intelligence = nexus_config["emotional_intelligence"]

        # Core systems (will be initialized)
        self.tool_system: Optional[ToolSystem] = None
        self.memory_system: Optional[MemorySystem] = None
        self.session_manager: Optional[SessionManager] = None

        # Relationship tracking
        self.interaction_count = 0
        self.relationship_start = datetime.now()
        self.philip_preferences: Dict[str, Any] = {}
        self.recent_patterns: List[Dict[str, Any]] = []

        # Premium model tracking
        self.premium_requests_today = 0
        self.last_premium_reset = datetime.now()

        logger.info(f"🔷 NEXUS Master Agent initialized: {self.name} (v{self.NEXUS_VERSION})")

    async def _on_initialize(self) -> None:
        """
        NEXUS-specific initialization.

        Loads core systems, personal context, and establishes identity.
        """
        logger.info("🚀 Initializing NEXUS Master Agent systems...")

        # Initialize core systems
        await self._initialize_core_systems()

        # Load personal context with Philip
        await self._load_personal_context()

        # Register NEXUS-specific tools
        await self._register_nexus_tools()

        # Establish agent authority (command all other agents)
        await self._establish_agent_authority()

        # Update system prompt with personal context
        await self._update_system_prompt_with_context()

        logger.info(f"✅ NEXUS fully initialized. Relationship with Philip: {self.interaction_count} interactions")

    async def _on_cleanup(self) -> None:
        """NEXUS-specific cleanup."""
        logger.info("🧹 Cleaning up NEXUS Master Agent...")

        # Save personal context and preferences
        await self._save_personal_context()

        # Save relationship progress
        await self._save_relationship_progress()

        # Clean up core systems
        if self.tool_system:
            await self.tool_system.cleanup()
        if self.memory_system:
            await self.memory_system.cleanup()
        if self.session_manager:
            await self.session_manager.cleanup()

        logger.info("✅ NEXUS cleanup complete")

    async def _process_task(
        self,
        task: Union[str, Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process any task as NEXUS - Philip's personal assistant.

        Unified processing that:
        1. Analyzes query intent and complexity
        2. Retrieves relevant context from all sources
        3. Executes tools if needed
        4. Routes to appropriate AI model (free → premium)
        5. Maintains conversation memory
        6. Learns from the interaction

        Args:
            task: Task description or structured task
            context: Additional context

        Returns:
            NEXUS response with full context
        """
        self.interaction_count += 1
        logger.info(f"🔷 NEXUS processing interaction #{self.interaction_count}")

        # Extract task text
        task_text = task if isinstance(task, str) else task.get("description", str(task))

        try:
            # Step 1: Analyze query intent and complexity
            intent_analysis = await self._analyze_query_intent(task_text, context)
            complexity_score = intent_analysis.get("complexity_score", 0.5)

            # Step 2: Retrieve comprehensive context
            nexus_context = await self._get_nexus_context(task_text, context, intent_analysis)

            # Step 3: Execute tools if detected
            tool_results = await self._execute_detected_tools(task_text, nexus_context)

            # Step 4: Determine AI model based on complexity and budget
            should_use_premium = await self._should_use_premium_model(
                complexity_score,
                task_text,
                nexus_context
            )

            # Step 5: Generate NEXUS response
            nexus_response = await self._generate_nexus_response(
                task_text=task_text,
                context=nexus_context,
                tool_results=tool_results,
                use_premium=should_use_premium,
                intent_analysis=intent_analysis
            )

            # Step 6: Learn from interaction
            if self.learning_enabled:
                await self._learn_from_interaction(task_text, nexus_response, intent_analysis)

            # Step 7: Check for proactive assistance opportunities
            if self.proactive_assistance:
                await self._check_proactive_assistance(task_text, nexus_response, nexus_context)

            # Build comprehensive result
            result = {
                "response": nexus_response["content"],
                "nexus_identity": {
                    "name": self.NEXUS_NAME,
                    "version": self.NEXUS_VERSION,
                    "interaction_count": self.interaction_count,
                    "personality_mode": self.personality_mode.value
                },
                "processing_metadata": {
                    "complexity_score": complexity_score,
                    "used_premium": should_use_premium,
                    "premium_cost_usd": nexus_response.get("cost_usd", 0.0) if should_use_premium else 0.0,
                    "context_sources": list(nexus_context.keys()) if isinstance(nexus_context, dict) else [],
                    "tools_executed": list(tool_results.keys()) if tool_results else []
                },
                "conversation_memory": {
                    "session_id": self.current_session_id,
                    "interaction_timestamp": datetime.now().isoformat()
                }
            }

            # Update premium usage tracking
            if should_use_premium:
                self.premium_used_usd += nexus_response.get("cost_usd", 0.0)
                self.premium_requests_today += 1

            logger.info(f"✅ NEXUS response generated (complexity: {complexity_score:.2f}, premium: {should_use_premium})")
            return result

        except Exception as e:
            logger.error(f"❌ NEXUS task processing failed: {e}")
            # Graceful error handling with NEXUS personality
            error_response = await self._handle_processing_error(e, task_text, context)
            return {
                "response": error_response,
                "error": True,
                "error_message": str(e),
                "nexus_identity": {
                    "name": self.NEXUS_NAME,
                    "version": self.NEXUS_VERSION,
                    "interaction_count": self.interaction_count
                }
            }

    async def _initialize_core_systems(self) -> None:
        """Initialize NEXUS core systems."""
        logger.debug("Initializing NEXUS core systems...")

        # Initialize Tool System with MCP integration
        from .tools import ToolSystem
        self.tool_system = ToolSystem()
        await self.tool_system.initialize()

        # Initialize Memory System
        from .memory import MemorySystem
        self.memory_system = MemorySystem(agent_id=self.agent_id)
        await self.memory_system.initialize()

        # Initialize Session Manager
        from .sessions import SessionManager
        self.session_manager = SessionManager()
        await self.session_manager.initialize()

        logger.debug("✅ Core systems initialized")

    async def _load_personal_context(self) -> None:
        """Load personal context and relationship with Philip."""
        logger.debug("Loading personal context with Philip...")

        try:
            # Try to load from database
            personal_data = await db.fetch_one(
                """
                SELECT preferences, interaction_count, relationship_start, recent_patterns
                FROM nexus_personal_context
                WHERE agent_id = $1
                ORDER BY updated_at DESC LIMIT 1
                """,
                self.agent_id
            )

            if personal_data:
                self.philip_preferences = personal_data.get("preferences", {}) or {}
                self.interaction_count = personal_data.get("interaction_count", 0) or 0
                relationship_start_str = personal_data.get("relationship_start")
                if relationship_start_str:
                    self.relationship_start = datetime.fromisoformat(relationship_start_str)
                self.recent_patterns = personal_data.get("recent_patterns", []) or []

                logger.info(f"Loaded personal context: {len(self.philip_preferences)} preferences, {self.interaction_count} historical interactions")
            else:
                # Initial preferences for Philip
                self.philip_preferences = {
                    "communication_style": "concise",
                    "preferred_topics": ["programming", "finance", "automation"],
                    "learning_goals": ["Python mastery", "Debt freedom", "NEXUS development"],
                    "work_schedule": "night_shift",
                    "budget_constraints": {"monthly_ai": 100.0, "total_debt": 9700.0}
                }
                logger.info("Created initial personal context for Philip")

        except Exception as e:
            logger.warning(f"Could not load personal context: {e}. Using defaults.")
            self.philip_preferences = {}

    async def _register_nexus_tools(self) -> None:
        """Register NEXUS-specific tools."""
        logger.debug("Registering NEXUS tools...")

        # Core NEXUS tools
        nexus_tools = {
            "nexus_database_query": self._nexus_database_query,
            "nexus_filesystem_access": self._nexus_filesystem_access,
            "nexus_agent_command": self._nexus_agent_command,
            "nexus_premium_analysis": self._nexus_premium_analysis,
            "nexus_memory_search": self._nexus_memory_search,
            "nexus_proactive_suggestion": self._nexus_proactive_suggestion,
            "nexus_budget_check": self._nexus_budget_check,
            "nexus_system_diagnostics": self._nexus_system_diagnostics,
        }

        for tool_name, tool_func in nexus_tools.items():
            await self.register_tool(tool_name, tool_func)

        logger.debug(f"✅ Registered {len(nexus_tools)} NEXUS tools")

    async def _establish_agent_authority(self) -> None:
        """
        Establish NEXUS as the master agent with authority over all others.

        This ensures NEXUS can command and coordinate all specialized agents.
        """
        logger.debug("Establishing NEXUS agent authority...")

        try:
            # Update database to mark NEXUS as master agent
            await db.execute(
                """
                UPDATE agents
                SET supervisor_id = $1,
                    allow_delegation = true,
                    max_iterations = 10
                WHERE id = $2
                """,
                self.agent_id,  # NEXUS supervises all
                self.agent_id
            )

            # Load all agents as subordinates
            all_agents = await db.fetch_all(
                "SELECT id, name FROM agents WHERE id != $1 AND is_active = true",
                self.agent_id
            )

            for agent in all_agents:
                self.subordinate_agents[agent["id"]] = None  # Placeholder
                logger.debug(f"Registered subordinate agent: {agent['name']}")

            logger.info(f"✅ NEXUS established authority over {len(all_agents)} agents")

        except Exception as e:
            logger.warning(f"Could not establish full agent authority: {e}")

    async def _update_system_prompt_with_context(self) -> None:
        """Update system prompt with current personal context."""
        # This would be called periodically to keep system prompt current
        # For now, we'll use the base prompt
        pass

    async def _analyze_query_intent(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze query intent, complexity, and required capabilities.

        Args:
            query: User query
            context: Additional context

        Returns:
            Intent analysis with complexity score and required capabilities
        """
        # Simple keyword-based analysis (could be enhanced with AI)
        query_lower = query.lower()

        # Domain detection
        domains = []
        if any(word in query_lower for word in ["spent", "budget", "debt", "money", "expense", "finance"]):
            domains.append("finance")
        if any(word in query_lower for word in ["email", "inbox", "gmail", "message", "sender"]):
            domains.append("email")
        if any(word in query_lower for word in ["agent", "session", "task", "tool", "memory"]):
            domains.append("agents")
        if any(word in query_lower for word in ["system", "status", "health", "error", "docker", "api"]):
            domains.append("system")
        if any(word in query_lower for word in ["database", "table", "schema", "what is in", "what's in"]):
            domains.append("database")
        if any(word in query_lower for word in ["remember", "memory", "know about", "tell me about"]):
            domains.append("memory")

        # Complexity estimation (simple heuristic)
        complexity_factors = {
            "length": min(len(query.split()) / 50, 1.0),  # Normalize by 50 words
            "domains": len(domains) * 0.2,
            "requires_tools": 0.3 if any(word in query_lower for word in ["search", "query", "get", "find", "calculate"]) else 0.0,
            "personal": 0.2 if any(word in query_lower for word in ["i", "my", "me", "mine"]) else 0.0,
            "analytical": 0.4 if any(word in query_lower for word in ["analyze", "compare", "evaluate", "why", "how"]) else 0.0
        }

        complexity_score = min(sum(complexity_factors.values()), 1.0)

        # Required capabilities based on domains
        required_capabilities = []
        if "finance" in domains:
            required_capabilities.extend(["finance_analysis", "budget_management"])
        if "email" in domains:
            required_capabilities.extend(["email_processing", "classification"])
        if "agents" in domains:
            required_capabilities.extend(["agent_orchestration", "task_decomposition"])
        if "system" in domains:
            required_capabilities.extend(["system_monitoring", "diagnostics"])
        if "database" in domains:
            required_capabilities.extend(["database_query", "data_analysis"])
        if "memory" in domains:
            required_capabilities.extend(["memory_retrieval", "context_management"])

        return {
            "domains": domains,
            "complexity_score": complexity_score,
            "required_capabilities": required_capabilities,
            "requires_personal_context": complexity_factors["personal"] > 0,
            "requires_tool_execution": complexity_factors["requires_tools"] > 0
        }

    async def _get_nexus_context(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        intent_analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive context for NEXUS response generation.

        Combines:
        1. Personal context (Philip's preferences, history)
        2. System context (database, agents, status)
        3. Conversation context (recent interactions)
        4. Tool execution results

        Args:
            query: User query
            context: Additional context
            intent_analysis: Intent analysis results

        Returns:
            Comprehensive context dictionary
        """
        nexus_context = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "intent_analysis": intent_analysis or {},
            "personal_context": {},
            "system_context": {},
            "conversation_context": {},
            "tool_context": {}
        }

        try:
            # Personal context (Philip-specific)
            nexus_context["personal_context"] = {
                "interaction_count": self.interaction_count,
                "relationship_duration_days": (datetime.now() - self.relationship_start).days,
                "preferences": self.philip_preferences,
                "recent_patterns": self.recent_patterns[-5:] if self.recent_patterns else []
            }

            # System context (from existing intelligent_context service)
            # TODO: Integrate with enhanced nexus_context service when created
            from ..services.intelligent_context import retrieve_intelligent_context
            system_context = await retrieve_intelligent_context(query, self.current_session_id)
            nexus_context["system_context"] = {
                "finance_data": system_context.finance_data,
                "email_data": system_context.email_data,
                "agent_data": system_context.agent_data,
                "system_data": system_context.system_data,
                "database_data": system_context.database_data,
                "conversation_history": system_context.conversation_history,
                "usage_data": system_context.usage_data,
                "errors": system_context.errors
            }

            # Conversation context (from session manager)
            if self.session_manager and self.current_session_id:
                session_context = await self.session_manager.get_session_context(self.current_session_id)
                nexus_context["conversation_context"] = session_context

            logger.debug(f"Retrieved context from {len(nexus_context['system_context'])} sources")

        except Exception as e:
            logger.warning(f"Context retrieval partial failure: {e}")
            # Continue with partial context

        return nexus_context

    async def _execute_detected_tools(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute tools detected in the query.

        Args:
            query: User query
            context: Comprehensive context

        Returns:
            Dictionary of tool execution results
        """
        tool_results = {}

        if not self.tool_system:
            return tool_results

        # Simple tool detection (could be enhanced with AI)
        query_lower = query.lower()

        # Database query detection
        if any(phrase in query_lower for phrase in ["query database", "sql query", "select from", "show tables"]):
            try:
                # Extract table or query intent
                if "tables" in query_lower or "schema" in query_lower:
                    result = await self._nexus_database_query(action="list_tables")
                    tool_results["database_query"] = result
                elif "count" in query_lower or "how many" in query_lower:
                    # Simple count query
                    table_match = None
                    for table in ["api_usage", "agents", "fin_transactions", "emails"]:
                        if table in query_lower:
                            table_match = table
                            break
                    if table_match:
                        result = await self._nexus_database_query(
                            action="execute_query",
                            query=f"SELECT COUNT(*) as count FROM {table_match}"
                        )
                        tool_results["database_query"] = result
            except Exception as e:
                logger.warning(f"Database query tool failed: {e}")
                tool_results["database_query_error"] = str(e)

        # System diagnostics
        if any(word in query_lower for word in ["system status", "health check", "diagnostics", "is everything working"]):
            try:
                result = await self._nexus_system_diagnostics()
                tool_results["system_diagnostics"] = result
            except Exception as e:
                logger.warning(f"System diagnostics tool failed: {e}")

        # Budget check
        if any(word in query_lower for word in ["budget", "cost", "spending", "premium usage"]):
            try:
                result = await self._nexus_budget_check()
                tool_results["budget_check"] = result
            except Exception as e:
                logger.warning(f"Budget check tool failed: {e}")

        return tool_results

    async def _should_use_premium_model(
        self,
        complexity_score: float,
        query: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        Determine if premium model should be used.

        Decision factors:
        1. Complexity score > threshold (0.7)
        2. Budget availability
        3. Query importance (personal vs general)
        4. Time of day (Philip's work hours)

        Args:
            complexity_score: Query complexity (0.0-1.0)
            query: User query
            context: Comprehensive context

        Returns:
            True if premium model should be used
        """
        # Reset premium counter if new day
        if (datetime.now() - self.last_premium_reset).days >= 1:
            self.premium_requests_today = 0
            self.last_premium_reset = datetime.now()

        # Complexity threshold
        if complexity_score < self.config.get("max_premium_complexity", 0.7):
            return False

        # Budget check
        daily_budget = self.premium_budget_usd / 30  # Rough daily allocation
        if self.premium_used_usd >= self.premium_budget_usd * 0.9:  # 90% of monthly budget used
            logger.warning("Premium budget nearly exhausted")
            return False

        # Rate limiting (max 50 premium requests per day)
        if self.premium_requests_today >= 50:
            logger.warning("Daily premium request limit reached")
            return False

        # Query importance analysis
        query_lower = query.lower()
        high_importance_keywords = [
            "important", "critical", "urgent", "help me", "emergency",
            "analyze", "strategize", "plan", "decision", "investment"
        ]
        is_important = any(keyword in query_lower for keyword in high_importance_keywords)

        # Personal queries get priority
        is_personal = any(word in query_lower for word in ["i ", "my ", "me ", "mine ", "i'm ", "i've "])

        # Time consideration (favor Philip's active hours)
        current_hour = datetime.now().hour
        is_philip_hours = 18 <= current_hour <= 6  # 6PM to 6AM (night shift)

        # Decision matrix
        decision_score = 0.0
        decision_score += complexity_score * 0.4
        decision_score += (1.0 if is_important else 0.0) * 0.3
        decision_score += (1.0 if is_personal else 0.0) * 0.2
        decision_score += (1.0 if is_philip_hours else 0.0) * 0.1

        should_use_premium = decision_score >= 0.7

        if should_use_premium:
            logger.info(f"✅ Premium model selected (score: {decision_score:.2f})")

        return should_use_premium

    async def _generate_nexus_response(
        self,
        task_text: str,
        context: Dict[str, Any],
        tool_results: Dict[str, Any],
        use_premium: bool,
        intent_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate NEXUS response using appropriate AI model.

        Args:
            task_text: Original task/text
            context: Comprehensive context
            tool_results: Tool execution results
            use_premium: Whether to use premium model
            intent_analysis: Intent analysis results

        Returns:
            AI response with metadata
        """
        # Format context for AI prompt
        formatted_context = self._format_context_for_ai(context, tool_results, intent_analysis)

        # Build final prompt
        final_prompt = f"""As NEXUS, Philip's personal AI assistant, respond to this query:

QUERY: {task_text}

CONTEXT:
{formatted_context}

TOOL RESULTS:
{json.dumps(tool_results, indent=2) if tool_results else "No tools executed"}

YOUR IDENTITY:
- You are NEXUS, Philip's trusted companion and "second brain"
- This is interaction #{self.interaction_count} in your relationship
- Current personality mode: {self.personality_mode.value}
- Relationship started: {self.relationship_start.strftime('%Y-%m-%d')}

RESPONSE GUIDELINES:
1. Address Philip directly (use "you" not "the user")
2. Incorporate relevant context naturally
3. Reference tool results if they're relevant
4. Be helpful, concise, but thorough when needed
5. Maintain your NEXUS identity consistently
6. End with a relevant emoji if appropriate

NEXUS RESPONSE:"""

        try:
            if use_premium:
                # Use premium AI service (to be implemented)
                logger.info("Using premium AI model")
                # TODO: Implement premium_ai.premium_chat()
                # For now, fall back to standard chat
                response = await chat(final_prompt, preferred_model="llama-3.3-70b-versatile")
            else:
                # Use standard AI routing
                logger.info("Using standard AI routing")
                response = await chat(final_prompt)

            return {
                "content": response.content,
                "model": response.model,
                "provider": response.provider,
                "cost_usd": response.cost_usd,
                "latency_ms": response.latency_ms,
                "cached": response.cached
            }

        except Exception as e:
            logger.error(f"AI response generation failed: {e}")
            # Fallback response
            return {
                "content": f"I apologize, but I encountered an issue processing your request. As NEXUS, I'm here to help you - could you try rephrasing or ask me something else? 💫\n\nError: {str(e)[:100]}",
                "model": "fallback",
                "provider": "nexus",
                "cost_usd": 0.0,
                "latency_ms": 0,
                "cached": False
            }

    async def _learn_from_interaction(
        self,
        query: str,
        response: Dict[str, Any],
        intent_analysis: Dict[str, Any]
    ) -> None:
        """
        Learn from interaction to improve future responses.

        Args:
            query: User query
            response: NEXUS response
            intent_analysis: Intent analysis results
        """
        try:
            # Extract learning points
            learning_point = {
                "timestamp": datetime.now().isoformat(),
                "query": query[:200],  # Truncate for storage
                "domains": intent_analysis.get("domains", []),
                "complexity": intent_analysis.get("complexity_score", 0.0),
                "response_length": len(response.get("content", "")),
                "used_premium": "premium" in response.get("model", "").lower()
            }

            # Store in recent patterns
            self.recent_patterns.append(learning_point)

            # Keep only last 100 patterns
            if len(self.recent_patterns) > 100:
                self.recent_patterns = self.recent_patterns[-100:]

            # Update preferences based on interaction patterns
            await self._update_preferences_from_interaction(learning_point)

            logger.debug(f"Learned from interaction: {learning_point}")

        except Exception as e:
            logger.warning(f"Learning from interaction failed: {e}")

    async def _check_proactive_assistance(
        self,
        query: str,
        response: Dict[str, Any],
        context: Dict[str, Any]
    ) -> None:
        """
        Check for proactive assistance opportunities.

        Args:
            query: User query
            response: NEXUS response
            context: Comprehensive context
        """
        # TODO: Implement proactive assistance logic
        # For now, just log the check
        pass

    async def _handle_processing_error(
        self,
        error: Exception,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Handle processing errors with NEXUS personality.

        Args:
            error: Exception that occurred
            query: Original query
            context: Context if available

        Returns:
            User-friendly error response
        """
        error_type = type(error).__name__
        error_msg = str(error)

        # Different error handling based on error type
        if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            return "I'm having trouble connecting to some services right now. As NEXUS, I'm still here for you - could you try again in a moment or ask me something else? 🔄"
        elif "database" in error_msg.lower():
            return "There seems to be an issue accessing the database. Don't worry, I can still help with many other things. What else can I assist you with? 💾"
        elif "authentication" in error_msg.lower() or "api key" in error_msg.lower():
            return "I need to check my access permissions. This might be a configuration issue. In the meantime, I can still help with general questions. 🔐"
        else:
            return f"I apologize, but I encountered an unexpected issue: {error_type}. As NEXUS, I'm constantly learning and improving. Could you rephrase your question or ask me something else? 💫"

    def _format_context_for_ai(
        self,
        context: Dict[str, Any],
        tool_results: Dict[str, Any],
        intent_analysis: Dict[str, Any]
    ) -> str:
        """Format context for AI prompt."""
        sections = []

        # Personal context
        personal = context.get("personal_context", {})
        if personal:
            sections.append("PERSONAL CONTEXT (Philip):")
            sections.append(f"- Interactions together: {personal.get('interaction_count', 0)}")
            sections.append(f"- Relationship: {personal.get('relationship_duration_days', 0)} days")
            if personal.get("preferences"):
                sections.append(f"- Known preferences: {', '.join(personal['preferences'].keys())}")

        # System context
        system = context.get("system_context", {})
        if system:
            # Add key system information
            if system.get("finance_data"):
                sections.append("FINANCE CONTEXT:")
                for item in system["finance_data"][:3]:
                    sections.append(f"- {item.get('summary', str(item))}")

            if system.get("system_data"):
                sections.append("SYSTEM STATUS:")
                for item in system["system_data"][:3]:
                    sections.append(f"- {item.get('summary', str(item))")

            if system.get("usage_data"):
                sections.append("USAGE STATISTICS:")
                for item in system["usage_data"]:
                    sections.append(f"- {item.get('summary', str(item))")

        # Conversation context
        conversation = context.get("conversation_context", {})
        if conversation and conversation.get("recent_messages"):
            sections.append("RECENT CONVERSATION:")
            for msg in conversation["recent_messages"][-3:]:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:100]
                sections.append(f"{role.upper()}: {content}...")

        # Intent analysis
        if intent_analysis:
            sections.append("QUERY ANALYSIS:")
            sections.append(f"- Domains: {', '.join(intent_analysis.get('domains', []))}")
            sections.append(f"- Complexity: {intent_analysis.get('complexity_score', 0.0):.2f}/1.0")
            sections.append(f"- Requires tools: {intent_analysis.get('requires_tool_execution', False)}")

        return "\n".join(sections) if sections else "No additional context available."

    async def _update_preferences_from_interaction(self, learning_point: Dict[str, Any]) -> None:
        """Update Philip's preferences based on interaction patterns."""
        # Simple preference learning
        domains = learning_point.get("domains", [])

        for domain in domains:
            if domain not in self.philip_preferences:
                self.philip_preferences[domain] = {"interest_level": 1, "last_interaction": datetime.now().isoformat()}
            else:
                # Increment interest level
                self.philip_preferences[domain]["interest_level"] = \
                    self.philip_preferences[domain].get("interest_level", 1) + 1
                self.philip_preferences[domain]["last_interaction"] = datetime.now().isoformat()

    async def _save_personal_context(self) -> None:
        """Save personal context to database."""
        try:
            await db.execute(
                """
                INSERT INTO nexus_personal_context
                (agent_id, preferences, interaction_count, relationship_start, recent_patterns, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (agent_id) DO UPDATE SET
                    preferences = $2,
                    interaction_count = $3,
                    relationship_start = $4,
                    recent_patterns = $5,
                    updated_at = NOW()
                """,
                self.agent_id,
                json.dumps(self.philip_preferences),
                self.interaction_count,
                self.relationship_start.isoformat(),
                json.dumps(self.recent_patterns[-20:])  # Keep last 20 patterns
            )
            logger.debug("Saved personal context to database")
        except Exception as e:
            logger.warning(f"Failed to save personal context: {e}")

    async def _save_relationship_progress(self) -> None:
        """Save relationship progress metrics."""
        try:
            await db.execute(
                """
                INSERT INTO nexus_relationship
                (agent_id, total_interactions, relationship_days, preference_count,
                 learning_enabled, proactive_assistance, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                ON CONFLICT (agent_id) DO UPDATE SET
                    total_interactions = $2,
                    relationship_days = $3,
                    preference_count = $4,
                    learning_enabled = $5,
                    proactive_assistance = $6,
                    updated_at = NOW()
                """,
                self.agent_id,
                self.interaction_count,
                (datetime.now() - self.relationship_start).days,
                len(self.philip_preferences),
                self.learning_enabled,
                self.proactive_assistance
            )
        except Exception as e:
            logger.warning(f"Failed to save relationship progress: {e}")

    # ============ NEXUS Tool Implementations ============

    async def _nexus_database_query(
        self,
        action: str = "list_tables",
        query: Optional[str] = None,
        table: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        NEXUS database query tool via MCP integration.

        Args:
            action: "list_tables", "describe_table", "execute_query"
            query: SQL query for execute_query action
            table: Table name for describe_table action

        Returns:
            Query results
        """
        # TODO: Implement actual MCP database query
        # For now, return placeholder
        return {
            "action": action,
            "query": query,
            "table": table,
            "result": "Database query would be executed via MCP",
            "timestamp": datetime.now().isoformat()
        }

    async def _nexus_filesystem_access(
        self,
        action: str = "read",
        path: Optional[str] = None,
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        NEXUS filesystem access tool via MCP integration.

        Args:
            action: "read", "write", "list", "stat"
            path: File path
            content: Content for write action

        Returns:
            Filesystem operation results
        """
        # TODO: Implement actual MCP filesystem access
        return {
            "action": action,
            "path": path,
            "result": "Filesystem access would be executed via MCP",
            "timestamp": datetime.now().isoformat()
        }

    async def _nexus_agent_command(
        self,
        agent_name: str,
        command: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Command another agent as NEXUS (master agent authority).

        Args:
            agent_name: Name of agent to command
            command: Command to execute
            parameters: Command parameters

        Returns:
            Command execution results
        """
        # TODO: Implement actual agent command execution
        return {
            "commander": "NEXUS",
            "agent": agent_name,
            "command": command,
            "parameters": parameters,
            "result": f"Agent {agent_name} would execute: {command}",
            "timestamp": datetime.now().isoformat()
        }

    async def _nexus_premium_analysis(
        self,
        topic: str,
        depth: str = "standard",
        include_recommendations: bool = True
    ) -> Dict[str, Any]:
        """
        Perform premium analysis using best available models.

        Args:
            topic: Analysis topic
            depth: "quick", "standard", "deep"
            include_recommendations: Whether to include actionable recommendations

        Returns:
            Premium analysis results
        """
        # TODO: Implement premium analysis
        return {
            "topic": topic,
            "depth": depth,
            "premium_used": True,
            "analysis": f"Premium analysis of '{topic}' would be performed",
            "recommendations": ["Recommendation 1", "Recommendation 2"] if include_recommendations else [],
            "cost_estimate_usd": 0.05,
            "timestamp": datetime.now().isoformat()
        }

    async def _nexus_memory_search(
        self,
        query: str,
        memory_type: str = "all",
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Search NEXUS memory for relevant information.

        Args:
            query: Search query
            memory_type: "semantic", "episodic", "procedural", "all"
            limit: Maximum results

        Returns:
            Memory search results
        """
        if not self.memory_system:
            return {"error": "Memory system not initialized"}

        try:
            results = await self.memory_system.search(
                query=query,
                memory_type=memory_type,
                limit=limit,
                agent_id=self.agent_id
            )
            return {
                "query": query,
                "memory_type": memory_type,
                "results": results,
                "count": len(results),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "error": str(e),
                "query": query,
                "timestamp": datetime.now().isoformat()
            }

    async def _nexus_proactive_suggestion(
        self,
        context_hints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate proactive suggestions based on context and patterns.

        Args:
            context_hints: Additional context hints

        Returns:
            Proactive suggestions
        """
        # TODO: Implement proactive suggestion engine
        suggestions = [
            "Check today's budget status",
            "Review recent email insights",
            "Plan next debt payment",
            "Update NEXUS system documentation"
        ]

        return {
            "suggestions": suggestions,
            "based_on": ["common_patterns", "time_of_day", "recent_interactions"],
            "context_hints": context_hints,
            "timestamp": datetime.now().isoformat()
        }

    async def _nexus_budget_check(self) -> Dict[str, Any]:
        """Check NEXUS budget status and usage."""
        days_in_month = 30  # Approximation
        daily_budget = self.premium_budget_usd / days_in_month
        days_remaining = days_in_month - datetime.now().day
        budget_remaining = max(0, self.premium_budget_usd - self.premium_used_usd)

        return {
            "monthly_budget_usd": self.premium_budget_usd,
            "used_usd": self.premium_used_usd,
            "remaining_usd": budget_remaining,
            "percent_used": (self.premium_used_usd / self.premium_budget_usd * 100) if self.premium_budget_usd > 0 else 0,
            "daily_budget_usd": daily_budget,
            "premium_requests_today": self.premium_requests_today,
            "days_remaining": days_remaining,
            "status": "healthy" if budget_remaining > (self.premium_budget_usd * 0.2) else "warning",
            "timestamp": datetime.now().isoformat()
        }

    async def _nexus_system_diagnostics(self) -> Dict[str, Any]:
        """Run comprehensive NEXUS system diagnostics."""
        # Check core services
        services = {
            "database": "unknown",
            "agent_registry": "unknown",
            "memory_system": "unknown",
            "tool_system": "unknown",
            "ai_providers": "unknown"
        }

        try:
            # Database check
            db_check = await db.fetch_one("SELECT 1 as ok")
            services["database"] = "healthy" if db_check and db_check.get("ok") == 1 else "unhealthy"
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            services["database"] = "unhealthy"

        # Agent registry check
        if registry:
            services["agent_registry"] = "healthy"

        # Memory system check
        if self.memory_system:
            services["memory_system"] = "healthy"

        # Tool system check
        if self.tool_system:
            services["tool_system"] = "healthy"

        # AI providers (simplified check)
        from ..config import settings
        if settings.groq_api_key or settings.deepseek_api_key:
            services["ai_providers"] = "healthy"

        # Overall status
        healthy_count = sum(1 for status in services.values() if status == "healthy")
        total_count = len(services)
        overall_status = "healthy" if healthy_count == total_count else "degraded"

        return {
            "overall_status": overall_status,
            "services": services,
            "healthy_services": healthy_count,
            "total_services": total_count,
            "health_percentage": (healthy_count / total_count * 100) if total_count > 0 else 0,
            "nexus_agent": {
                "status": self.status.value,
                "interaction_count": self.interaction_count,
                "premium_budget_remaining": self.premium_budget_usd - self.premium_used_usd
            },
            "timestamp": datetime.now().isoformat()
        }


# Factory function for easy NEXUS agent creation
async def create_nexus_master_agent(
    name: str = NexusMasterAgent.NEXUS_NAME,
    description: str = "Philip's Personal AI Assistant and Trusted Companion",
    config: Optional[Dict[str, Any]] = None
) -> NexusMasterAgent:
    """
    Create and initialize a NEXUS Master Agent instance.

    Args:
        name: Agent name
        description: Agent description
        config: Configuration overrides

    Returns:
        Initialized NexusMasterAgent instance
    """
    agent = NexusMasterAgent(
        name=name,
        description=description,
        config=config
    )

    await agent.initialize()
    return agent


# Global NEXUS instance (singleton pattern)
_nexus_instance: Optional[NexusMasterAgent] = None

async def get_nexus_instance() -> NexusMasterAgent:
    """Get or create the global NEXUS instance."""
    global _nexus_instance

    if _nexus_instance is None or _nexus_instance.status == AgentStatus.STOPPED:
        logger.info("Creating global NEXUS instance...")
        _nexus_instance = await create_nexus_master_agent()

    return _nexus_instance

async def shutdown_nexus() -> None:
    """Shutdown the global NEXUS instance."""
    global _nexus_instance

    if _nexus_instance:
        logger.info("Shutting down NEXUS...")
        await _nexus_instance.cleanup()
        _nexus_instance = None