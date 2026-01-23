# NEXUS Multi-Agent Framework - Complete Documentation

## Overview

The NEXUS Multi-Agent Framework provides a comprehensive system for creating, managing, and orchestrating AI agents. This framework enables hierarchical agent coordination, persistent memory, session management, and performance monitoring. It's designed to be extensible, scalable, and integrated with existing NEXUS services.

**Status**: ✅ **Fully Implemented and Tested** (Phase 1 fixes completed 2026-01-22)

## Architecture

The agent framework consists of 6 core components:

1. **Base Agent System** (`app/agents/base.py`) - Abstract base classes for all agents
2. **Agent Registry** (`app/agents/registry.py`) - Central registry for agent discovery and lifecycle management
3. **Memory System** (`app/agents/memory.py`) - Vector memory with ChromaDB + PostgreSQL integration
4. **Session Management** (`app/agents/sessions.py`) - Session creation, message tracking, cost attribution
5. **Performance Monitoring** (`app/agents/monitoring.py`) - Metrics collection, cost tracking, alerting
6. **API Endpoints** (`app/routers/agents.py`) - 31 RESTful endpoints for agent management

## Core Concepts

### Agent Types
The framework supports multiple agent types through the `AgentType` enum:
- **DOMAIN**: Specialized agents (finance, health, email, etc.)
- **EMAIL_INTELLIGENCE**: Email processing orchestrator
- **ORCHESTRATOR**: Coordinates multiple agents
- **SUPERVISOR**: Manages subordinate agents
- **WORKER**: Task-specific agents
- **ANALYZER**: Analysis and insight generation
- **DECISION_SUPPORT**: Decision support and analysis
- **CODE_REVIEW**: Code review and quality assurance

### Agent Lifecycle
Agents follow a defined lifecycle with `AgentStatus` states:
- `CREATED` → `INITIALIZING` → `IDLE` → `PROCESSING` → `WAITING_FOR_TOOL` → `IDLE`
- Error handling: `ERROR` state with automatic recovery attempts
- Clean shutdown: `STOPPED` state with resource cleanup

## Component Details

### 1. Base Agent System (`app/agents/base.py`)

**Key Classes:**
- `BaseAgent`: Abstract base class with lifecycle management, tool integration, and AI request handling
- `DomainAgent`: Specialized agent for specific domains (finance, health, email, etc.)
- `OrchestratorAgent`: Coordinates multiple agents for complex tasks

**Core Features:**
- **Lifecycle Management**: `initialize()`, `execute()`, `cleanup()` methods
- **Tool Integration**: Register and execute tools with schema validation
- **AI Integration**: Agent-specific AI requests with context injection
- **Delegation**: Task delegation to other agents with handoff tracking
- **Error Handling**: Automatic error logging and recovery attempts
- **Metrics Tracking**: Performance metrics with database persistence

**Example: Creating a Custom Agent**
```python
from app.agents.base import DomainAgent, AgentType
from app.agents.registry import registry

class FinanceAgent(DomainAgent):
    """Specialized agent for financial tasks."""

    async def _on_initialize(self):
        """Load financial tools and knowledge."""
        await self.register_tool("calculate_budget", self._calculate_budget)
        await self.register_tool("analyze_expenses", self._analyze_expenses)

    async def _process_task(self, task, context):
        """Process financial tasks."""
        # Use AI with financial context
        response = await self._ai_request(
            prompt=task,
            task_type="analysis",
            system_prompt="You are a financial expert agent. Analyze budgets, expenses, and provide recommendations."
        )
        return {"response": response["content"], "domain": "finance"}

    async def _calculate_budget(self, income: float, expenses: float) -> Dict[str, Any]:
        """Calculate budget surplus/deficit."""
        surplus = income - expenses
        return {"income": income, "expenses": expenses, "surplus": surplus, "deficit": -surplus if surplus < 0 else 0}

    async def _analyze_expenses(self, expenses: List[Dict]) -> Dict[str, Any]:
        """Analyze expense patterns."""
        # Implementation here
        return {"analysis": "Expense analysis result"}

# Create and register the agent
async def create_finance_agent():
    agent = FinanceAgent(
        name="Finance Expert",
        agent_type=AgentType.DOMAIN,
        domain="finance",
        description="Specialized agent for financial analysis and budgeting",
        capabilities=["budget_calculation", "expense_analysis", "financial_planning"]
    )
    await agent.initialize()
    return agent
```

### 2. Agent Registry (`app/agents/registry.py`)

**Singleton Pattern:** `AgentRegistry` provides global access to all agents.

**Key Features:**
- **Agent Discovery**: Find agents by ID, name, capabilities, or domain
- **Lifecycle Management**: Create, update, delete agents with database persistence
- **Capability Matching**: Intelligent agent selection for tasks
- **Load Balancing**: Distribute tasks among idle agents
- **Database Integration**: Automatic loading/saving of agent configurations

**Example: Using the Registry**
```python
from app.agents.registry import registry

# Initialize the registry (automatically loads agents from database)
await registry.initialize()

# Create a new agent
agent = await registry.create_agent(
    agent_type="domain",
    name="Research Assistant",
    description="Helps with research and analysis",
    capabilities=["research", "summarization", "analysis"],
    domain="research"
)

# Find agents by capability
research_agents = await registry.find_agents_by_capability("research")

# Select best agent for a task
selected_agent, score = await registry.select_agent_for_task(
    task_description="Research quantum computing trends",
    required_capabilities=["research", "analysis"],
    preferred_domain="technology"
)

# Get registry status
status = await registry.get_registry_status()
print(f"Total agents: {status['total_agents']}, Active: {status['active_agents']}")
```

### 3. Memory System (`app/agents/memory.py`)

**Dual Storage:** Combines ChromaDB (vector similarity) with PostgreSQL (structured storage).

**Memory Types:**
- `SEMANTIC`: Facts and knowledge (stored as subject-predicate-object triples)
- `EPISODIC`: Experiences and events (linked to sessions)
- `PROCEDURAL`: Skills and how-to knowledge
- `WORKING`: Short-term/context memory

**Key Features:**
- **Semantic Search**: Vector-based similarity search with embeddings
- **Memory Consolidation**: Automatic summarization, clustering, and pruning
- **Agent Isolation**: Namespaced memories per agent
- **Memory Blocks**: In-context memory for agent persona, task context, etc.
- **Automatic Cleanup**: Expiration of low-importance memories

**Example: Using the Memory System**
```python
from app.agents.memory import memory_system, MemoryType

# Initialize the memory system
await memory_system.initialize()

# Store a memory
memory_id = await memory_system.store_memory(
    agent_id="finance_agent_123",
    content="User prefers monthly budget reviews on the 15th",
    memory_type=MemoryType.SEMANTIC,
    importance_score=0.8,
    tags=["preference", "budget", "schedule"],
    metadata={"source": "conversation", "confidence": 0.9}
)

# Query memories with semantic search
results = await memory_system.query_memory(
    agent_id="finance_agent_123",
    query_text="When does the user want budget reviews?",
    limit=5,
    similarity_threshold=0.7
)

# Get memory blocks (in-context memory)
persona_block = await memory_system.get_memory_block(
    agent_id="finance_agent_123",
    block_label="persona"
)

# Update memory block
await memory_system.update_memory_block(
    agent_id="finance_agent_123",
    block_label="task",
    content="Current task: Analyze Q4 expenses and project Q1 budget",
    priority=30  # Lower number = higher priority
)
```

### 4. Session Management (`app/agents/sessions.py`)

**Session Types:**
- `CHAT`: Interactive conversation
- `TASK`: Task execution
- `AUTOMATION`: Automated workflow
- `COLLABORATION`: Multi-agent collaboration
- `ANALYSIS`: Data analysis session

**Key Features:**
- **Message History**: Complete conversation history with tool call attribution
- **Cost Tracking**: Per-session and per-agent cost breakdown
- **Context Management**: Session-specific context and state
- **Automatic Summarization**: AI-generated session summaries
- **Analytics**: Topic extraction, sentiment analysis, engagement metrics

**Example: Session Management**
```python
from app.agents.sessions import session_manager, SessionConfig, SessionType

# Create a session
session_id = await session_manager.create_session(
    title="Budget Planning Session",
    session_type=SessionType.TASK,
    primary_agent_id="finance_agent_123",
    config=SessionConfig(
        max_messages=200,
        max_duration_hours=2,
        enable_cost_tracking=True,
        auto_generate_summary=True
    )
)

# Add messages to session
message_id = await session_manager.add_message(
    session_id=session_id,
    role="user",
    content="Can you analyze my spending from last month?",
    agent_id=None,  # User message
    tokens_input=15,
    tokens_output=0
)

# Add agent response
response_id = await session_manager.add_message(
    session_id=session_id,
    role="assistant",
    content="I've analyzed your spending. You spent $1,200 last month, which is 20% over budget.",
    agent_id="finance_agent_123",
    parent_message_id=message_id,
    tokens_input=0,
    tokens_output=45,
    cost_usd=0.00045
)

# Get session analytics
analytics = await session_manager.get_session_analytics(session_id)
print(f"Topics: {analytics.get('topics', [])}")
print(f"Sentiment: {analytics.get('sentiment', {})}")

# End session with AI summary
await session_manager.end_session(
    session_id=session_id,
    status=SessionStatus.COMPLETED
)
```

### 5. Performance Monitoring (`app/agents/monitoring.py`)

**Metric Types:**
- `LATENCY`: Execution time in milliseconds
- `COST`: USD cost per execution
- `SUCCESS_RATE`: Percentage of successful executions
- `TOKEN_USAGE`: Input/output tokens
- `TOOL_USAGE`: Tool invocation counts
- `ERROR_RATE`: Failure percentage

**Key Features:**
- **Real-time Metrics**: Continuous metric collection with buffering
- **Anomaly Detection**: Automatic alerting for high latency, failure rates, cost overruns
- **Cost Reporting**: Detailed cost breakdown by agent, model, and time period
- **Alert System**: Configurable alerts with severity levels
- **Performance Dashboards**: System-wide and agent-specific performance views

**Example: Performance Monitoring**
```python
from app.agents.monitoring import performance_monitor, MetricType, AlertSeverity

# Initialize with registry
await performance_monitor.initialize(agent_registry)

# Record agent execution metrics
await performance_monitor.record_agent_execution(
    agent_id="finance_agent_123",
    success=True,
    execution_time_ms=1250,
    tokens_used=245,
    cost_usd=0.00245,
    tools_used=["calculate_budget", "analyze_expenses"]
)

# Record custom metric
await performance_monitor.record_metric(
    agent_id="finance_agent_123",
    metric_type=MetricType.LATENCY,
    value=1250.5,
    tags={"task_type": "budget_analysis", "complexity": "high"}
)

# Create alert for high latency
alert_id = await performance_monitor.create_alert(
    title="High latency for finance agent",
    message="Finance agent execution took 12.5 seconds, exceeding 10s threshold",
    severity=AlertSeverity.WARNING,
    source="agent",
    source_id="finance_agent_123",
    metadata={"execution_time_ms": 12500, "threshold": 10000}
)

# Get performance reports
agent_perf = await performance_monitor.get_agent_performance(
    agent_id="finance_agent_123",
    time_range_hours=24
)

system_perf = await performance_monitor.get_system_performance(
    time_range_hours=24
)

cost_report = await performance_monitor.get_cost_report()
```

## API Endpoints Reference

The agent framework exposes 31 RESTful endpoints through `app/routers/agents.py`:

### Agent Management (8 endpoints)
- `GET /agents` - List all agents with filtering
- `POST /agents` - Create new agent
- `GET /agents/{agent_id}` - Get agent details
- `PUT /agents/{agent_id}` - Update agent configuration
- `DELETE /agents/{agent_id}` - Delete agent (soft delete)
- `POST /agents/{agent_id}/start` - Start agent
- `POST /agents/{agent_id}/stop` - Stop agent
- `GET /agents/{agent_id}/status` - Get agent status and metrics

### Registry & Selection (2 endpoints)
- `GET /registry-status` - Get registry status and statistics
- `POST /registry-select-agent` - Select best agent for a task

### Task Execution (3 endpoints)
- `POST /tasks` - Submit task for execution
- `GET /tasks/{task_id}` - Get task status
- `POST /tasks/{task_id}/cancel` - Cancel running task

### Session Management (6 endpoints)
- `POST /sessions` - Create new session
- `GET /sessions/{session_id}` - Get session details
- `GET /sessions` - List all sessions
- `POST /sessions/{session_id}/messages` - Add message to session
- `GET /sessions/{session_id}/messages` - Get session messages
- `POST /sessions/{session_id}/end` - End session

### Tool Management (3 endpoints)
- `GET /tools` - List registered tools
- `POST /tools` - Register new tool
- `POST /tools/execute` - Execute tool directly

### Performance Monitoring (4 endpoints)
- `GET /agents/{agent_id}/performance` - Get agent performance metrics
- `GET /system/performance` - Get system performance metrics
- `GET /system/alerts` - Get system alerts
- `POST /agents/{agent_id}/delegate` - Delegate task to another agent

### Memory System (3 endpoints)
- `GET /memory/{agent_id}` - Get agent memories
- `POST /memory/{agent_id}/query` - Query agent memory with semantic search
- `POST /memory/{agent_id}/store` - Store new memory

### Error Reporting (2 endpoints)
- `GET /agents/{agent_id}/errors` - Get agent errors
- `POST /agents/{agent_id}/errors/{error_id}/resolve` - Resolve agent error

## Practical Examples

### Example 1: Complete Agent Workflow
```python
import asyncio
from app.agents.registry import registry
from app.agents.sessions import session_manager
from app.agents.memory import memory_system

async def complete_agent_workflow():
    """Complete example showing agent creation, task execution, and memory storage."""

    # 1. Create or get agent
    agent = await registry.get_agent_by_name("Research Assistant")
    if not agent:
        agent = await registry.create_agent(
            agent_type="domain",
            name="Research Assistant",
            domain="research",
            capabilities=["research", "summarization", "analysis"]
        )

    # 2. Create session
    session_id = await session_manager.create_session(
        title="Research quantum computing",
        primary_agent_id=agent.agent_id
    )

    # 3. Execute task
    result = await agent.execute(
        task="Research current trends in quantum computing and summarize key findings",
        session_id=session_id,
        context={"urgency": "medium", "depth": "detailed"}
    )

    # 4. Store key findings in memory
    if result.get("success"):
        await memory_system.store_memory(
            agent_id=agent.agent_id,
            content=result["result"].get("response", ""),
            memory_type=MemoryType.SEMANTIC,
            importance_score=0.7,
            tags=["quantum_computing", "research", "trends"],
            metadata={
                "session_id": session_id,
                "task_type": "research",
                "confidence": 0.8
            }
        )

    # 5. End session
    await session_manager.end_session(session_id)

    return result

# Run the workflow
result = asyncio.run(complete_agent_workflow())
```

### Example 2: Multi-Agent Collaboration
```python
async def multi_agent_collaboration():
    """Example of multiple agents collaborating on a complex task."""

    # Get specialized agents
    research_agent = await registry.get_agent_by_name("Research Assistant")
    analysis_agent = await registry.get_agent_by_name("Data Analyst")
    writing_agent = await registry.get_agent_by_name("Content Writer")

    # Create collaboration session
    session_id = await session_manager.create_session(
        title="Market Analysis Report",
        session_type=SessionType.COLLABORATION
    )

    # Add all agents to session
    for agent in [research_agent, analysis_agent, writing_agent]:
        await session_manager.add_agent_to_session(session_id, agent.agent_id)

    # Research phase
    research_result = await research_agent.execute(
        task="Research current market trends in renewable energy",
        session_id=session_id
    )

    # Analysis phase
    analysis_result = await analysis_agent.execute(
        task=f"Analyze this research data: {research_result['result']['response']}",
        session_id=session_id,
        context={"research_data": research_result}
    )

    # Writing phase
    report_result = await writing_agent.execute(
        task=f"Write a comprehensive market analysis report based on: {analysis_result['result']['response']}",
        session_id=session_id,
        context={"research": research_result, "analysis": analysis_result}
    )

    # Store final report in memory
    await memory_system.store_memory(
        agent_id=writing_agent.agent_id,
        content=report_result["result"]["response"],
        memory_type=MemoryType.SEMANTIC,
        importance_score=0.9,
        tags=["market_analysis", "renewable_energy", "report"],
        metadata={
            "session_id": session_id,
            "collaborating_agents": [a.agent_id for a in [research_agent, analysis_agent, writing_agent]],
            "report_type": "market_analysis"
        }
    )

    return report_result
```

### Example 3: Agent with Custom Tools
```python
from app.agents.base import DomainAgent
from app.agents.tools import tool_system

class CustomAgent(DomainAgent):
    """Agent with custom tools for specific tasks."""

    async def _on_initialize(self):
        """Register custom tools."""
        await self.register_tool(
            name="fetch_weather",
            tool_func=self._fetch_weather,
            schema={
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"},
                    "days": {"type": "integer", "description": "Forecast days", "default": 3}
                },
                "required": ["location"]
            }
        )

        await self.register_tool(
            name="calculate_metrics",
            tool_func=self._calculate_metrics,
            schema={
                "type": "object",
                "properties": {
                    "data": {"type": "array", "items": {"type": "number"}},
                    "metric": {"type": "string", "enum": ["mean", "median", "stddev"]}
                },
                "required": ["data", "metric"]
            }
        )

    async def _fetch_weather(self, location: str, days: int = 3) -> Dict[str, Any]:
        """Fetch weather data (example implementation)."""
        # In production, this would call a weather API
        return {
            "location": location,
            "forecast": f"Sunny for {days} days",
            "temperature": "72°F",
            "source": "simulated"
        }

    async def _calculate_metrics(self, data: List[float], metric: str) -> Dict[str, Any]:
        """Calculate statistical metrics."""
        import statistics
        if metric == "mean":
            result = statistics.mean(data)
        elif metric == "median":
            result = statistics.median(data)
        elif metric == "stddev":
            result = statistics.stdev(data) if len(data) > 1 else 0

        return {"metric": metric, "result": result, "data_points": len(data)}

# Register tool globally (optional)
async def register_custom_tools():
    """Register custom tools in the global tool system."""
    agent = CustomAgent(name="Tool Expert")
    await agent.initialize()

    # Tools are automatically registered via agent._register_tool_in_db()
    # They can also be accessed through the global tool system
    tools = await tool_system.list_tools()
    print(f"Available tools: {[t['name'] for t in tools]}")
```

## Database Schema

The agent framework uses dedicated PostgreSQL tables:

### Core Tables
- **agents**: Agent definitions and configurations
- **agent_tools**: Tool definitions and schemas
- **agent_tool_assignments**: Agent-tool relationships
- **sessions**: Session metadata and state
- **messages**: Message history with cost attribution
- **memories**: Agent memories with vector embeddings
- **agent_performance**: Daily performance metrics
- **agent_performance_metrics**: Detailed metric measurements
- **system_alerts**: System alerts and notifications

### Memory Tables
- **semantic_memories**: Factual knowledge (subject-predicate-object)
- **episodic_memories**: Experience records
- **procedural_memories**: Skill definitions
- **memory_blocks**: In-context memory blocks
- **memory_consolidation_jobs**: Memory maintenance jobs

## Best Practices

### 1. Agent Design
- Keep agents focused on specific domains or capabilities
- Implement comprehensive error handling
- Use meaningful agent names and descriptions
- Document agent capabilities and limitations

### 2. Memory Management
- Use appropriate memory types for different information
- Set realistic importance scores for memories
- Tag memories for better organization
- Regularly review and prune old memories

### 3. Session Management
- Create sessions for logically related conversations
- Use appropriate session types (chat, task, collaboration)
- Enable cost tracking for budget monitoring
- Review session analytics for insights

### 4. Performance Monitoring
- Monitor key metrics: latency, success rate, cost
- Set up alerts for critical thresholds
- Regularly review cost reports
- Use performance data to optimize agent configurations

### 5. Tool Development
- Define clear input/output schemas for tools
- Implement comprehensive error handling in tools
- Document tool purpose and usage
- Test tools thoroughly before deployment

## Testing and Debugging

### Testing Agents
```python
import pytest
from unittest.mock import AsyncMock, patch
from app.agents.base import DomainAgent

@pytest.mark.asyncio
async def test_agent_execution():
    """Test agent task execution."""
    agent = DomainAgent(name="Test Agent", domain="test")
    await agent.initialize()

    # Mock AI response
    with patch.object(agent, '_ai_request', return_value={"content": "Test response"}):
        result = await agent.execute("Test task")

        assert result["success"] == True
        assert "Test response" in str(result["result"])
        assert agent.status.value == "idle"

@pytest.mark.asyncio
async def test_agent_tool_execution():
    """Test agent tool execution."""
    agent = DomainAgent(name="Test Agent", domain="test")
    await agent.initialize()

    # Register test tool
    mock_tool = AsyncMock(return_value={"result": "success"})
    await agent.register_tool("test_tool", mock_tool)

    # Execute tool
    result = await agent.execute_tool("test_tool", param1="value1")

    assert result == {"result": "success"}
    mock_tool.assert_called_once_with(param1="value1")
```

### Debugging Tips
1. **Check Agent Status**: Use `GET /agents/{agent_id}/status` endpoint
2. **Review Session Logs**: Examine session messages for errors
3. **Monitor Performance**: Check metrics for anomalies
4. **Inspect Memory**: Query agent memory for context issues
5. **Enable Detailed Logging**: Set log level to DEBUG for troubleshooting

## Common Patterns

### Pattern 1: Agent Factory
```python
class AgentFactory:
    """Factory for creating specialized agents."""

    @staticmethod
    async def create_finance_agent(name: str = "Finance Expert") -> DomainAgent:
        """Create a finance agent with standard configuration."""
        agent = DomainAgent(
            name=name,
            domain="finance",
            agent_type=AgentType.DOMAIN,
            description="Specialized agent for financial analysis",
            capabilities=["budgeting", "expense_tracking", "financial_planning"],
            system_prompt="You are a financial expert. Provide accurate, helpful financial advice."
        )
        await agent.initialize()
        return agent

    @staticmethod
    async def create_research_agent(name: str = "Research Assistant") -> DomainAgent:
        """Create a research agent with standard configuration."""
        agent = DomainAgent(
            name=name,
            domain="research",
            agent_type=AgentType.DOMAIN,
            description="Specialized agent for research and analysis",
            capabilities=["research", "summarization", "analysis", "sourcing"],
            system_prompt="You are a research assistant. Provide thorough, well-sourced information."
        )
        await agent.initialize()
        return agent
```

### Pattern 2: Agent Coordinator
```python
class AgentCoordinator:
    """Coordinates multiple agents for complex workflows."""

    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.workflow_agents = {}

    async def setup_research_workflow(self, topic: str) -> Dict[str, Any]:
        """Set up a research workflow with multiple agents."""
        # Get or create agents
        researcher = await self.registry.get_agent_by_name("Research Assistant")
        analyst = await self.registry.get_agent_by_name("Data Analyst")
        writer = await self.registry.get_agent_by_name("Content Writer")

        # Create workflow session
        from app.agents.sessions import session_manager
        session_id = await session_manager.create_session(
            title=f"Research: {topic}",
            session_type=SessionType.COLLABORATION
        )

        # Store workflow state
        self.workflow_agents[session_id] = {
            "researcher": researcher,
            "analyst": analyst,
            "writer": writer,
            "topic": topic,
            "phase": "research"
        }

        return {
            "session_id": session_id,
            "agents": [researcher.agent_id, analyst.agent_id, writer.agent_id],
            "workflow": "research_analysis_writing"
        }
```

## Integration with Existing Services

The agent framework integrates seamlessly with existing NEXUS services:

### 1. AI Service Integration
- **Cost Cascade**: Agents use `app.services.ai.chat()` for AI calls with cost optimization
- **Semantic Caching**: Automatic caching via `app.services.semantic_cache` (0.92 similarity threshold)
- **Provider Routing**: Groq → DeepSeek → Gemini → OpenRouter → Anthropic cascade

### 2. Database Integration
- **Connection Pooling**: Uses shared `app.database.db` asyncpg connection pool
- **Schema Alignment**: All tables follow NEXUS conventions (UUID primary keys, timestamps)
- **Transaction Management**: Proper async transaction handling

### 3. Email Intelligence Integration
- **Backward Compatibility**: `EmailIntelligenceAgent` maintains existing email API endpoints
- **Service Reuse**: Uses existing `app.services.email_client`, `app.services.email_learner`
- **Unified Interface**: Same `/email/*` endpoints work with both old and new implementations

### 4. Memory System Integration
- **ChromaDB**: Vector storage for semantic memory
- **PostgreSQL**: Structured memory metadata and relations
- **Embeddings**: Uses `app.services.embeddings` for text embeddings

### 5. Monitoring Integration
- **API Usage**: All AI calls logged to `api_usage` table
- **Cost Tracking**: Session-based cost attribution
- **Performance Metrics**: Integrated with existing monitoring infrastructure

## Next Steps

1. **Create Specialized Agents**: Implement domain-specific agents (finance, health, email, etc.)
2. **Integrate with Existing Services**: Connect agents to email, finance, and automation systems
3. **Implement Advanced Orchestration**: Add complex workflow and decision-making logic
4. **Enhance Memory System**: Improve memory consolidation and knowledge graph integration
5. **Add User Interface**: Create web interface for agent management and monitoring

## Troubleshooting Common Issues

### Issue 1: Agent Not Found in Registry
**Symptoms**: `Agent not found` error when trying to access agent
**Solution**:
```python
# Check if agent exists in database
agent_data = await db.fetch_one("SELECT id FROM agents WHERE name = $1", "Agent Name")
if agent_data:
    # Agent exists in database but not in registry
    # Force registry to reload from database
    await registry._load_agents_from_db()
```

### Issue 2: Memory Query Returns No Results
**Symptoms**: Memory queries return empty results even when memories exist
**Solution**:
```python
# Check memory system status
await memory_system.initialize()  # Ensure initialized

# Check if ChromaDB is accessible
if not memory_system.use_chromadb:
    print("ChromaDB not available, using PostgreSQL-only mode")

# Try lower similarity threshold
results = await memory_system.query_memory(
    agent_id=agent_id,
    query_text="your query",
    similarity_threshold=0.5  # Lower threshold
)
```

### Issue 3: Session Messages Not Saving
**Symptoms**: Messages added to session don't appear in database
**Solution**:
```python
# Check session status
session = await session_manager.get_session(session_id)
if not session:
    print("Session not found or not active")

# Check database connection
try:
    test = await db.fetch_one("SELECT 1")
    print("Database connection OK")
except Exception as e:
    print(f"Database connection error: {e}")
```

## API Testing Examples

### Using curl to Test Endpoints
```bash
# List all agents
curl -X GET "http://localhost:8080/agents"

# Create a new agent
curl -X POST "http://localhost:8080/agents" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Agent",
    "agent_type": "domain",
    "description": "Test agent for documentation",
    "capabilities": ["testing", "documentation"],
    "domain": "testing"
  }'

# Submit a task
curl -X POST "http://localhost:8080/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Test task description",
    "agent_id": "agent-uuid-here"
  }'
```

### Using Python to Test API
```python
import httpx
import asyncio

async def test_agent_api():
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        # Test registry status
        response = await client.get("/registry-status")
        print(f"Registry status: {response.json()}")

        # Create a session
        session_data = {
            "title": "Test Session",
            "session_type": "chat",
            "primary_agent_id": "agent-uuid-here"
        }
        response = await client.post("/sessions", json=session_data)
        session_id = response.json()["id"]
        print(f"Created session: {session_id}")

        # Add message to session
        message_data = {
            "content": "Hello, agent!",
            "role": "user"
        }
        response = await client.post(f"/sessions/{session_id}/messages", json=message_data)
        print(f"Added message: {response.json()}")

asyncio.run(test_agent_api())
```

## Conclusion

The NEXUS Multi-Agent Framework provides a robust, scalable foundation for building intelligent agent systems. With comprehensive lifecycle management, persistent memory, session tracking, and performance monitoring, it enables complex multi-agent workflows while maintaining simplicity and ease of use.

The framework is fully integrated with existing NEXUS services and follows established conventions for async Python development, database design, and API structure. It's designed to be extensible, allowing for the creation of specialized agents for any domain or task.

For further assistance or to report issues, refer to the main CLAUDE.md documentation or test the system using the provided test scripts.