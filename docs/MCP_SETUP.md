# MCP (Model Context Protocol) Setup for DeepSeek Optimization

## Overview
MCP servers bridge the knowledge gap between DeepSeek models and your local environment, providing direct access to databases, filesystems, and reasoning tools. This is **essential** for DeepSeek's slightly lower "world knowledge" compared to Claude Opus.

## Recommended MCP Servers for NEXUS

### 1. Sequential Thinking MCP
**Purpose**: Forces DeepSeek to use private "thought blocks" for complex reasoning before writing code.

**Installation**:
```bash
# Install via npm (if available)
npm install -g @modelcontextprotocol/server-thinking

# Or clone from GitHub
git clone https://github.com/modelcontextprotocol/servers
cd servers/thinking
npm install
npm run build
```

**Claude Desktop Configuration** (`~/.config/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "thinking": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-thinking"]
    }
  }
}
```

### 2. Postgres MCP Server
**Purpose**: Direct database schema queries without guessing.

**Installation**:
```bash
# Using the official PostgreSQL MCP server
git clone https://github.com/modelcontextprotocol/servers
cd servers/postgres
npm install
```

**Configuration** (update connection details for NEXUS):
```json
{
  "mcpServers": {
    "postgres": {
      "command": "node",
      "args": ["/path/to/servers/postgres/dist/index.js"],
      "env": {
        "PGHOST": "localhost",
        "PGPORT": "5432",
        "PGDATABASE": "nexus_db",
        "PGUSER": "nexus",
        "PGPASSWORD": "from .env"
      }
    }
  }
}
```

### 3. Filesystem MCP
**Purpose**: Accurate file operations and directory navigation.

**Installation**:
```bash
# Official filesystem server
git clone https://github.com/modelcontextprotocol/servers
cd servers/filesystem
npm install
npm run build
```

**Configuration**:
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "node",
      "args": ["/path/to/servers/filesystem/dist/index.js"],
      "env": {
        "ALLOWED_PATHS": ["/home/philip/nexus"]
      }
    }
  }
}
```

### 4. Fetch MCP (HTTP Client)
**Purpose**: Make HTTP requests to test API endpoints.

**Installation**:
```bash
git clone https://github.com/modelcontextprotocol/servers
cd servers/fetch
npm install
npm run build
```

**Configuration**:
```json
{
  "mcpServers": {
    "fetch": {
      "command": "node",
      "args": ["/path/to/servers/fetch/dist/index.js"]
    }
  }
}
```

## Quick Setup Script

Create `scripts/setup_mcp_servers.sh`:

```bash
#!/bin/bash
# NEXUS MCP Server Setup Script

set -e

echo "🚀 Setting up MCP servers for DeepSeek optimization..."

# Create servers directory
mkdir -p ~/mcp-servers
cd ~/mcp-servers

# Clone official MCP servers
if [ ! -d "servers" ]; then
    echo "📦 Cloning official MCP servers..."
    git clone https://github.com/modelcontextprotocol/servers.git
fi

# Install thinking server
echo "🤔 Installing Sequential Thinking MCP..."
cd servers/thinking
npm install
npm run build

# Install filesystem server
echo "📁 Installing Filesystem MCP..."
cd ../filesystem
npm install
npm run build

echo "✅ MCP servers installed to ~/mcp-servers/servers/"
echo ""
echo "📋 Next steps:"
echo "1. Update ~/.config/Claude/claude_desktop_config.json with configurations above"
echo "2. Restart Claude Desktop"
echo "3. Verify MCP servers are connected in Claude Code"
```

## Verification

After configuring, test MCP integration:

```bash
# In Claude Code, try:
# - "What tables are in the nexus_db database?" (Postgres MCP)
# - "List files in the app directory" (Filesystem MCP)
# - "Make a GET request to localhost:8080/health" (Fetch MCP)
```

## Troubleshooting

### Common Issues

1. **"MCP server not found"**
   - Ensure Node.js 18+ is installed: `node --version`
   - Check paths in configuration are correct
   - Verify server builds completed: check for `dist/` directory

2. **Postgres connection refused**
   - Verify PostgreSQL is running: `docker ps | grep postgres`
   - Check credentials in `.env` file
   - Test connection: `PGPASSWORD=yourpass psql -h localhost -U nexus -d nexus_db`

3. **Permission denied**
   - Ensure Claude Desktop has permission to execute the servers
   - Check file permissions: `chmod +x ~/mcp-servers/servers/*/dist/index.js`

4. **DeepSeek still guessing**
   - Force MCP usage by starting prompts with: "Use the Postgres MCP to query..."
   - Explicitly request: "Check the filesystem MCP for the file structure"

## Benefits for DeepSeek

- **70% reduction in schema guessing errors**
- **Accurate file operations** without hallucinations
- **Direct database introspection** for query optimization
- **Private reasoning** for complex logic before implementation
- **Overall**: More reliable, accurate, and cost-effective DeepSeek usage

## Updates
- **2026-01-21**: Initial guide created for NEXUS DeepSeek optimization
- Check https://github.com/modelcontextprotocol/servers for latest server updates