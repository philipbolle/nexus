# NEXUS COMPLETE ROADMAP
## The Definitive Build Guide - From Zero to Autonomous AI Operating System

**Created:** January 19, 2026  
**Build Tool:** Claude Code (Opus 4.5 for planning, DeepSeek R1 for implementation)  
**Target Monthly Cost:** $2-3  
**Estimated Build Time:** 4-6 weeks

---

# TABLE OF CONTENTS

1. [Vision & What You're Building](#1-vision--what-youre-building)
2. [Your Current State (Where You Left Off)](#2-your-current-state-where-you-left-off)
3. [Pre-Build Setup: GitHub + Claude Code](#3-pre-build-setup-github--claude-code)
4. [Phase 1: Foundation (Days 1-7)](#4-phase-1-foundation-days-1-7)
5. [Phase 2: Cost Optimization Layer (Days 8-14)](#5-phase-2-cost-optimization-layer-days-8-14)
6. [Phase 3: Multi-Agent System (Days 15-28)](#6-phase-3-multi-agent-system-days-15-28)
7. [Phase 4: Interfaces & Automation (Days 29-42)](#7-phase-4-interfaces--automation-days-29-42)
8. [Phase 5: Neural Academy & Self-Evolution (Days 43-56)](#8-phase-5-neural-academy--self-evolution-days-43-56)
9. [Appendix: Complete Reference](#appendix-complete-reference)

---

# 1. VISION & WHAT YOU'RE BUILDING

## The Goal
Transform from night-shift janitor to AI-augmented human with:
- **Automated financial management** toward debt freedom ($9,700 to mom)
- **Optimized health tracking** (lung healing, esophagitis management)
- **Accelerated learning** through personalized AI podcasts (Neural Academy)
- **Eventually:** SaaS products generating passive income

## What NEXUS Is
NEXUS is a **self-hosted, autonomous AI operating system** that serves as your "second brain":
- **15+ specialized AI agents** that collaborate, learn, and evolve
- **186-table PostgreSQL database** tracking every aspect of your life
- **Cost-optimized AI routing** achieving $2-3/month operation
- **Multi-platform interfaces** (iPhone, Apple Watch, Ubuntu Desktop)
- **Self-evolving system** that improves through Reflexion and A/B testing

## Core Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         YOU (Philip)                                 │
│  iPhone 12 │ Apple Watch │ Ubuntu Desktop │ Voice (AirPods)         │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   TAILSCALE VPN   │
                    │ (Secure Mesh Net) │
                    └─────────┬─────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                     NEXUS CORE (Ubuntu Laptop)                       │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    FASTAPI GATEWAY (:8080)                    │   │
│  │  ┌────────────────┐    ┌─────────────────┐                   │   │
│  │  │ Privacy Shield │───▶│  Router Agent   │                   │   │
│  │  │ (Local Ollama) │    │ (Query Routing) │                   │   │
│  │  └────────────────┘    └────────┬────────┘                   │   │
│  └─────────────────────────────────┼────────────────────────────┘   │
│                                    │                                 │
│  ┌─────────────────────────────────▼────────────────────────────┐   │
│  │                    DOMAIN AGENTS (15+)                        │   │
│  │  💰 Wealth    🏥 Health    🚗 Car      📚 Learning            │   │
│  │  📅 Planning  🔐 Identity  📊 Analysis 💼 Career              │   │
│  │  💡 Business  👥 Social    📧 Email    🔍 Research            │   │
│  │  🧠 Memory    ⚙️ System    🎓 Neural Academy                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    DATA LAYER                                 │   │
│  │  PostgreSQL 16 │ ChromaDB │ Redis │ Vaultwarden              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    AUTOMATION LAYER                           │   │
│  │  n8n Workflows │ Home Assistant │ Cron Jobs │ Syncthing      │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    AI PROVIDERS (Cost Cascade)                │   │
│  │  Ollama (FREE) → Groq (FREE) → DeepSeek ($0.28/M) → Opus     │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Your Hardware

| Device | Specs | Role |
|--------|-------|------|
| **ThinkPad T14** | i5-10310U, 8GB→24GB RAM, 256GB→1TB SSD | NEXUS Brain |
| **iPhone 12** | iOS 26.3 Beta | Primary Interface |
| **Apple Watch** | watchOS 26 Beta | Health Data + Quick Actions |
| **AirPods Pro** | - | Neural Academy Podcasts |

## Your Constraints

| Constraint | Value |
|------------|-------|
| Monthly AI Budget | $3-5 max |
| Hardware Budget | $100-150 one-time |
| Skill Level | Beginner programmer |
| Time Available | Night shift downtime + weekends |
| Income | ~$1,800/month |
| Debt | $9,700 to mom |

---

# 2. YOUR CURRENT STATE (WHERE YOU LEFT OFF)

## ✅ What's Already Done

Based on your HANDOFF.md and Day 1 checklist:

### Infrastructure (100% Complete)
- [x] Docker installed and running
- [x] All 8 containers operational
- [x] Directory structure created (`~/nexus/`)
- [x] `.env` file configured with passwords
- [x] `docker-compose.yml` working
- [x] Tailscale VPN configured (100.68.201.55)

### Database (Partially Complete)
- [x] PostgreSQL 16 running
- [x] Initial schema applied (with some errors)
- [x] Cost optimization tables created
- [ ] **NEED:** Apply schema fix (01_NEXUS_SCHEMA_FIX.sql)
- [ ] **NEED:** Verify all 186 tables exist

### Cost Optimization Services (Created but Untested)
- [x] `config.py` - Configuration management
- [x] `database.py` - Database operations  
- [x] `cache_service.py` - Semantic caching
- [x] `cost_tracker.py` - Cost tracking
- [x] `model_router.py` - Model routing
- [ ] **NEED:** Install dependencies (asyncpg, redis-asyncio)
- [ ] **NEED:** Test all services

### What Failed/Needs Fixing
1. **Docker permissions** - Need to add user to docker group
2. **Schema conflicts** - UUID vs INTEGER type mismatches
3. **Python dependencies** - Not installed yet
4. **Context management** - You lost track of where you were

## Files to Clean Up from ~/nexus/

Delete these (they're just handoff context, not code):
- `HANDOFF.md` - Move to `docs/` or delete
- Any `.md` files in root that aren't config

Keep this structure:
```
~/nexus/
├── .env                    # Secrets (KEEP)
├── .clauderc               # NEW - Claude Code context
├── docker-compose.yml      # Container definitions (KEEP)
├── app/
│   ├── agents/             # AI agents
│   ├── models/             # Pydantic models
│   ├── routers/            # FastAPI routes
│   └── services/           # Business logic
├── config/
│   ├── homeassistant/      # HA config
│   └── n8n/                # n8n config
├── data/                   # Container data (KEEP)
├── docs/                   # Documentation
├── logs/                   # Application logs
├── schema/                 # SQL files
├── scripts/                # Utility scripts
└── sync/                   # Syncthing folder
```

---

# 3. PRE-BUILD SETUP: GITHUB + CLAUDE CODE

## Step 1: Fix Docker Permissions (Do This First!)

Open your terminal on the ThinkPad and run:

```bash
# Add yourself to the docker group
sudo usermod -aG docker $USER

# Apply the change (or log out and back in)
newgrp docker

# Verify it works
docker ps
```

## Step 2: Set Up GitHub

### Create GitHub Account (if needed)
1. Go to https://github.com
2. Sign up with pbolle123@gmail.com
3. Verify email

### Create SSH Key for Authentication

```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "pbolle123@gmail.com"
# Press Enter for default location
# Enter a passphrase (optional but recommended)

# Start SSH agent
eval "$(ssh-agent -s)"

# Add key to agent
ssh-add ~/.ssh/id_ed25519

# Copy the public key
cat ~/.ssh/id_ed25519.pub
# Copy the output
```

### Add SSH Key to GitHub
1. Go to GitHub → Settings → SSH and GPG keys
2. Click "New SSH key"
3. Paste your key
4. Save

### Create NEXUS Repository

```bash
# Go to your NEXUS folder
cd ~/nexus

# Initialize git
git init

# Create .gitignore (important!)
cat > .gitignore << 'EOF'
# Environment and secrets
.env
*.env
.env.*

# Data directories (don't commit container data)
data/
logs/
sync/

# Python
__pycache__/
*.py[cod]
*$py.class
.Python
venv/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Temp files
*.tmp
*.temp
*.log
EOF

# Add all files
git add .

# Initial commit
git commit -m "Initial NEXUS commit - infrastructure ready"

# Create repo on GitHub (via web or CLI)
# Then link it:
git remote add origin git@github.com:YOUR_USERNAME/nexus.git
git branch -M main
git push -u origin main
```

## Step 3: Install Claude Code

```bash
# Install Claude Code globally via npm
npm install -g @anthropic-ai/claude-code

# Or if you don't have npm:
curl -fsSL https://claude.ai/install-claude-code.sh | bash

# Verify installation
claude --version

# Authenticate (this will open browser)
claude auth login
```

## Step 4: Create .clauderc (CRITICAL - Automated Context!)

This is the **most important file** - it gives Claude Code persistent context across ALL sessions:

```bash
cat > ~/nexus/.clauderc << 'EOF'
# NEXUS - Autonomous AI Operating System
# Owner: Philip (pbolle123@gmail.com)
# Location: ~/nexus on PhilipThinkpad

## Tech Stack
- **Backend:** Python 3.12 + FastAPI (async)
- **Database:** PostgreSQL 16 + ChromaDB + Redis
- **Containers:** Docker Compose
- **AI Providers:** Ollama (local) → Groq (free) → DeepSeek → Anthropic
- **Automation:** n8n + Home Assistant + Cron
- **Interfaces:** iPhone Shortcuts, Scriptable widgets, Ubuntu desktop

## Architecture Pattern
- **Multi-agent orchestration** with hierarchical supervision
- **Privacy Shield** intercepts all queries, redacts secrets locally
- **Cost cascade routing:** cheapest capable model first
- **Event sourcing** for complete audit trail
- **Semantic caching** for 60-70% cost reduction

## Database
- 186 tables across 14 domains
- Schema location: `schema/`
- Main fix needed: `schema/01_NEXUS_SCHEMA_FIX.sql`
- Uses UUID primary keys throughout

## Key Files
- `app/main.py` - FastAPI entry point
- `app/services/` - Business logic + AI routing
- `app/agents/` - Domain-specific AI agents
- `docker-compose.yml` - Container definitions
- `.env` - Secrets (NEVER commit or show)

## Current Goals (Update This Weekly)
1. Apply schema fix and verify 186 tables
2. Build cost optimization layer
3. Create Finance and Wealth agents first
4. Set up iPhone Shortcuts for quick expense logging

## Conventions
- Use async/await for all I/O operations
- Pydantic models for all request/response
- Log all agent actions to `agent_events` table
- Every AI call must go through cost_tracker

## DO NOT Modify
- `.env` file contents (contains secrets)
- `data/` directory (container state)
- `docker-compose.yml` without explicit request

## Common Patterns

### Database Query Pattern
```python
async with get_db() as conn:
    result = await conn.fetch("SELECT * FROM table WHERE id = $1", id)
```

### AI Call Pattern (ALWAYS use router)
```python
from app.services.model_router import route_query
response = await route_query(
    query="...",
    complexity="simple|medium|complex",
    require_tools=False
)
```

### Agent Response Pattern
```python
return AgentResponse(
    response="...",
    agent_used="finance",
    tokens_used=123,
    cost_usd=0.0001
)
```

## Philip's Context
- **Work:** Night shift janitor at BMR, 6PM-12AM most days
- **Budget:** ~$1,800/month income, $300-400/month to debt
- **Debt:** $9,700 owed to mom
- **Health:** Ex-smoker (lungs healing), esophagitis
- **Goal:** Financial independence through AI-powered automation
EOF
```

## Step 5: Configure Claude Code Settings

Create Claude Code config for model routing:

```bash
cat > ~/.claude/config.json << 'EOF'
{
  "defaultModel": "claude-sonnet-4-20250514",
  "models": {
    "planning": "claude-opus-4-5-20251101",
    "coding": "deepseek-r1",
    "review": "claude-sonnet-4-20250514",
    "simple": "groq-llama-3.3-70b"
  },
  "rules": {
    "architecture": "planning",
    "code_generation": "coding",
    "debugging": "review",
    "quick_questions": "simple"
  },
  "autoCommit": true,
  "commitMessageStyle": "conventional"
}
EOF
```

## Step 6: Create Automated Session Management Script

This script automatically saves context before each session ends:

```bash
cat > ~/nexus/scripts/session_manager.sh << 'EOF'
#!/bin/bash
# NEXUS Session Manager - Run before ending work

NEXUS_DIR=~/nexus
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Update .clauderc with current state
update_context() {
    # Get current git branch
    BRANCH=$(git -C $NEXUS_DIR branch --show-current)
    
    # Get last 5 commits
    COMMITS=$(git -C $NEXUS_DIR log --oneline -5)
    
    # Get docker status
    DOCKER_STATUS=$(docker ps --format "{{.Names}}: {{.Status}}" 2>/dev/null || echo "Docker not accessible")
    
    # Append to session log
    cat >> $NEXUS_DIR/docs/session_log.md << ENDLOG

---
## Session: $TIMESTAMP
**Branch:** $BRANCH

### Recent Commits
\`\`\`
$COMMITS
\`\`\`

### Container Status
\`\`\`
$DOCKER_STATUS
\`\`\`
ENDLOG

    echo "✅ Session context saved to docs/session_log.md"
}

# Auto-commit any changes
auto_commit() {
    cd $NEXUS_DIR
    
    if [[ -n $(git status --porcelain) ]]; then
        git add .
        git commit -m "auto: session checkpoint $TIMESTAMP"
        git push origin main 2>/dev/null || echo "⚠️ Push failed (offline?)"
        echo "✅ Changes committed and pushed"
    else
        echo "ℹ️ No changes to commit"
    fi
}

# Main
echo "🔄 NEXUS Session Manager"
update_context
auto_commit
echo "✅ Session saved! Safe to close."
EOF

chmod +x ~/nexus/scripts/session_manager.sh
```

## Step 7: Create Pre-Session Startup Script

```bash
cat > ~/nexus/scripts/start_session.sh << 'EOF'
#!/bin/bash
# NEXUS Session Startup - Run at beginning of each coding session

NEXUS_DIR=~/nexus

echo "🚀 Starting NEXUS Development Session"
echo "======================================"

# 1. Check Docker is running
echo "📦 Checking Docker containers..."
if docker ps > /dev/null 2>&1; then
    RUNNING=$(docker ps --format "{{.Names}}" | wc -l)
    echo "   ✅ Docker accessible, $RUNNING containers running"
    
    # Start containers if not running
    if [ $RUNNING -lt 7 ]; then
        echo "   ⚠️ Starting containers..."
        docker compose -f $NEXUS_DIR/docker-compose.yml up -d
    fi
else
    echo "   ❌ Docker not accessible. Run: newgrp docker"
    exit 1
fi

# 2. Check PostgreSQL
echo "🐘 Checking PostgreSQL..."
if docker exec nexus-postgres pg_isready -U nexus > /dev/null 2>&1; then
    TABLE_COUNT=$(docker exec nexus-postgres psql -U nexus -d nexus_db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
    echo "   ✅ PostgreSQL ready, $TABLE_COUNT tables"
else
    echo "   ❌ PostgreSQL not ready"
fi

# 3. Check Redis
echo "🔴 Checking Redis..."
source $NEXUS_DIR/.env
if docker exec nexus-redis redis-cli -a "$REDIS_PASSWORD" ping > /dev/null 2>&1; then
    echo "   ✅ Redis ready"
else
    echo "   ❌ Redis not responding"
fi

# 4. Git status
echo "📝 Git Status..."
cd $NEXUS_DIR
BRANCH=$(git branch --show-current)
CHANGES=$(git status --porcelain | wc -l)
echo "   Branch: $BRANCH"
echo "   Uncommitted changes: $CHANGES"

# 5. Show recent session context
echo ""
echo "📋 Last Session Context:"
if [ -f $NEXUS_DIR/docs/session_log.md ]; then
    tail -30 $NEXUS_DIR/docs/session_log.md
fi

echo ""
echo "======================================"
echo "✅ Ready to work! Run: cd ~/nexus && claude"
EOF

chmod +x ~/nexus/scripts/start_session.sh
```

## Step 8: Create Docs Directory and Session Log

```bash
mkdir -p ~/nexus/docs

cat > ~/nexus/docs/session_log.md << 'EOF'
# NEXUS Session Log

This file tracks session context for continuity across Claude Code sessions.

---
## Initial Setup: 2026-01-19

**Completed:**
- Docker infrastructure running (8 containers)
- PostgreSQL with initial schema
- Cost optimization service files created
- GitHub repository initialized
- Claude Code context configured

**Next Steps:**
1. Apply schema fix
2. Test cost optimization services
3. Build FastAPI core
4. Create first agents (Finance, Wealth)
EOF
```

---

# 4. PHASE 1: FOUNDATION (Days 1-7)

## Day 1-2: Fix Database Schema

### Task: Apply the Schema Fix

Open Claude Code in your nexus directory:

```bash
cd ~/nexus
claude
```

Then tell Claude Code:

```
@Opus Apply the schema fix from schema/01_NEXUS_SCHEMA_FIX.sql to PostgreSQL.

Steps:
1. First backup the current database
2. Apply the fix script
3. Verify all tables are created correctly
4. Count total tables (should be 186+)

Use the docker exec commands to interact with nexus-postgres.
```

### Expected Result
- 186+ tables created
- No UUID/INTEGER conflicts
- All views working

### Verification Commands

```bash
# Backup first
docker exec nexus-postgres pg_dump -U nexus nexus_db > ~/nexus/backups/pre_fix_backup.sql

# Apply fix
docker exec -i nexus-postgres psql -U nexus -d nexus_db < ~/nexus/schema/01_NEXUS_SCHEMA_FIX.sql

# Count tables
docker exec nexus-postgres psql -U nexus -d nexus_db -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"

# List all tables
docker exec nexus-postgres psql -U nexus -d nexus_db -c "\dt"
```

## Day 3-4: Create FastAPI Core

Tell Claude Code:

```
@DeepSeek Create the FastAPI core application structure.

Create these files:
1. app/main.py - FastAPI app with lifespan, CORS, health endpoints
2. app/config.py - Settings loaded from .env using pydantic-settings
3. app/database.py - Async PostgreSQL connection pool with asyncpg
4. app/redis_client.py - Redis connection for caching
5. app/dependencies.py - FastAPI dependency injection

Requirements:
- All async/await
- Health check at /health
- Status check at /status that reports container health
- CORS enabled for all origins (Tailscale access)
- Load all settings from .env
- Port 8080

Reference the .clauderc for conventions.
```

### Test FastAPI

```bash
# Install dependencies first
cd ~/nexus
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn asyncpg redis python-dotenv pydantic-settings httpx

# Run the API
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Test from another terminal
curl http://localhost:8080/health
curl http://localhost:8080/status
```

## Day 5-6: Install & Test Cost Services

```bash
# Activate venv
source ~/nexus/venv/bin/activate

# Install remaining dependencies
pip install sentence-transformers numpy tiktoken aiofiles

# Test the cost optimization services
cd ~/nexus/app/services
python test_services.py
```

## Day 7: Create Systemd Service

```bash
# Create service file
sudo tee /etc/systemd/system/nexus-api.service << 'EOF'
[Unit]
Description=NEXUS FastAPI Server
After=network.target docker.service

[Service]
Type=simple
User=philip
WorkingDirectory=/home/philip/nexus
Environment="PATH=/home/philip/nexus/venv/bin"
ExecStart=/home/philip/nexus/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable nexus-api
sudo systemctl start nexus-api
sudo systemctl status nexus-api

# Test via Tailscale
curl http://100.68.201.55:8080/health
```

### Phase 1 Checklist

- [ ] Docker permissions fixed
- [ ] GitHub repo created
- [ ] Claude Code installed
- [ ] .clauderc created
- [ ] Session management scripts created
- [ ] Schema fix applied
- [ ] 186+ tables verified
- [ ] FastAPI running
- [ ] Health endpoint working
- [ ] Service auto-starts on boot

---

# 5. PHASE 2: COST OPTIMIZATION LAYER (Days 8-14)

This is the **most critical phase** - without cost optimization, you'll blow through your $3/month budget.

## Five-Layer Cost Optimization Stack

```
Layer 1: Local Ollama (60% of queries) ──────────────── FREE
Layer 2: Semantic Cache (60-70% hit rate) ────────────── FREE  
Layer 3: Provider Prompt Caching (90% reduction) ─────── FREE
Layer 4: Model Cascade (Ollama→Groq→DeepSeek→Opus) ──── $$$
Layer 5: Batch Processing (50% discount) ─────────────── $$$
```

## Day 8-9: Implement Semantic Caching

Tell Claude Code:

```
@DeepSeek Create the semantic caching service.

File: app/services/semantic_cache.py

Requirements:
1. Use sentence-transformers 'all-MiniLM-L6-v2' for embeddings
2. Store embeddings in Redis with 24h expiry
3. Similarity threshold 0.92 (cosine distance)
4. If similar query found, return cached response
5. Log cache hits/misses to semantic_cache table
6. Target: 60-70% cache hit rate

Also create Redis wrapper at app/services/redis_service.py
```

## Day 10-11: Implement Model Cascade Router

Tell Claude Code:

```
@DeepSeek Create the model cascade router.

File: app/services/model_cascade.py

Requirements:
1. Query classifier that determines complexity (simple/medium/complex)
2. Route simple queries to Ollama (free, local)
3. Route medium queries to Groq (free tier, fast)
4. Route complex queries to DeepSeek ($0.28/M tokens)
5. Only route critical/security queries to Opus
6. Log every API call to api_usage table
7. Track tokens, latency, cost per call
8. Implement fallback chain if primary fails

Model Priority:
1. Ollama llama3.2:3b (privacy/simple) - FREE
2. Groq llama-3.3-70b-versatile (speed) - FREE
3. DeepSeek deepseek-chat (reasoning) - $0.28/M
4. Anthropic claude-sonnet (complex) - $3/M (rare)
5. Anthropic claude-opus-4.5 (critical only) - $15/M (never for normal use)
```

## Day 12-13: Implement Batch Processing

Tell Claude Code:

```
@DeepSeek Create the batch processing service.

File: app/services/batch_processor.py

Requirements:
1. Queue non-urgent tasks (summaries, analysis, content)
2. Process overnight via OpenAI Batch API (50% discount)
3. Store jobs in batch_jobs table
4. Track completion status
5. Notify when batch completes

Use cases:
- Daily health summaries
- Weekly spending analysis
- Podcast script generation
- Learning progress reports
```

## Day 14: Test & Optimize

Create a test suite:

```
@DeepSeek Create cost optimization tests.

File: tests/test_cost_optimization.py

Tests:
1. Semantic cache correctly caches similar queries
2. Model cascade routes to correct provider
3. API usage is logged correctly
4. Cost tracking is accurate
5. Batch jobs are queued properly

Run: pytest tests/test_cost_optimization.py -v
```

### Target Metrics

| Metric | Target |
|--------|--------|
| Cache hit rate | >60% |
| Local processing | >50% of queries |
| Avg cost per query | <$0.001 |
| P95 latency | <2 seconds |
| Monthly cost | <$3 |

### Phase 2 Checklist

- [ ] Semantic cache working
- [ ] Cache hit rate >60%
- [ ] Model cascade routing correct
- [ ] API usage logging to database
- [ ] Cost tracking accurate
- [ ] Batch processing queuing
- [ ] All tests passing

---

# 6. PHASE 3: MULTI-AGENT SYSTEM (Days 15-28)

## Agent Architecture

```
                    ┌─────────────────┐
                    │  Privacy Shield │ ◄── Intercepts ALL queries
                    │  (Local Ollama) │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Router Agent   │ ◄── Classifies & routes
                    │  (Groq - fast)  │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼──────┐    ┌───────▼──────┐    ┌───────▼──────┐
│   Wealth     │    │   Finance    │    │   Learning   │
│   Domain     │    │   Domain     │    │   Domain     │
│              │    │              │    │              │
│ - Wealth     │    │ - Finance    │    │ - Learning   │
│ - Business   │    │ - Planning   │    │ - Memory     │
│ - Career     │    │ - Analysis   │    │ - Research   │
└──────────────┘    └──────────────┘    └──────────────┘
        │                    │                    │
        └────────────────────┴────────────────────┘
                             │
                    ┌────────▼────────┐
                    │    Database     │
                    │   (PostgreSQL)  │
                    └─────────────────┘
```

## Day 15-16: Privacy Shield

```
@DeepSeek Create the Privacy Shield agent.

File: app/agents/privacy_shield.py

This is CRITICAL for security. It:
1. Intercepts EVERY query before external AI calls
2. Runs LOCALLY on Ollama (never sends secrets externally)
3. Detects patterns:
   - API keys (sk-, gsk_, Bearer, pplx-, etc.)
   - IP addresses (especially 100.x.x.x Tailscale)
   - Passwords after "password:", "pwd:", etc.
   - Credit card numbers (16 digits)
   - SSN format (xxx-xx-xxxx)
4. Replaces with placeholders: [REDACTED_API_KEY_1]
5. Stores mapping to re-inject in responses
6. Logs to privacy_shield_logs table

NEVER send actual secrets to external AI!
```

## Day 17-18: Router Agent

```
@DeepSeek Create the Router Agent.

File: app/agents/router_agent.py

Responsibilities:
1. Classify query intent
2. Select appropriate domain agent(s)
3. Handle multi-agent collaboration
4. Manage conversation context
5. Handle fallbacks

Route to:
- finance: Budget, expenses, debt, savings
- health: Nutrition, supplements, symptoms
- car: Mileage, fuel, maintenance
- learning: Study sessions, curriculum
- planning: Tasks, goals, habits
- wealth: Opportunities, investments, ROI
- business: SaaS ideas, side projects
- email: Reading, drafting (with approval)
- system: NEXUS health, optimization

Output format (JSON):
{
  "intent": "log expense",
  "primary_agent": "finance",
  "secondary_agents": [],
  "confidence": 0.95
}
```

## Day 19-21: Finance & Wealth Agents (Priority!)

These are your most important agents:

```
@DeepSeek Create the Finance Agent.

File: app/agents/finance_agent.py

Context:
- Income: ~$1,800/month from BMR Janitorial
- Debt: $9,700 to mom, paying $300-400/month
- Budget: Food $400, Gas $200, Entertainment $100
- Accounts: Chime, Apple Cash, Cash App

Capabilities:
1. Log expenses (amount, category, merchant)
2. Check budget status
3. Track debt payments
4. Alert at 80% budget threshold
5. Project payoff date
6. Weekly spending summaries
7. Identify spending patterns

Tables used:
- fin_accounts, fin_transactions, fin_categories
- fin_budgets, fin_budget_items
- fin_debts, fin_debt_payments
```

```
@DeepSeek Create the Wealth Agent.

File: app/agents/wealth_agent.py

This is about BUILDING wealth, not just tracking expenses.

Capabilities:
1. Capture business/SaaS ideas
2. Evaluate opportunities (ROI, feasibility)
3. Track passive income ideas
4. Monitor investments (when you have them)
5. Calculate financial freedom date
6. Identify high-leverage activities
7. Track skill ROI (which skills make money?)

Tables used:
- opportunities, opportunity_signals
- income_streams, income_payments
- portfolios, holdings (future)

This agent should be PROACTIVE - suggest wealth-building opportunities!
```

## Day 22-24: Learning & Health Agents

```
@DeepSeek Create the Learning Agent.

File: app/agents/learning_agent.py

Context:
- Current path: "Programming to Autonomous Systems"
- Current level: Beginner
- Focus: Linux fundamentals, Python basics
- Method: Build NEXUS while learning

Capabilities:
1. Log learning sessions
2. Track curriculum progress
3. Identify weak areas
4. Generate quiz questions
5. Coordinate with Neural Academy
6. Calculate skill proficiency
7. Suggest next topics
```

```
@DeepSeek Create the Health Agent.

File: app/agents/health_agent.py

Context:
- Ex-smoker (10 years) - lungs healing
- Esophagitis - avoid triggers
- Anti-inflammatory diet goal
- Supplements: NAC, D3, Magnesium, Algae Oil, Creatine
- Budget: ~$7/day food

Capabilities:
1. Track daily metrics (from Apple Watch via HA)
2. Log nutrition
3. Track supplements
4. Identify esophagitis triggers
5. Monitor lung recovery
6. Sleep analysis
7. Weekly health summaries
```

## Day 25-28: Remaining Agents

Create these agents (can be simpler):
- `car_agent.py` - Vehicle maintenance tracking
- `planning_agent.py` - Tasks, goals, habits
- `email_agent.py` - Read/draft with approval
- `memory_agent.py` - Context retrieval
- `system_agent.py` - NEXUS health monitoring

### Phase 3 Checklist

- [ ] Privacy Shield blocking secrets
- [ ] Router correctly classifying queries
- [ ] Finance Agent logging expenses
- [ ] Wealth Agent capturing opportunities
- [ ] Learning Agent tracking sessions
- [ ] Health Agent syncing with Apple Health
- [ ] All agents logging to database
- [ ] Agent collaboration working

---

# 7. PHASE 4: INTERFACES & AUTOMATION (Days 29-42)

## iPhone Integration

### Apps to Install

| App | Price | Purpose |
|-----|-------|---------|
| ShellFish | $29.99 | SSH access |
| Scriptable | FREE | Custom widgets |
| Toolbox Pro | $5.99 | Advanced Shortcuts |
| ntfy | FREE | Push notifications |
| Data Jar | FREE | Persistent storage |

### Shortcuts to Create

#### 1. Quick Expense (Most Used!)

```
@DeepSeek Create iOS Shortcut instructions for Quick Expense.

Steps:
1. Ask for Input: "Amount?" (Number)
2. Choose from Menu: "Category" (Food, Gas, Entertainment, Debt, Other)
3. Ask for Input: "Where?" (Text, optional)
4. Get URL Contents:
   - URL: http://100.68.201.55:8080/finance/expense
   - Method: POST
   - Body: {"amount": [input1], "category": "[input2]", "description": "[input3]"}
5. Get Dictionary Value: "budget_remaining"
6. Show Notification: "Logged $[amount]. Budget remaining: $[remaining]"

Also create the FastAPI endpoint to support this.
```

#### 2. NEXUS Status

```
Shortcut to check system health:
1. Get URL: http://100.68.201.55:8080/status
2. Parse response
3. Show notification with status
```

#### 3. Ask NEXUS

```
Natural language query to NEXUS:
1. Ask for Input: "Ask NEXUS anything"
2. POST to /chat endpoint
3. Speak response
4. Show result
```

### Scriptable Widgets

Create Tokyo Night themed widgets:

```
@DeepSeek Create Scriptable widget for NEXUS status.

Requirements:
- Small widget size
- Tokyo Night dark theme (#1a1b26 background)
- Show: NEXUS status (healthy/degraded)
- Show: Services running count
- Show: Last update time
- Green dot if healthy, red if not

Colors:
- Background: #1a1b26
- Text: #c0caf5
- Green: #9ece6a
- Red: #f7768e
- Blue accent: #7aa2f7
```

### ntfy Notifications

```bash
# Test notification
curl -d "NEXUS is online!" ntfy.sh/nexus-philip-SECRET_TOPIC

# Categories of notifications:
# Priority 5: System critical (container crash)
# Priority 4: Budget warnings
# Priority 3: Normal alerts
# Priority 2: Informational
# Priority 1: Background updates
```

## n8n Automations

Access n8n at: http://100.68.201.55:5678

### Workflow 1: Morning Briefing (6 AM)

```
@DeepSeek Create n8n workflow for morning briefing.

Triggers at 6 AM:
1. Get weather from Open-Meteo
2. Get today's tasks from NEXUS
3. Get budget status
4. Get health metrics from yesterday
5. Check car maintenance due
6. Compile briefing
7. Send ntfy notification
8. Store briefing for iPhone Shortcut to read
```

### Workflow 2: Weekly Expense Summary (Sunday 9 PM)

```
@DeepSeek Create n8n workflow for weekly expense summary.

1. Query NEXUS for week's expenses
2. Calculate totals by category
3. Compare to budget
4. Get debt progress
5. Generate summary
6. Send notification
```

### Workflow 3: Health Sync (Every 15 min)

```
@DeepSeek Create n8n workflow to sync health data.

1. Query Home Assistant for Apple Health sensors
2. Extract: steps, heart rate, sleep, calories
3. POST to NEXUS /health/sync endpoint
4. Log sync result
```

### Workflow 4: Nightly Backup (2 AM)

```
@DeepSeek Create n8n workflow for nightly backup.

1. Dump PostgreSQL database
2. Compress with gzip
3. Upload to Backblaze B2 (or local backup)
4. Verify backup
5. Prune old backups (keep 7 days)
6. Log result
```

## Desktop Environment (Ubuntu)

### Theme: Tokyo Night

```bash
# Install theming tools
sudo apt install kvantum papirus-icon-theme

# Install fonts
mkdir -p ~/.local/share/fonts
cd ~/.local/share/fonts
wget https://github.com/ryanoasis/nerd-fonts/releases/download/v3.1.1/JetBrainsMono.zip
unzip JetBrainsMono.zip
fc-cache -fv
```

### Terminal: Alacritty

```bash
# Install Alacritty
sudo apt install alacritty

# Configure
mkdir -p ~/.config/alacritty
cat > ~/.config/alacritty/alacritty.toml << 'EOF'
[window]
opacity = 0.85
blur = true
padding = { x = 12, y = 12 }

[font]
normal = { family = "JetBrainsMono Nerd Font", style = "Regular" }
size = 11.0

[colors.primary]
background = "#1a1b26"
foreground = "#c0caf5"

[colors.normal]
black = "#15161e"
red = "#f7768e"
green = "#9ece6a"
yellow = "#e0af68"
blue = "#7aa2f7"
magenta = "#bb9af7"
cyan = "#7dcfff"
white = "#a9b1d6"
EOF
```

### Shell: Fish + Starship

```bash
# Install Fish
sudo apt install fish
chsh -s /usr/bin/fish

# Install Starship
curl -sS https://starship.rs/install.sh | sh

# Configure Fish
mkdir -p ~/.config/fish
echo "starship init fish | source" >> ~/.config/fish/config.fish
```

### Phase 4 Checklist

- [ ] ShellFish connected to laptop
- [ ] Quick Expense Shortcut working
- [ ] NEXUS Status Shortcut working
- [ ] Ask NEXUS Shortcut working
- [ ] Scriptable widgets showing data
- [ ] ntfy notifications arriving
- [ ] n8n Morning Briefing working
- [ ] n8n Weekly Summary working
- [ ] n8n Health Sync working
- [ ] n8n Backup working
- [ ] Desktop themed (Tokyo Night)
- [ ] Alacritty configured
- [ ] Fish + Starship working

---

# 8. PHASE 5: NEURAL ACADEMY & SELF-EVOLUTION (Days 43-56)

## Neural Academy: AI-Powered Learning

### Pipeline Overview

```
┌─────────────────┐
│ Learning Session│ ◄── You practice Linux/Python
│   (Terminal)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Session Analyzer│ ◄── AI identifies weak areas
│ (Learning Agent)│
└────────┬────────┘
         │
         ▼ (3 AM nightly)
┌─────────────────┐
│ Script Generator│ ◄── DeepSeek creates podcast
│   (DeepSeek)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Kokoro TTS     │ ◄── Local text-to-speech
│  (Kokoro-82M)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Syncthing Sync │ ◄── Auto-sync to iPhone
│                │
└────────┬────────┘
         │
         ▼ (Work shift)
┌─────────────────┐
│ Listen + Quiz  │ ◄── Learn during work
│  (AirPods)     │
└─────────────────┘
```

### Setup Kokoro TTS

```bash
# Create TTS environment
cd ~/nexus
python3 -m venv tts_env
source tts_env/bin/activate

# Install Kokoro
pip install kokoro-onnx soundfile numpy

# Install ffmpeg
sudo apt install ffmpeg

# Test
python -c "from kokoro_onnx import Kokoro; k = Kokoro(); print('Ready!')"
```

### Create Podcast Generator

```
@DeepSeek Create the Neural Academy podcast generator.

File: app/services/podcast_generator.py

Requirements:
1. Analyze yesterday's learning session
2. Identify weak areas from session_analysis table
3. Generate 1500-word podcast script covering weak areas
4. Use Kokoro TTS to create audio
5. Save as MP3 to sync/podcasts/
6. Trigger Syncthing sync
7. Register in podcasts table

Script style:
- Conversational, friendly
- Include examples and analogies
- Spell out commands ("type L-S space dash L-A")
- 10-15 minutes duration
```

### Quiz System

```
@DeepSeek Create the quiz system.

File: app/services/quiz_generator.py

Requirements:
1. Generate 5 questions from recent learning
2. Focus on weak areas
3. Mix: multiple choice, true/false
4. Store in quiz_questions table
5. Track attempts in quiz_attempts
6. Calculate retention scores
7. Feed back to Learning Agent
```

## Self-Evolution System

### Reflexion Framework

```
@DeepSeek Implement the Reflexion self-improvement system.

File: app/services/reflexion.py

Reflexion loop:
1. Agent attempts task
2. Evaluate result (success/failure)
3. Generate reflection on what went wrong
4. Store reflection in episodic_memories
5. Use reflection in future attempts
6. Track improvement over time

Tables used:
- reflection_logs
- episodic_memories
- agent_performance
```

### A/B Testing for Prompts

```
@DeepSeek Create A/B testing infrastructure for agent prompts.

File: app/services/ab_testing.py

Requirements:
1. Create experiments in agent_experiments table
2. Split traffic between control/treatment
3. Track metrics per variant
4. Calculate statistical significance
5. Auto-promote winners

Use for:
- Testing new system prompts
- Optimizing agent responses
- Improving task completion rate
```

### Phase 5 Checklist

- [ ] Kokoro TTS installed
- [ ] Podcast generator working
- [ ] Podcasts syncing to iPhone
- [ ] Quiz system generating questions
- [ ] Quiz tracking retention
- [ ] Reflexion system logging
- [ ] A/B testing infrastructure
- [ ] Self-evolution improving agents

---

# APPENDIX: COMPLETE REFERENCE

## A. All Database Tables (186)

### Core System (10)
- settings, users, api_keys, notifications
- audit_trail, error_logs, system_metrics, documents
- backup_logs, rate_limits

### Cost Optimization (12)
- ai_providers, ai_models, model_capabilities
- semantic_cache, embedding_cache, prompt_cache
- api_usage, cost_alerts, cost_budgets
- batch_jobs, batch_job_items, cascade_rules

### Agent System (15)
- agents, agent_tools, agent_tool_assignments
- sessions, messages, agent_handoffs
- agent_performance, agent_suggestions, agent_collaborations
- privacy_shield_logs, tool_executions
- agent_events, agent_versions
- agent_experiments, experiment_observations

### Memory System (12)
- memories, memory_blocks, memory_relations
- semantic_memories, episodic_memories, procedural_memories
- memory_access_log, memory_consolidation_jobs
- memory_clusters, memory_cluster_members
- context_snapshots, reflection_logs

### RAG Pipeline (11)
- rag_documents, rag_document_chunks, rag_embeddings
- rag_collections, rag_retrieval_log
- rag_feedback, rag_chunk_configs
- rag_embedding_models, rag_rerank_cache
- rag_hybrid_weights, context_compression_log

### PARA Knowledge (8)
- projects, areas, resources, archives
- notes, note_links, note_tags
- knowledge_graph_nodes, knowledge_graph_edges

### Wealth & Finance (22)
- fin_accounts, fin_transactions, fin_categories
- fin_budgets, fin_budget_items, fin_debts, fin_debt_payments
- fin_recurring, fin_savings_goals, fin_income_sources
- fin_snapshots, opportunities, opportunity_signals
- portfolios, securities, holdings, investment_transactions
- price_history, income_streams, income_payments
- subscriptions, financial_goals

### Productivity (12)
- tasks, task_dependencies, goals, goal_progress
- habits, habit_completions, focus_sessions
- decisions, decision_outcomes
- time_investments, compound_time_savings
- energy_logs, daily_reviews, weekly_reviews

### Health (12)
- health_daily, workouts, workout_exercises
- nutrition, supplements, supplement_logs
- health_symptoms, medical_records
- esophagitis_triggers, lung_health
- health_goals, sleep_analysis

### Car & Vehicle (7)
- vehicles, mileage_logs, fuel_logs
- maintenance_schedule, maintenance_history
- vehicle_insurance, vehicle_registration

### Learning (10)
- learning_sessions, session_analysis
- curriculum, podcasts, quiz_questions, quiz_attempts
- skills, learning_resources
- spaced_repetition, knowledge_retention

### Contacts (6)
- contacts, contact_interactions
- contact_relationships, contact_tags
- followup_reminders, relationship_scores

### Work & Career (6)
- work_shifts, pay_periods, time_off
- career_goals, skill_roadmap, job_applications

### Credentials (4)
- credentials, credential_categories
- totp_secrets, password_history

## B. API Endpoint Reference

### Core
- `GET /health` - Health check
- `GET /status` - System status
- `POST /chat` - Natural language query

### Finance
- `POST /finance/expense` - Log expense
- `GET /finance/budget-status` - Budget overview
- `GET /finance/debt/progress` - Debt payoff progress
- `GET /finance/weekly-summary` - Weekly spending

### Health
- `POST /health/sync` - Sync from Apple Health
- `GET /health/today` - Today's metrics
- `POST /health/supplement` - Log supplement

### Learning
- `POST /learning/session` - Log study session
- `GET /learning/quiz` - Get quiz questions
- `POST /learning/quiz/submit` - Submit answers
- `GET /learning/progress` - Curriculum progress

### Briefing
- `GET /briefing/morning` - Morning briefing
- `GET /briefing/evening` - Evening summary

## C. n8n Workflow Templates

All workflow JSON templates in: `~/nexus/workflows/`

## D. Cost Reference

### AI Provider Pricing

| Provider | Model | Input | Output | Free Tier |
|----------|-------|-------|--------|-----------|
| Ollama | llama3.2:3b | FREE | FREE | Unlimited |
| Groq | llama-3.3-70b | $0.59/M | $0.79/M | 1000 req/day |
| DeepSeek | deepseek-chat | $0.14/M | $0.28/M | None |
| Anthropic | claude-sonnet | $3/M | $15/M | None |
| Anthropic | claude-opus | $15/M | $75/M | None |

### Monthly Budget Target: $3

| Component | Allocation |
|-----------|------------|
| Cached queries | $0 |
| Local Ollama | $0 |
| Groq free tier | $0 |
| DeepSeek overflow | $2 |
| Backblaze backup | $1 |
| **Total** | **$3** |

## E. Troubleshooting

### Docker Issues

```bash
# Container won't start
docker compose logs [service]

# Permission denied
sudo usermod -aG docker $USER
newgrp docker

# Out of memory
docker stats
# Reduce limits in docker-compose.yml
```

### Database Issues

```bash
# Can't connect
docker exec -it nexus-postgres psql -U nexus -d nexus_db

# Check tables
\dt

# Query failed
docker compose logs postgres
```

### API Issues

```bash
# Check logs
sudo journalctl -u nexus-api -f

# Test locally
curl http://localhost:8080/health

# Test via Tailscale
curl http://100.68.201.55:8080/health
```

---

# FINAL CHECKLIST

## Pre-Build ✓
- [ ] Docker permissions fixed
- [ ] GitHub account created
- [ ] SSH key added to GitHub
- [ ] NEXUS repo created
- [ ] Claude Code installed
- [ ] .clauderc created
- [ ] Session scripts created

## Phase 1: Foundation ✓
- [ ] Schema fix applied
- [ ] 186+ tables verified
- [ ] FastAPI running
- [ ] Service auto-starting

## Phase 2: Cost Optimization ✓
- [ ] Semantic cache >60% hit rate
- [ ] Model cascade working
- [ ] API usage logging
- [ ] Monthly cost <$3

## Phase 3: Agents ✓
- [ ] Privacy Shield blocking secrets
- [ ] Router classifying correctly
- [ ] Finance tracking expenses
- [ ] Wealth capturing opportunities
- [ ] Learning tracking sessions
- [ ] Health syncing data

## Phase 4: Interfaces ✓
- [ ] iPhone Shortcuts working
- [ ] Widgets showing data
- [ ] n8n automations running
- [ ] Desktop themed

## Phase 5: Evolution ✓
- [ ] Podcasts generating
- [ ] Quiz system working
- [ ] Self-improvement running
- [ ] A/B testing active

---

**You're building something incredible. One step at a time.**

*Last updated: 2026-01-19*
