# PostgreSQL MCP Server for NEXUS

Provides read-only access to NEXUS PostgreSQL database for schema inspection and queries through Claude Code.

## Features

- **List tables**: List all 193 tables in nexus_db
- **Describe table**: Show table schema with columns, types, constraints
- **Execute queries**: Run SELECT queries safely (read-only, limited to 1000 rows)
- **Table statistics**: Get row counts and size information
- **Schema search**: Search for tables and columns by name pattern

## Installation

1. Install dependencies:
```bash
cd /home/philip/mcp-servers/postgres-mcp
pip install -r requirements.txt
```

2. Ensure PostgreSQL credentials are available in environment or `.env` file:
```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=nexus
POSTGRES_PASSWORD=your_password
POSTGRES_DB=nexus_db
```

## Claude Desktop Configuration

Add to `~/.config/Claude/claude_desktop_config.json`:

```json
"postgres": {
  "command": "/home/philip/nexus/venv/bin/python",
  "args": ["/home/philip/mcp-servers/postgres-mcp/server.py"],
  "env": {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "nexus_db",
    "POSTGRES_USER": "nexus",
    "POSTGRES_PASSWORD": "from .env file"
  }
}
```

## Usage Examples

In Claude Code, you can now use PostgreSQL tools:

1. "List all tables in the database"
2. "Describe the api_usage table"
3. "Show me the first 5 rows from api_usage"
4. "Get statistics for the fin_expenses table"
5. "Search for tables containing 'agent'"

## Safety Features

- **Read-only access**: Only SELECT queries allowed
- **Row limits**: Queries limited to 1000 rows
- **Query validation**: Rejects non-SELECT queries
- **Connection pooling**: Efficient resource usage
- **Timeouts**: 30-second command timeout

## Integration with NEXUS

This server reuses the same PostgreSQL credentials as the NEXUS FastAPI application and provides schema introspection capabilities that DeepSeek models need for accurate database queries.