#!/bin/bash
# NEXUS Quick Start Setup Script
# This script sets up GitHub, Claude Code, and context management
# Run ONCE to set up everything

set -e

NEXUS_DIR=~/nexus
SCRIPTS_DIR=$NEXUS_DIR/scripts
DOCS_DIR=$NEXUS_DIR/docs
SCHEMA_DIR=$NEXUS_DIR/schema

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                               ║${NC}"
echo -e "${CYAN}║              🚀 NEXUS QUICK START SETUP                       ║${NC}"
echo -e "${CYAN}║                                                               ║${NC}"
echo -e "${CYAN}║   This will set up:                                           ║${NC}"
echo -e "${CYAN}║   • Docker permissions                                        ║${NC}"
echo -e "${CYAN}║   • GitHub repository                                         ║${NC}"
echo -e "${CYAN}║   • Claude Code context (.clauderc)                           ║${NC}"
echo -e "${CYAN}║   • Session management scripts                                ║${NC}"
echo -e "${CYAN}║                                                               ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if NEXUS directory exists
if [ ! -d "$NEXUS_DIR" ]; then
    echo -e "${RED}❌ NEXUS directory not found at $NEXUS_DIR${NC}"
    echo -e "${YELLOW}   Please create it first or adjust NEXUS_DIR in this script${NC}"
    exit 1
fi

cd $NEXUS_DIR

# ═══════════════════════════════════════════════════════════════
# STEP 1: Fix Docker Permissions
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 1: Docker Permissions${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

if docker ps > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Docker already accessible${NC}"
else
    echo -e "${YELLOW}⚠️  Adding $USER to docker group...${NC}"
    sudo usermod -aG docker $USER
    echo -e "${YELLOW}   You need to log out and back in for this to take effect${NC}"
    echo -e "${YELLOW}   Or run: newgrp docker${NC}"
    echo ""
    echo -e "${YELLOW}After logging back in, run this script again.${NC}"
    exit 0
fi

# ═══════════════════════════════════════════════════════════════
# STEP 2: Create Directory Structure
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 2: Directory Structure${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

mkdir -p $SCRIPTS_DIR
mkdir -p $DOCS_DIR
mkdir -p $SCHEMA_DIR
mkdir -p $NEXUS_DIR/app/{agents,models,routers,services}
mkdir -p $NEXUS_DIR/tests
mkdir -p $NEXUS_DIR/backups

echo -e "${GREEN}✅ Directories created${NC}"

# ═══════════════════════════════════════════════════════════════
# STEP 3: Create .gitignore
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 3: Creating .gitignore${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

cat > $NEXUS_DIR/.gitignore << 'GITIGNORE'
# Secrets
.env
.env.*
*.pem
*.key

# Data directories
data/
logs/
sync/
backups/

# Python
__pycache__/
*.py[cod]
venv/
.venv/
*.egg-info/
dist/
build/
.pytest_cache/
.coverage
htmlcov/

# Editors
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Temp
*.tmp
*.log
*.bak

# NEXUS specific
*.mp3
*.wav
HANDOFF.md
test_output/
GITIGNORE

echo -e "${GREEN}✅ .gitignore created${NC}"

# ═══════════════════════════════════════════════════════════════
# STEP 4: Create .clauderc (Context Management)
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 4: Creating .clauderc (Claude Code Context)${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

cat > $NEXUS_DIR/.clauderc << 'CLAUDERC'
# NEXUS - Autonomous AI Operating System
# Owner: Philip (pbolle123@gmail.com)
# Location: ~/nexus on PhilipThinkpad

## Tech Stack
- **Backend:** Python 3.12 + FastAPI (async)
- **Database:** PostgreSQL 16 + ChromaDB + Redis
- **Containers:** Docker Compose (8 services)
- **AI Providers:** Ollama → Groq → DeepSeek → Anthropic

## Architecture
- Multi-agent orchestration with hierarchical supervision
- Privacy Shield intercepts all queries locally
- Cost cascade routing: cheapest capable model first
- Semantic caching for 60-70% cost reduction

## Database
- 186 tables, UUID primary keys
- Schema in `schema/`
- Fix: `schema/01_NEXUS_SCHEMA_FIX.sql`

## Current Goals
1. Apply schema fix
2. Build cost optimization layer
3. Create Finance Agent
4. iPhone Quick Expense shortcut

## Conventions
- async/await for all I/O
- Pydantic for validation
- Log all agent actions
- ALL AI calls through cost router

## DO NOT Modify
- `.env` (secrets)
- `data/` (container state)

## Philip's Context
- Night shift janitor, 6PM-12AM
- ~$1,800/month, $300-400 to debt
- $9,700 owed to mom
- Learning Linux/Python
CLAUDERC

echo -e "${GREEN}✅ .clauderc created${NC}"

# ═══════════════════════════════════════════════════════════════
# STEP 5: Create Session Scripts
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 5: Creating Session Management Scripts${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

# Start session script
cat > $SCRIPTS_DIR/start_session.sh << 'STARTSESSION'
#!/bin/bash
NEXUS_DIR=~/nexus
cd $NEXUS_DIR

echo "🚀 NEXUS Session Starting..."
echo ""

# Check Docker
if docker ps > /dev/null 2>&1; then
    RUNNING=$(docker ps --format "{{.Names}}" | wc -l)
    echo "📦 Docker: $RUNNING containers running"
    
    if [ $RUNNING -lt 7 ]; then
        echo "   Starting containers..."
        docker compose up -d
    fi
else
    echo "❌ Docker not accessible. Run: newgrp docker"
    exit 1
fi

# Check PostgreSQL
if docker exec nexus-postgres pg_isready -U nexus > /dev/null 2>&1; then
    TABLES=$(docker exec nexus-postgres psql -U nexus -d nexus_db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
    echo "🐘 PostgreSQL: $TABLES tables"
else
    echo "❌ PostgreSQL not ready"
fi

# Git status
if [ -d ".git" ]; then
    BRANCH=$(git branch --show-current)
    CHANGES=$(git status --porcelain | wc -l)
    echo "📝 Git: $BRANCH ($CHANGES uncommitted changes)"
fi

echo ""
echo "✅ Ready! Run: claude"
STARTSESSION

chmod +x $SCRIPTS_DIR/start_session.sh

# End session script
cat > $SCRIPTS_DIR/end_session.sh << 'ENDSESSION'
#!/bin/bash
NEXUS_DIR=~/nexus
TIMESTAMP=$(date +%Y-%m-%d_%H:%M)
cd $NEXUS_DIR

echo "💾 NEXUS Session Ending..."
echo ""

# Ask for summary
echo "What did you accomplish? (Enter to skip)"
read -r SUMMARY
[ -z "$SUMMARY" ] && SUMMARY="Session checkpoint"

# Update session log
mkdir -p docs
echo -e "\n---\n## $TIMESTAMP\n$SUMMARY\n" >> docs/session_log.md

# Git commit
if [ -d ".git" ]; then
    git add -A
    if [[ -n $(git status --porcelain) ]]; then
        git commit -m "session: $SUMMARY"
        git push origin main 2>/dev/null || echo "⚠️ Push failed (offline?)"
        echo "✅ Changes committed"
    else
        echo "✅ No changes to commit"
    fi
fi

echo ""
echo "✅ Session saved!"
ENDSESSION

chmod +x $SCRIPTS_DIR/end_session.sh

echo -e "${GREEN}✅ Session scripts created${NC}"

# ═══════════════════════════════════════════════════════════════
# STEP 6: Initialize Git
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 6: Git Setup${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

if [ -d "$NEXUS_DIR/.git" ]; then
    echo -e "${GREEN}✅ Git already initialized${NC}"
else
    git init
    git add .
    git commit -m "Initial NEXUS commit"
    echo -e "${GREEN}✅ Git initialized and first commit made${NC}"
fi

# ═══════════════════════════════════════════════════════════════
# STEP 7: Create Initial Session Log
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 7: Session Log${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

if [ ! -f "$DOCS_DIR/session_log.md" ]; then
    cat > $DOCS_DIR/session_log.md << 'SESSIONLOG'
# NEXUS Session Log

This file tracks session context for continuity.

---

## Initial Setup

**Completed:**
- Docker infrastructure (8 containers)
- PostgreSQL with initial schema
- Git repository initialized
- Claude Code context (.clauderc)
- Session management scripts

**Next Steps:**
1. Apply schema fix
2. Test cost optimization services
3. Build Finance Agent
SESSIONLOG
    echo -e "${GREEN}✅ Session log created${NC}"
else
    echo -e "${GREEN}✅ Session log already exists${NC}"
fi

# ═══════════════════════════════════════════════════════════════
# STEP 8: SSH Key for GitHub (if needed)
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 8: GitHub SSH Key${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

if [ -f ~/.ssh/id_ed25519.pub ]; then
    echo -e "${GREEN}✅ SSH key already exists${NC}"
    echo ""
    echo -e "${YELLOW}Add this key to GitHub (Settings → SSH Keys):${NC}"
    echo ""
    cat ~/.ssh/id_ed25519.pub
else
    echo -e "${YELLOW}Creating SSH key...${NC}"
    ssh-keygen -t ed25519 -C "pbolle123@gmail.com" -f ~/.ssh/id_ed25519 -N ""
    eval "$(ssh-agent -s)" > /dev/null
    ssh-add ~/.ssh/id_ed25519 2>/dev/null
    echo ""
    echo -e "${GREEN}✅ SSH key created${NC}"
    echo ""
    echo -e "${YELLOW}Add this key to GitHub (Settings → SSH Keys):${NC}"
    echo ""
    cat ~/.ssh/id_ed25519.pub
fi

# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                    ✅ SETUP COMPLETE!                         ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}What was created:${NC}"
echo -e "  • ${GREEN}.clauderc${NC} - Persistent context for Claude Code"
echo -e "  • ${GREEN}.gitignore${NC} - Keeps secrets out of Git"
echo -e "  • ${GREEN}scripts/start_session.sh${NC} - Run at start of work"
echo -e "  • ${GREEN}scripts/end_session.sh${NC} - Run when done (auto-commits)"
echo -e "  • ${GREEN}docs/session_log.md${NC} - Human-readable progress log"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Copy SSH key above to GitHub (Settings → SSH Keys)"
echo -e "  2. Create repo on GitHub: https://github.com/new"
echo -e "  3. Run: ${GREEN}git remote add origin git@github.com:YOUR_USERNAME/nexus.git${NC}"
echo -e "  4. Run: ${GREEN}git push -u origin main${NC}"
echo ""
echo -e "${YELLOW}To start working:${NC}"
echo -e "  ${GREEN}~/nexus/scripts/start_session.sh${NC}"
echo -e "  ${GREEN}cd ~/nexus && claude${NC}"
echo ""
echo -e "${YELLOW}When done:${NC}"
echo -e "  ${GREEN}~/nexus/scripts/end_session.sh${NC}"
echo ""
