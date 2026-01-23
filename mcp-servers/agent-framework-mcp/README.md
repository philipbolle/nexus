# Agent Framework MCP Server for NEXUS

Provides access to NEXUS agent framework operations through Claude Code MCP tools.

## Features

- **List agents**: Get all registered agents with status and details
- **Agent status**: Check agent metrics and performance
- **Execute tasks**: Submit tasks to agents for execution
- **Agent sessions**: List sessions for specific agents
- **Memory queries**: Query agent memory with natural language
- **System performance**: Get overall system metrics
- **System alerts**: View current system alerts
- **Tool registry**: List registered tools

## Installation

1. Install dependencies:
```bash
cd /home/philip/mcp-servers/agent-framework-mcp
pip install -r requirements.txt
```

2. Ensure NEXUS API is running on `http://localhost:8080` (default)

## Claude Desktop Configuration

Add to `~/.config/Claude/claude_desktop_config.json`:

```json
"agent-framework": {
  "command": "/home/philip/nexus/venv/bin/python",
  "args": ["/home/philip/mcp-servers/agent-framework-mcp/server.py"],
  "env": {
    "NEXUS_API_URL": "http://localhost:8080"
  }
}
```

## Usage Examples

In Claude Code, you can now use agent framework tools:

1. "List all agents in the system"
2. "Get status for agent email-intelligence"
3. "Submit a task to the email agent to scan new emails"
4. "Query the email agent's memory for 'user preferences'"
5. "Check system performance metrics"
6. "List all registered tools"

## Integration with NEXUS

This server connects to the NEXUS FastAPI application (`http://localhost:8080`) and provides MCP access to the agent framework endpoints. It enables Claude Code to interact directly with the agent system for monitoring and task execution.

## Safety Features

- **Read-only by default**: Most operations are read-only
- **Task execution limits**: Tasks go through standard agent framework validation
- **Error handling**: Comprehensive error reporting
- **Timeouts**: 30-second request timeout