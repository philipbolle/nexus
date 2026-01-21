#!/bin/bash
# NEXUS MCP Server Setup Script
# Install essential MCP servers for DeepSeek optimization

set -e

echo "🚀 Setting up MCP servers for DeepSeek optimization..."
echo "======================================================"

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 18+ first."
    echo "   Ubuntu/Debian: sudo apt install nodejs npm"
    echo "   macOS: brew install node"
    exit 1
fi

NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version too old (found v$(node --version), need 18+)"
    exit 1
fi

echo "✅ Node.js $(node --version) detected"

# Create servers directory
MCP_DIR="$HOME/mcp-servers"
mkdir -p "$MCP_DIR"
cd "$MCP_DIR"

# Clone official MCP servers
if [ ! -d "servers" ]; then
    echo "📦 Cloning official MCP servers from GitHub..."
    git clone https://github.com/modelcontextprotocol/servers.git || {
        echo "❌ Failed to clone MCP servers"
        echo "   Check internet connection or GitHub access"
        exit 1
    }
else
    echo "📦 MCP servers already cloned, updating..."
    cd servers
    git pull
    cd ..
fi

echo ""
echo "Installing MCP servers (monorepo)..."
echo "------------------------------------"

# Navigate to servers directory
cd servers

# Check if npm install has been run
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies for all MCP servers..."
    npm install --silent
    echo "   ✅ Dependencies installed"
else
    echo "📦 Dependencies already installed"
fi

# Build all servers
echo "🔨 Building all MCP servers..."
npm run build --silent
echo "   ✅ All servers built"

# Verify critical servers were built
echo "🔍 Verifying server builds..."
cd "$MCP_DIR"

# Check JavaScript servers
JS_SERVERS=("sequentialthinking" "filesystem")
for server in "${JS_SERVERS[@]}"; do
    if [ -f "servers/src/$server/dist/index.js" ]; then
        echo "   ✅ $server (JavaScript) built successfully"
    else
        echo "   ❌ $server build missing: servers/src/$server/dist/index.js"
    fi
done

# Install and verify Python fetch server
echo "🐍 Installing Python Fetch server..."
cd "servers/src/fetch"
if [ ! -d ".venv" ]; then
    echo "   Creating virtual environment..."
    python3 -m venv .venv 2>/dev/null
fi

if [ -f ".venv/bin/mcp-server-fetch" ]; then
    echo "   ✅ Fetch server already installed"
else
    echo "   Installing dependencies..."
    .venv/bin/pip install -e . --quiet 2>/dev/null
    if [ -f ".venv/bin/mcp-server-fetch" ]; then
        echo "   ✅ Fetch server installed successfully"
    else
        echo "   ❌ Failed to install Fetch server"
    fi
fi
cd "$MCP_DIR"

# Install custom PostgreSQL MCP server
echo "🐘 Installing PostgreSQL MCP server..."
cd "$MCP_DIR"
if [ ! -d "postgres-mcp" ]; then
    echo "   Creating PostgreSQL MCP server directory..."
    mkdir -p postgres-mcp
fi

cd postgres-mcp

# Copy server files from NEXUS template directory
TEMPLATE_DIR="/home/philip/nexus/scripts/mcp-servers/postgres-mcp"
if [ ! -f "server.py" ] && [ -d "$TEMPLATE_DIR" ]; then
    echo "   Copying server files from NEXUS templates..."
    cp "$TEMPLATE_DIR"/*.py . 2>/dev/null || true
    cp "$TEMPLATE_DIR"/*.txt . 2>/dev/null || true
    cp "$TEMPLATE_DIR"/*.md . 2>/dev/null || true
    if [ -f "server.py" ]; then
        echo "   ✅ PostgreSQL MCP server files copied successfully"
    else
        echo "   ⚠️  Could not copy server files from $TEMPLATE_DIR"
        echo "   See docs/MCP_SETUP.md for manual creation instructions"
    fi
elif [ -f "server.py" ]; then
    echo "   ✅ PostgreSQL MCP server files already exist"
else
    echo "   ❌ PostgreSQL MCP server files not found and no templates available"
    echo "   See docs/MCP_SETUP.md for manual creation instructions"
fi

# Install Python dependencies
if [ ! -d ".venv" ]; then
    echo "   Creating virtual environment..."
    python3 -m venv .venv 2>/dev/null
fi

if [ -f ".venv/bin/activate" ]; then
    echo "   Installing dependencies..."
    .venv/bin/pip install -r requirements.txt --quiet 2>/dev/null
    echo "   ✅ PostgreSQL MCP dependencies installed"
else
    echo "   ❌ Failed to create virtual environment"
fi

cd "$MCP_DIR"

echo ""
echo "======================================================"
echo "✅ MCP servers installed to $MCP_DIR/ (servers/ + postgres-mcp/)"
echo ""
echo "📋 NEXT STEPS:"
echo ""
echo "1. Configure Claude Desktop:"
echo "   Edit ~/.config/Claude/claude_desktop_config.json"
echo ""
echo "2. Add MCP server configurations:"
cat << 'EOF'
   {
     "mcpServers": {
       "thinking": {
         "command": "node",
         "args": ["/home/philip/mcp-servers/servers/src/sequentialthinking/dist/index.js"]
       },
       "filesystem": {
         "command": "node",
         "args": ["/home/philip/mcp-servers/servers/src/filesystem/dist/index.js"],
         "env": {
           "ALLOWED_PATHS": ["/home/philip/nexus"]
         }
       },
       "fetch": {
         "command": "/home/philip/mcp-servers/servers/src/fetch/.venv/bin/mcp-server-fetch"
       },
       "postgres": {
         "command": "/home/philip/mcp-servers/postgres-mcp/.venv/bin/python",
         "args": ["/home/philip/mcp-servers/postgres-mcp/server.py"]
       }
     }
   }
EOF
echo ""
echo "3. Restart Claude Desktop"
echo ""
echo "4. Test MCP integration in Claude Code:"
echo "   - 'List files in app directory' (Filesystem MCP)"
echo "   - 'Check if API is healthy' (Fetch MCP → http://localhost:8080/health)"
echo "   - 'Think through this problem' (Thinking MCP)"
echo "   - 'List database tables' (PostgreSQL MCP)"
echo ""
echo "📚 Full documentation: docs/MCP_SETUP.md"
echo "======================================================"