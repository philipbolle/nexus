# NEXUS Agent Framework - API Quick Reference

## Base URL
```
http://localhost:8080
```

## Authentication
Currently open (Tailscale network only). Add API key authentication for production.

## Agent Management Endpoints

### List All Agents
```http
GET /agents
```

**Query Parameters:**
- `skip` (int, default: 0) - Number of agents to skip
- `limit` (int, default: 100) - Maximum agents to return (1-1000)
- `active_only` (bool, default: false) - Only return active agents
- `agent_type` (string, optional) - Filter by agent type

**Response:**
```json
{
  "agents": [
    {
      "id": "uuid",
      "name": "Finance Agent",
      "agent_type": "domain",
      "description": "Financial analysis agent",
      "capabilities": ["budgeting", "expense_tracking"],
      "domain": "finance",
      "status": "idle",
      "metrics": {...}
    }
  ],
  "total_count": 5
}
```

### Create Agent
```http
POST /agents
```

**Request Body:**
```json
{
  "name": "Research Assistant",
  "agent_type": "domain",
  "description": "Helps with research tasks",
  "system_prompt": "You are a research assistant...",
  "capabilities": ["research", "summarization"],
  "domain": "research",
  "supervisor_id": "optional-uuid",
  "config": {}
}
```

**Response:** Agent details (201 Created)

### Get Agent Details
```http
GET /agents/{agent_id}
```

**Response:** Agent details

### Update Agent
```http
PUT /agents/{agent_id}
```

**Request Body:** Partial update of agent fields

### Delete Agent
```http
DELETE /agents/{agent_id}
```

**Response:** 204 No Content

### Start Agent
```http
POST /agents/{agent_id}/start
```

**Response:** Updated agent details

### Stop Agent
```http
POST /agents/{agent_id}/stop
```

**Response:** Updated agent details

### Get Agent Status
```http
GET /agents/{agent_id}/status
```

**Response:**
```json
{
  "agent_id": "uuid",
  "status": "idle",
  "is_active": true,
  "current_tasks": 0,
  "total_tasks": 15,
  "success_rate": 0.93,
  "metrics": {...}
}
```

## Registry Endpoints

### Get Registry Status
```http
GET /registry-status
```

**Response:**
```json
{
  "status": "running",
  "total_agents": 5,
  "active_agents": 3,
  "idle_agents": 2,
  "processing_agents": 1,
  "error_agents": 0,
  "capabilities_available": ["research", "finance", "email"],
  "domains_available": ["research", "finance"]
}
```

### Select Agent for Task
```http
POST /registry-select-agent
```

**Request Body:**
```json
{
  "task_description": "Analyze monthly expenses",
  "required_capabilities": ["expense_analysis", "budgeting"],
  "preferred_domain": "finance",
  "exclude_agent_ids": ["uuid-to-exclude"]
}
```

**Response:**
```json
{
  "selected_agent_id": "uuid",
  "selected_agent_name": "Finance Agent",
  "agent_type": "domain",
  "capabilities": ["expense_analysis", "budgeting"],
  "domain": "finance",
  "score": 0.85,
  "alternative_agents": []
}
```

## Task Execution Endpoints

### Submit Task
```http
POST /tasks
```

**Request Body:**
```json
{
  "task": "Analyze monthly expenses and provide recommendations",
  "agent_id": "optional-uuid",
  "session_id": "optional-uuid",
  "context": {"month": "January", "year": 2026},
  "priority": "normal",
  "capabilities": ["expense_analysis"],
  "domain": "finance"
}
```

**Response:** Task submission result

### Get Task Status
```http
GET /tasks/{task_id}
```

**Response:** Task status and result

### Cancel Task
```http
POST /tasks/{task_id}/cancel
```

**Response:** Updated task status

## Session Management Endpoints

### Create Session
```http
POST /sessions
```

**Request Body:**
```json
{
  "title": "Budget Planning Session",
  "session_type": "task",
  "primary_agent_id": "agent-uuid",
  "metadata": {"purpose": "monthly_budget_review"}
}
```

**Response:** Session details (201 Created)

### Get Session Details
```http
GET /sessions/{session_id}
```

**Response:** Session details

### List Sessions
```http
GET /sessions
```

**Query Parameters:**
- `skip` (int, default: 0)
- `limit` (int, default: 100)
- `session_type` (string, optional)
- `active_only` (bool, default: false)

**Response:** List of session summaries

### Add Message to Session
```http
POST /sessions/{session_id}/messages
```

**Request Body:**
```json
{
  "content": "Can you analyze my spending?",
  "role": "user",
  "agent_id": "optional-uuid",
  "parent_message_id": "optional-uuid",
  "tool_calls": {},
  "tool_results": {}
}
```

**Response:** Message details

### Get Session Messages
```http
GET /sessions/{session_id}/messages
```

**Query Parameters:**
- `skip` (int, default: 0)
- `limit` (int, default: 100)

**Response:** List of messages

### End Session
```http
POST /sessions/{session_id}/end
```

**Response:** `{"status": "session_ended"}`

## Tool Management Endpoints

### List Tools
```http
GET /tools
```

**Query Parameters:**
- `enabled_only` (bool, default: true)
- `tool_type` (string, optional)

**Response:** List of tool definitions

### Register Tool
```http
POST /tools
```

**Request Body:**
```json
{
  "name": "calculate_budget",
  "display_name": "Budget Calculator",
  "description": "Calculate budget surplus/deficit",
  "tool_type": "calculation",
  "input_schema": {
    "type": "object",
    "properties": {
      "income": {"type": "number"},
      "expenses": {"type": "number"}
    }
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "surplus": {"type": "number"}
    }
  },
  "requires_confirmation": false
}
```

**Response:** Tool definition (201 Created)

### Execute Tool
```http
POST /tools/execute
```

**Request Body:**
```json
{
  "tool_name": "calculate_budget",
  "agent_id": "optional-uuid",
  "session_id": "optional-uuid",
  "parameters": {
    "income": 5000,
    "expenses": 4200
  }
}
```

**Response:** Tool execution result

## Performance Monitoring Endpoints

### Get Agent Performance
```http
GET /agents/{agent_id}/performance
```

**Query Parameters:**
- `start_date` (string, optional) - YYYY-MM-DD
- `end_date` (string, optional) - YYYY-MM-DD
- `metric` (string, optional) - Specific metric to retrieve

**Response:** List of performance metrics

### Get System Performance
```http
GET /system/performance
```

**Response:** System-wide performance metrics

### Get System Alerts
```http
GET /system/alerts
```

**Query Parameters:**
- `severity` (string, optional) - Filter by severity
- `resolved` (bool, optional) - Filter by resolved status

**Response:** List of alerts

### Delegate Task
```http
POST /agents/{agent_id}/delegate
```

**Request Body:**
```json
{
  "target_agent_id": "target-uuid",
  "task": "Analyze Q4 expenses",
  "context": {"quarter": "Q4", "year": 2025},
  "reason": "Specialized expertise required"
}
```

**Response:** Delegation result

## Memory System Endpoints

### Get Agent Memories
```http
GET /memory/{agent_id}
```

**Query Parameters:**
- `memory_type` (string, optional)
- `limit` (int, default: 50)

**Response:** List of memories

### Query Memory
```http
POST /memory/{agent_id}/query
```

**Request Body:**
```json
{
  "text": "budget planning",
  "limit": 10,
  "threshold": 0.7
}
```

**Response:** List of memory search results

### Store Memory
```http
POST /memory/{agent_id}/store
```

**Request Body:**
```json
{
  "content": "User prefers monthly budget reviews",
  "type": "semantic",
  "metadata": {
    "importance": 0.8,
    "tags": ["preference", "budget"]
  }
}
```

**Response:** `{"memory_id": "uuid", "status": "stored"}`

## Error Reporting Endpoints

### Get Agent Errors
```http
GET /agents/{agent_id}/errors
```

**Query Parameters:**
- `resolved` (bool, optional)
- `severity` (string, optional)

**Response:** List of agent errors

### Resolve Error
```http
POST /agents/{agent_id}/errors/{error_id}/resolve
```

**Response:** `{"status": "resolved"}`

## Python Client Examples

### Basic Client Class
```python
import httpx
import asyncio
from typing import Dict, Any, List

class NexusAgentClient:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url)

    async def list_agents(self, **params) -> List[Dict]:
        response = await self.client.get("/agents", params=params)
        return response.json()["agents"]

    async def create_agent(self, agent_data: Dict) -> Dict:
        response = await self.client.post("/agents", json=agent_data)
        return response.json()

    async def submit_task(self, task_data: Dict) -> Dict:
        response = await self.client.post("/tasks", json=task_data)
        return response.json()

    async def create_session(self, session_data: Dict) -> Dict:
        response = await self.client.post("/sessions", json=session_data)
        return response.json()

    async def close(self):
        await self.client.aclose()

# Usage example
async def example_usage():
    client = NexusAgentClient()

    # List agents
    agents = await client.list_agents(active_only=True)
    print(f"Active agents: {len(agents)}")

    # Create a session
    session = await client.create_session({
        "title": "Test Session",
        "session_type": "chat"
    })
    print(f"Created session: {session['id']}")

    await client.close()

asyncio.run(example_usage())
```

### Complete Workflow Example
```python
async def complete_workflow():
    client = NexusAgentClient()

    # 1. Select agent for task
    selection = await client.client.post("/registry-select-agent", json={
        "task_description": "Research AI trends in 2026",
        "required_capabilities": ["research", "analysis"],
        "preferred_domain": "technology"
    })
    agent_id = selection.json()["selected_agent_id"]

    # 2. Create session
    session = await client.create_session({
        "title": "AI Trends Research",
        "session_type": "task",
        "primary_agent_id": agent_id
    })
    session_id = session["id"]

    # 3. Submit task
    task = await client.submit_task({
        "task": "Research and summarize key AI trends for 2026",
        "agent_id": agent_id,
        "session_id": session_id,
        "context": {"depth": "detailed", "sources": "recent"}
    })

    # 4. Store result in memory
    if task.get("success"):
        await client.client.post(f"/memory/{agent_id}/store", json={
            "content": task["result"]["response"],
            "type": "semantic",
            "metadata": {
                "session_id": session_id,
                "topic": "ai_trends_2026"
            }
        })

    await client.close()
```

## Common Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 404 Not Found
```json
{
  "detail": "Agent not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Testing with curl

### Quick Test Commands
```bash
# Test registry status
curl -s "http://localhost:8080/registry-status" | jq .

# List all agents
curl -s "http://localhost:8080/agents" | jq '.agents[].name'

# Create test agent
curl -X POST "http://localhost:8080/agents" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Agent", "agent_type": "domain", "description": "Test"}' \
  | jq .

# Test memory system
curl -s "http://localhost:8080/memory/system/query" \
  -H "Content-Type: application/json" \
  -d '{"text": "test query", "limit": 5}' \
  | jq .
```

## Monitoring and Debugging

### Check System Health
```bash
# Check if API is running
curl -s "http://localhost:8080/health" | jq .

# Check system performance
curl -s "http://localhost:8080/system/performance" | jq .

# Check for alerts
curl -s "http://localhost:8080/system/alerts" | jq .
```

### View Logs
```bash
# View API logs
journalctl -u nexus-api -f

# View specific agent logs
journalctl -u nexus-api | grep "Agent.*Finance"
```

## Best Practices for API Usage

1. **Use Async Clients**: Always use async HTTP clients (httpx, aiohttp)
2. **Handle Errors**: Implement proper error handling for network issues
3. **Close Connections**: Always close HTTP clients when done
4. **Use Pagination**: For large lists, use skip/limit parameters
5. **Monitor Rate Limits**: Be mindful of API rate limits (if implemented)
6. **Cache Responses**: Cache static data like agent lists
7. **Validate Inputs**: Validate data before sending to API
8. **Use Timeouts**: Set appropriate timeouts for all requests

## Integration Examples

### Integration with Existing Services
```python
async def integrate_with_email():
    """Example of integrating agent framework with email service."""
    client = NexusAgentClient()

    # Get email agent
    agents = await client.list_agents(agent_type="email_intelligence")
    if agents:
        email_agent = agents[0]

        # Submit email processing task
        task = await client.submit_task({
            "task": "Process unread emails and extract important information",
            "agent_id": email_agent["id"],
            "priority": "high"
        })

        # Store results in memory
        if task["success"]:
            await client.client.post(f"/memory/{email_agent['id']}/store", json={
                "content": f"Email processing completed: {task['result']}",
                "type": "episodic",
                "metadata": {"task_type": "email_processing"}
            })

    await client.close()
```

This quick reference provides all the essential information for working with the NEXUS Agent Framework API. For more detailed examples and comprehensive documentation, refer to the complete agent framework documentation.