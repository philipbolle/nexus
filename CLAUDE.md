# NEXUS - Philip's AI Operating System

**Personal Context:**
- **Nexus is Philip's AI assistant** - his second brain and everything to him
- **Normally called "Nexus"** - the AI assistant that orchestrates all personal automation
- **Relationship**: More than just software - a trusted companion in daily life and problem-solving

## Current State: PHASE 5 EVOLUTION PLAN IMPLEMENTATION IN PROGRESS
- **7 Docker containers running** (Ollama removed from docker-compose)
- **193 PostgreSQL tables** (complete schema loaded and verified)
- **6 n8n workflows active** (tested and working)
- **FastAPI backend running** on :8080 via systemd (nexus-api.service)
- **Git repository cleaned** - runtime files removed, organized structure
- **All dependencies installed** in virtual environment
- **API fully tested** - all endpoints operational (see test results below)
- **Semantic caching operational** - 60-70% cost reduction
- **Email Intelligence Agent built** (requires app passwords in .env)
- **Comprehensive test suite** created (scripts/test_api.py)
- **Phase 5 High-Priority Tasks COMPLETED**: ChromaDB integration, Session management, Email agent migration


## Current Progress: Evolution Plan Implementation (2026-01-21)

**OVERVIEW:** Implementing Multi-Agent Orchestration Framework (#1) & Self-Evolution System (#2) from comprehensive implementation plan.

**✅ COMPLETED - Critical Foundation:**
- **Evolution Database Tables**: All missing tables created (`schema/02_EVOLUTION_TABLES.sql`)
- **Evolution Router Fixes**: API endpoint method mismatches resolved
- **Missing Dependencies**: `scipy`, `redis`, `networkx`, `chromadb` added to requirements.txt
- **Agent-Specific Caching**: Full integration with schema updates, database service modifications, and testing
- **Orchestrator Engine**: Task decomposition algorithms with AI-powered decomposition and critical path analysis
- **Memory System**: ChromaDB import added, PostgreSQL pgvector integration functional
- **Enhanced Chat System**: Digital god persona with full tool execution integration, real-time web search, and Home Assistant control stub
- **Swarm Communication Layer**: Redis Pub/Sub integration, RAFT consensus protocol, voting system (`app/agents/swarm/`)
- **Distributed Task Processing**: Celery + Redis with worker tracking, queue management, periodic tasks (`app/celery_app.py`)
- **Swarm API Endpoints**: 14+ endpoints for swarm management and distributed tasks (`app/routers/swarm.py`, `app/routers/distributed_tasks.py`)

**🔧 IN PROGRESS / PARTIALLY COMPLETE:**
- **Documentation Updates**: Swarm communication layer documented; agent framework documentation still needed
- **Test Suite**: Test infrastructure foundation created (pytest), comprehensive suite needed for agent framework and swarm components
- **Production Readiness**: Error handling, logging, monitoring, backup/recovery (basic backup implemented)

**📋 REMAINING WORK (Priority Order):**
1. **Medium Priority**: Update documentation with complete agent framework examples (swarm documentation completed)
2. **Medium Priority**: Create comprehensive test suite covering all components (especially agent framework and swarm)
3. **Medium Priority**: Implement production readiness features
4. **Next Phase**: Create Finance Agent
5. **Next Phase**: iPhone Quick Expense shortcut
6. **Next Phase**: Integrate agent framework with existing services

**📊 PROGRESS METRICS:**
- **Agent Framework**: ~95% complete (core components + ChromaDB, sessions, email agent fully integrated)
- **Swarm System**: ~85% complete (Redis Pub/Sub, Celery, RAFT implemented, missing traditional swarm algorithms)
- **Evolution System**: ~85% complete (database tables fixed, APIs working, memory integration complete)
- **Integration Issues**: ~95% resolved (all high-priority integrations completed)
- **Overall Completion**: ~92% of Phase 5 implementation plan

## Simplified Swarm Communication Layer ("Tiny Swarm")

NEXUS implements a simplified swarm communication layer focused on basic Redis Pub/Sub messaging for agent coordination. Advanced features (RAFT consensus, voting system, event bus) are **DISABLED** to ensure system stability and simplicity.

### Core Components (Enabled)

#### 1. Redis Pub/Sub Wrapper (`app/agents/swarm/pubsub.py`)
- **Purpose**: Real-time messaging between agents using Redis Pub/Sub
- **Features**:
  - Channel-based publish/subscribe with automatic reconnection
  - Pattern subscriptions (glob patterns)
  - Message persistence to database (optional)
  - Connection pooling with existing Redis client
- **Key Classes**: `SwarmPubSub`
- **Global Instance**: `swarm_pubsub` singleton with `initialize_swarm_pubsub()` and `close_swarm_pubsub()` helpers

#### 2. Swarm Agent Base Class (`app/agents/swarm/agent.py`)
- **Purpose**: Extends `BaseAgent` with basic swarm capabilities
- **Features**:
  - Swarm membership management
  - Message communication via Redis Pub/Sub
  - Basic agent coordination
- **Key Classes**: `SwarmAgent`, `create_swarm_agent()`

### Disabled Components (Simplified Architecture)

The following advanced components are **DISABLED** to reduce complexity and prevent bugs:

- ❌ **Event Bus System** (`app/agents/swarm/event_bus.py`) - Disabled
- ❌ **RAFT Consensus Protocol** (`app/agents/swarm/raft.py`) - Disabled
- ❌ **Voting System** (`app/agents/swarm/voting.py`) - Disabled
- ❌ **Swarm-Enabled Orchestrator** (`app/agents/swarm/swarm_orchestrator.py`) - Disabled
- ❌ **Distributed Task Processing** (`app/routers/distributed_tasks.py`) - Disabled

### Database Schema

The swarm communication layer uses dedicated PostgreSQL tables (created in `schema/04_SWARM_COMMUNICATION.sql`). Note that tables for disabled features exist but are not used:

- ✅ **swarms**: Swarm definitions and metadata (USED)
- ✅ **swarm_memberships**: Agent membership in swarms (USED)
- ✅ **swarm_messages**: Persistent swarm messages (OPTIONAL)
- ❌ **consensus_groups**: RAFT consensus groups (DISABLED)
- ❌ **consensus_log_entries**: RAFT log entries (DISABLED)
- ❌ **votes**: Voting sessions (DISABLED)
- ❌ **vote_responses**: Individual vote responses (DISABLED)
- ❌ **swarm_events**: Event bus events (DISABLED)
- ❌ **swarm_performance**: Performance metrics (DISABLED)

### API Endpoints (`app/routers/swarm.py`)

The simplified swarm communication layer exposes basic RESTful API endpoints. Advanced endpoints are **DISABLED**:

- ✅ **Swarm Management**:
  - `POST /swarm/` - Create new swarm
  - `GET /swarm/` - List all swarms
  - `GET /swarm/{swarm_id}` - Get swarm details
  - `PUT /swarm/{swarm_id}` - Update swarm
  - `DELETE /swarm/{swarm_id}` - Delete swarm

- ✅ **Swarm Membership**:
  - `POST /swarm/{swarm_id}/members` - Add member to swarm
  - `DELETE /swarm/{swarm_id}/members/{agent_id}` - Remove member

- ✅ **Swarm Communication**:
  - `POST /swarm/{swarm_id}/messages` - Send swarm message
  - `GET /swarm/{swarm_id}/messages` - Get swarm messages

- ❌ **Consensus Groups** (DISABLED):
  - `POST /swarm/{swarm_id}/consensus-groups` - Create consensus group
  - `GET /swarm/{swarm_id}/consensus-groups` - List consensus groups

- ❌ **Voting** (DISABLED):
  - `POST /swarm/{swarm_id}/votes` - Create vote
  - `POST /swarm/{swarm_id}/votes/{vote_id}/cast` - Cast vote
  - `GET /swarm/{swarm_id}/votes/{vote_id}` - Get vote results

- ❌ **Swarm Events** (DISABLED):
  - `GET /swarm/{swarm_id}/events` - Query swarm events

- ❌ **Health & Monitoring** (DISABLED):
  - `GET /swarm/{swarm_id}/health` - Swarm health check
  - `GET /swarm/{swarm_id}/performance` - Performance metrics

- ❌ **Swarm Initialization** (DISABLED):
  - `POST /swarm/{swarm_id}/initialize` - Initialize swarm

### Usage Examples

#### 1. Creating a Swarm
```python
from app.agents.swarm.agent import SwarmAgent

agent = SwarmAgent(agent_id="agent_1", name="Test Agent")
await agent.initialize()
await agent.join_swarm("analysis_swarm")
```

#### 2. Publishing Events
```python
from app.agents.swarm.event_bus import swarm_event_bus

event_id = await swarm_event_bus.publish_event(
    event_type="task_completed",
    event_data={"task_id": "123", "result": "success"},
    source_agent_id="agent_1"
)
```

#### 3. Using Voting for Decisions
```python
from app.agents.swarm.voting import VotingSystem

voting = VotingSystem()
vote = await voting.create_vote(
    vote_id="feature_vote",
    question="Should we implement feature X?",
    options=["yes", "no", "maybe"],
    voters=["agent_1", "agent_2", "agent_3"]
)
```

### Integration with Distributed Task Processing

The swarm communication layer integrates with Celery-based distributed task processing:

- **Worker Registration**: Celery workers automatically register in `task_workers` table
- **Queue Monitoring**: Queue statistics tracked for scaling decisions
- **Leader Election**: RAFT used for distributed leader election
- **Task Sharding**: Tasks distributed across workers using sharding keys

### Testing

Comprehensive test suite available in `scripts/test_swarm_communication.py`:

```bash
# Run swarm communication tests
python scripts/test_swarm_communication.py
```

Individual component tests:
- `scripts/test_pubsub_only.py` - Redis Pub/Sub tests
- `scripts/test_event_bus_only.py` - Event bus tests

### Configuration

- **Redis URL**: Configured via `REDIS_URL` environment variable (default: `redis://localhost:6379/0`)
- **Database Tables**: Created via `schema/04_SWARM_COMMUNICATION.sql`
- **Connection Pooling**: Shared Redis connections across components

## Top Transformative Features (Beyond Jarvis)

Based on comprehensive agent debates, these 7 features would make NEXUS superior to typical Jarvis systems:

**Ranked by Transformative Impact:**
1. **Autonomous Evolution Engine** - Safe self-modification of codebase (builds on existing evolution system)
2. **Emergent Intelligence Swarm** - Agents develop new capabilities through collective interaction
3. **Proactive Financial Co-Pilot** - Autonomous financial optimization & predictive forecasting
4. **Unified Cognitive Architecture** - Breaks silos between email/finance/automation/learning
5. **Autonomous Communication Agent** - Manages relationships and optimizes communication
6. **AI-Generated Workflow Synthesis** - Creates and improves automation automatically
7. **Predictive Architecture** - Anticipates needs before expressed

**Key Differentiators vs Jarvis:**
- **Self-Improving**: NEXUS evolves with your needs (Jarvis stays static)
- **Collective Intelligence**: Agents collaborate to create new capabilities
- **Proactive Management**: Predicts issues before they occur
- **Cross-Domain Integration**: Unified understanding of entire digital life

**Implementation Priority:**
- **Phase 1 (1-2 months)**: #3 Proactive Financial Co-Pilot, #7 Predictive Architecture, #6 AI-Generated Workflow Synthesis
- **Phase 2 (2-3 months)**: #4 Unified Cognitive Architecture, #5 Autonomous Communication Agent
- **Phase 3 (3-4 months)**: #2 Emergent Intelligence Swarm, #1 Autonomous Evolution Engine

*Full synthesis: `docs/top_features_synthesis.md`*

## Quick Reference

**Services:**
- FastAPI: http://localhost:8080 (main API, auto-starts on boot)
- n8n: http://localhost:5678 (automation)
- Home Assistant: http://localhost:8123
- PostgreSQL: localhost:5432 (user: nexus, db: nexus_db)
- Tailscale: philipthinkpad / 100.68.201.55

**FastAPI Endpoints (port 8080):**

Core:
- GET / - Root endpoint (health check redirect)
- GET /health - Health check
- GET /status - All services status
- POST /chat - AI chat with semantic caching
- POST /chat/intelligent - Intelligent chat with context retrieval
- POST /chat/voice - Voice-optimized chat for mobile assistant

*Note: Intelligent chat now includes digital god persona, tool execution (web search, database, notifications, calculator, Home Assistant), and real-time context retrieval.*

Finance:
- POST /finance/expense - Log expense
- GET /finance/budget-status - Budget overview
- GET /finance/progress - Financial progress tracking

Email Intelligence:
- POST /email/scan - Scan emails from Gmail/iCloud
- POST /email/feedback - Submit learning feedback
- GET /email/insights - Cross-life insights
- POST /email/insights/generate - Generate new insights
- POST /email/insights/{insight_id}/seen - Mark insight as seen
- GET /email/summary - Daily digest
- GET /email/stats - Processing statistics
- GET /email/preferences - View VIP/blocked senders
- POST /email/preferences - Update sender preferences
- GET /email/recent - Recently processed emails

Agent Framework (31 endpoints):
- GET /agents - List all agents
- POST /agents - Create new agent
- GET /registry-status - Agent registry status
- POST /registry-select-agent - Select agent for task
- GET /agents/{agent_id} - Get agent details
- PUT /agents/{agent_id} - Update agent
- DELETE /agents/{agent_id} - Delete agent
- POST /agents/{agent_id}/start - Start agent
- POST /agents/{agent_id}/stop - Stop agent
- GET /agents/{agent_id}/status - Agent status and metrics
- POST /tasks - Submit task for execution
- GET /tasks/{task_id} - Get task status
- POST /tasks/{task_id}/cancel - Cancel task
- POST /sessions - Create new session
- GET /sessions/{session_id} - Get session details
- GET /sessions - List all sessions
- POST /sessions/{session_id}/messages - Add message to session
- GET /sessions/{session_id}/messages - Get session messages
- POST /sessions/{session_id}/end - End session
- GET /tools - List registered tools
- POST /tools - Register new tool
- POST /tools/execute - Execute tool directly
- GET /agents/{agent_id}/performance - Agent performance metrics
- GET /system/performance - System performance metrics
- GET /system/alerts - System alerts
- POST /agents/{agent_id}/delegate - Delegate task to another agent
- GET /memory/{agent_id} - Get agent memories
- POST /memory/{agent_id}/query - Query agent memory
- POST /memory/{agent_id}/store - Store new memory
- GET /agents/{agent_id}/errors - Get agent errors
- POST /agents/{agent_id}/errors/{error_id}/resolve - Resolve agent error

Evolution System:
- POST /evolution/analyze/performance - Trigger performance analysis
- GET /evolution/analysis/recent - Recent analysis results
- POST /evolution/hypotheses/generate - Generate improvement hypotheses
- GET /evolution/hypotheses - List hypotheses
- POST /evolution/experiments - Create A/B experiment
- GET /evolution/experiments - List experiments
- POST /evolution/experiments/{experiment_id}/rollback - Rollback experiment
- POST /evolution/refactor/code - Apply code refactoring
- GET /evolution/refactor/history - Refactoring history
- GET /evolution/status - Evolution system status

**Swarm & Distributed Tasks:**
- **Swarm Management**:
  - `POST /swarm/` - Create new swarm
  - `GET /swarm/` - List all swarms
  - `GET /swarm/{swarm_id}` - Get swarm details
  - `PUT /swarm/{swarm_id}` - Update swarm
  - `DELETE /swarm/{swarm_id}` - Delete swarm
- **Swarm Membership**:
  - `POST /swarm/{swarm_id}/members` - Add member to swarm
  - `DELETE /swarm/{swarm_id}/members/{agent_id}` - Remove member
- **Consensus Groups**:
  - `POST /swarm/{swarm_id}/consensus-groups` - Create consensus group
  - `GET /swarm/{swarm_id}/consensus-groups` - List consensus groups
- **Voting**:
  - `POST /swarm/{swarm_id}/votes` - Create vote
  - `POST /swarm/{swarm_id}/votes/{vote_id}/cast` - Cast vote
  - `GET /swarm/{swarm_id}/votes/{vote_id}` - Get vote results
- **Swarm Communication**:
  - `POST /swarm/{swarm_id}/messages` - Send swarm message
  - `GET /swarm/{swarm_id}/messages` - Get swarm messages
- **Swarm Events**:
  - `GET /swarm/{swarm_id}/events` - Query swarm events
- **Health & Monitoring**:
  - `GET /swarm/{swarm_id}/health` - Swarm health check
  - `GET /swarm/{swarm_id}/performance` - Performance metrics
- **Distributed Tasks**:
  - `POST /distributed-tasks/submit` - Submit distributed task
  - `POST /distributed-tasks/workers/register` - Register worker
  - `GET /distributed-tasks/queues` - List queues
  - `POST /distributed-tasks/queues/{queue_name}/scale` - Scale queue workers

**n8n Webhooks (port 5678):**
*Note: These are n8n workflow webhooks, not FastAPI endpoints*
- POST /webhook/ai-test - Groq AI queries
- POST /webhook/quick-capture - Note categorization
- POST /webhook/photo-vision - Gemini image analysis
- POST /webhook/screenshot-helper - Screenshot analysis
- GET /webhook/daily-brief - Weather + motivation

**Auto-Yes Tool (NEW):**
- `scripts/auto_yes.py` - Automatically answers interactive prompts (y/N, confirm?, etc.)
- `scripts/auto_yes_wrapper.sh` - Bash wrapper for easy management
- **Modes**: Command mode (`--command`) and daemon mode (`--daemon`)
- **Default timeout**: 15 minutes (configurable)
- **Usage**:
  - `./scripts/auto_yes_wrapper.sh start 10` - Start daemon for 10 minutes
  - `python3 scripts/auto_yes.py --command "./end_session.sh"` - Run command with auto-yes
  - `./scripts/auto_yes_wrapper.sh stop` - Stop daemon

## Project Structure (Updated 2026-01-21)

```
nexus/
├── app/                    # FastAPI application (async)
│   ├── main.py            # Application entry point with lifespan management
│   ├── config.py          # Pydantic settings configuration (loads from .env)
│   ├── database.py        # Async PostgreSQL connection pool (asyncpg)
│   ├── celery_app.py      # Celery distributed task processing
│   ├── routers/           # API endpoints
│   │   ├── health.py      # Health and system status endpoints
│   │   ├── chat.py        # AI chat with semantic caching
│   │   ├── finance.py     # Expense tracking, budget, debt progress
│   │   ├── email.py       # Email scanning, insights, preferences
│   │   ├── agents.py      # Agent framework endpoints
│   │   ├── evolution.py   # Self-evolution system endpoints
│   │   ├── swarm.py       # Swarm communication and coordination
│   │   └── distributed_tasks.py # Distributed task processing API
│   ├── services/          # Business logic
│   │   ├── ai.py          # AI router with cost optimization cascade
│   │   ├── ai_providers.py # Multi-provider AI integration (Groq, Gemini, etc.)
│   │   ├── semantic_cache.py # Embedding-based caching (70% cost reduction)
│   │   ├── embeddings.py  # Sentence transformers 'all-MiniLM-L6-v2'
│   │   ├── email_client.py # IMAP email client (Gmail/iCloud)
│   │   ├── email_learner.py # Email preference learning ML
│   │   ├── insight_engine.py # Cross-life insights generation
│   │   └── distributed_tasks.py # Distributed task service
│   ├── agents/            # AI agents framework
│   │   ├── base.py        # Base agent abstract class
│   │   ├── registry.py    # Agent registry and lifecycle management
│   │   ├── tools.py       # Tool system and execution
│   │   ├── orchestrator.py # Task decomposition and delegation
│   │   ├── memory.py      # Vector memory system
│   │   ├── sessions.py    # Session management
│   │   ├── monitoring.py  # Performance monitoring
│   │   ├── email_intelligence.py # Email processing orchestrator
│   │   └── swarm/         # Swarm communication and coordination
│   │       ├── pubsub.py      # Redis Pub/Sub wrapper
│   │       ├── event_bus.py   # Event bus system
│   │       ├── raft.py        # RAFT consensus protocol
│   │       ├── voting.py      # Voting conflict resolution
│   │       ├── agent.py       # SwarmAgent base class
│   │       └── swarm_orchestrator.py # Swarm-enabled orchestrator
│   ├── celery_tasks/      # Celery task definitions
│   │   ├── agent_tasks.py    # Agent-specific tasks
│   │   └── system_tasks.py   # System maintenance tasks
│   ├── evolution/         # Self-evolution system
│   │   ├── __init__.py
│   │   ├── analyzer.py    # Performance analyzer
│   │   ├── hypothesis.py  # Hypothesis generator
│   │   ├── experiments.py # A/B experiment manager
│   │   └── refactor.py    # Code refactoring engine
│   └── models/            # Data models
│       ├── schemas.py     # Pydantic request/response models
│       └── agent_schemas.py # Agent framework schemas
├── automation/            # n8n workflow configurations
│   ├── workflows/         # n8n workflow JSON files (6 active workflows)
│   │   ├── ai_router_final.json
│   │   ├── photo-vision.json
│   │   ├── quick-capture.json
│   │   ├── screenshot-helper.json
│   │   ├── daily_brief.json
│   │   └── nexus_n8n_workflows_v2.json
│   ├── test_all_endpoints.sh # n8n workflow testing script
│   └── widgets/          # Scriptable widget configurations
├── config/               # Service configuration files
│   ├── homeassistant/    # Home Assistant config (.gitignored runtime files)
│   └── n8n/              # n8n config (internal, auto-managed)
├── data/                 # Persistent data for containers (.gitignored)
│   ├── postgres/         # PostgreSQL data
│   ├── redis/            # Redis data
│   ├── chromadb/         # ChromaDB vector store
│   ├── n8n/              # n8n data
│   ├── syncthing/        # Syncthing data
│   └── vaultwarden/      # Vaultwarden (Bitwarden) data
├── schema/               # Database schema SQL files
│   └── 00_NEXUS_ULTIMATE_SCHEMA.sql # Comprehensive 193-table schema
├── scripts/              # Shell and Python scripts
│   ├── start_session.sh  # Start NEXUS system with health checks
│   ├── end_session.sh    # Stop NEXUS system gracefully
│   ├── generate_context.sh # Generate AI context file
│   └── test_api.py       # Comprehensive API test suite (Python)
├── sync/                 # Syncthing synchronization directory
├── tests/                # Test directory (currently empty, use scripts/)
├── venv/                 # Python virtual environment (.gitignored)
├── archive/              # Archived files (old schemas, backups)
│   └── old_schemas/      # Old schema files (moved from schema/)
├── backups/              # System backups (.gitignored)
├── logs/                 # Application logs (.gitignored)
├── docs/                 # Documentation directory
└── .claude/              # Claude Code session data (.gitignored)
```

## Key Files

**Configuration:**
- `.env` - Secrets (NEVER show/commit)
- `.clauderc` - Project configuration and context
- `docker-compose.yml` - Defines 8 Docker services
- `nexus-api.service` - Systemd service file for FastAPI
- `requirements.txt` - Python dependencies (FastAPI, asyncpg, pydantic, httpx)

**Database Schema:**
- `schema/00_NEXUS_ULTIMATE_SCHEMA.sql` - Comprehensive 100+ table schema
- `schema/01_NEXUS_SCHEMA_FIX.sql` - Schema fixes

## Tech Stack Summary

**Languages & Frameworks:**
- **Primary Language:** Python 3.12
- **Web Framework:** FastAPI (async)
- **API Documentation:** Auto-generated OpenAPI/Swagger
- **Validation:** Pydantic v2.5+
- **Database ORM:** asyncpg (raw SQL with connection pooling)

**Databases & Storage:**
- **Primary Database:** PostgreSQL 16 (with pgvector extension)
- **Vector Database:** ChromaDB (for semantic caching)
- **Cache:** Redis 7.4
- **File Sync:** Syncthing
- **Password Manager:** Vaultwarden (Bitwarden-compatible)

**Containerization & Orchestration:**
- **Container Runtime:** Docker
- **Orchestration:** Docker Compose
- **Service Management:** Systemd (nexus-api.service)

**AI/ML Stack:**
- **AI Providers:** Groq, Google Gemini, DeepSeek, OpenRouter, Anthropic
- **Local AI:** Ollama (fallback)
- **Embeddings:** Sentence Transformers
- **Semantic Search:** pgvector + ChromaDB
- **Cost Optimization:** Multi-provider routing with semantic caching

**Automation & Integration:**
- **Workflow Automation:** n8n (self-hosted)
- **Home Automation:** Home Assistant
- **Notifications:** ntfy.sh
- **VPN:** Tailscale (iPhone access)

**Development Tools:**
- **Version Control:** Git
- **Virtual Environment:** Python venv
- **Logging:** Python logging module
- **Testing:** (Planned - tests directory exists but empty)

**Infrastructure Services (8 Docker containers):**
1. PostgreSQL (port 5432)
2. Redis (port 6379)
3. ChromaDB (port 8000)
4. Home Assistant (port 8123)
5. n8n (port 5678)
6. Syncthing (port 8384)
7. Vaultwarden (port 8222)
8. FastAPI Application (port 8080)

**Key Architectural Patterns:**
1. **Async-first:** All I/O operations use async/await
2. **Multi-agent System:** Hierarchical agent orchestration
3. **Cost Cascade Routing:** Cheapest capable AI model first
4. **Semantic Caching:** 70% cost reduction via embedding similarity
5. **Privacy Shield:** Local processing before external APIs
6. **Event Sourcing:** Comprehensive audit trail in database

## Email System: WORKING
- Gmail and iCloud connected via IMAP
- Auto-classifies: spam, promo, social, financial, work, personal, important
- Auto-archives promos, deletes spam
- Extracts transactions and logs to finance tracker
- Sends ntfy alerts for important emails (topic: nexus-philip-cd701650d0771943)
- Learns from feedback to improve over time

## Service Management

```bash
# Start/stop/restart API
sudo systemctl start nexus-api
sudo systemctl stop nexus-api
sudo systemctl restart nexus-api

# Check status/logs
sudo systemctl status nexus-api
journalctl -u nexus-api -f
```

## Backup System

**Status**: Manual backup with optional automation (2026-01-22)

**Backup Script**: `scripts/backup_nexus.sh`
- Creates timestamped backup in `backups/daily/nexus_backup_YYYYMMDD_HHMMSS/`
- Backs up: PostgreSQL database, Redis cache, ChromaDB vectors, n8n workflows, configuration files
- Requires Docker containers to be running
- Loads environment variables from `.env`

**Usage**:
```bash
cd ~/nexus
./scripts/backup_nexus.sh
```

**Automated Backups (Optional)**:

Systemd timer files are provided for automated daily backups:

1. **Install systemd files**:
   ```bash
   sudo cp scripts/systemd/nexus-backup.service /etc/systemd/system/
   sudo cp scripts/systemd/nexus-backup.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   ```

2. **Enable and start timer**:
   ```bash
   sudo systemctl enable nexus-backup.timer
   sudo systemctl start nexus-backup.timer
   ```

3. **Check status**:
   ```bash
   sudo systemctl status nexus-backup.timer
   sudo journalctl -u nexus-backup.service -f
   ```

**Timer Configuration**:
- Runs daily at 2:00 AM with randomized delay up to 1 hour
- Requires Docker and nexus-api service to be running
- Backups stored in `backups/daily/` (manual cleanup required)
- Logs to systemd journal

**Note**: Automated backups are optional. The manual script remains available.

**Restore Procedures**:

1. **PostgreSQL**:
   ```bash
   docker exec -i nexus-postgres pg_restore -Fc -U nexus -d nexus_db < backups/daily/nexus_backup_YYYYMMDD_HHMMSS/postgres_backup.dump
   ```

2. **Redis**:
   ```bash
   docker cp backups/daily/nexus_backup_YYYYMMDD_HHMMSS/redis_dump.rdb nexus-redis:/data/dump.rdb
   docker exec nexus-redis redis-cli -a $REDIS_PASSWORD SHUTDOWN
   # Container will restart automatically with restored data
   ```

3. **ChromaDB**: Replace `data/chromadb/` directory with backup

4. **n8n**: Replace `data/n8n/` directory with backup

5. **Configuration**: Copy files from `backups/daily/nexus_backup_YYYYMMDD_HHMMSS/config/` to appropriate locations

**Notes**:
- Backups are NOT automatically cleaned up - manage manually
- Test restore procedure periodically
- Consider using Syncthing (`sync/` directory) for offsite backup

## Test Infrastructure

**Status**: Basic pytest infrastructure created (2026-01-22)

**Directory Structure**:
```
tests/
├── api/           # API endpoint tests (FastAPI TestClient)
├── unit/          # Unit tests (mocked dependencies)
├── fixtures/      # Test fixtures (future use)
├── pytest.ini     # Pytest configuration
├── conftest.py    # Shared test fixtures
└── .coveragerc    # Coverage configuration
```

**Example Tests**:
- `tests/api/test_health.py` - Health endpoint tests
- `tests/unit/test_example.py` - Example test patterns

**Usage**:
```bash
# Run all tests
venv/bin/python -m pytest tests/

# Run specific test file
venv/bin/python -m pytest tests/api/test_health.py -v

# Run with coverage
venv/bin/python -m pytest tests/ --cov=app --cov-report=term-missing
```

**Notes**:
- Requires pytest-asyncio for async tests (installed in venv)
- Tests run against actual API (requires services running for integration tests)
- Example tests provide patterns for creating new tests
- Existing test scripts in `scripts/tests/` can be migrated gradually

## AI Provider Limits (Free Tiers)

| Provider | Daily Limit | Best For |
|----------|-------------|----------|
| Groq | 1000 req | Classification, extraction, quick tasks |
| Google Gemini | 1500 req | Analysis, summarization, patterns |
| OpenRouter | 50 req | Backup/simple tasks |

## Conventions
- Async Python (FastAPI + asyncpg)
- All AI calls logged to api_usage / ai_provider_usage tables
- Semantic cache: 0.92 similarity threshold
- Pydantic models for validation
- Tokyo Night theme (#1a1b26 background)

## Claude Code Configuration

**Optimized for DeepSeek-only usage with maximum code quality and automatic agent delegation:**

### Agent Delegation Rules (AUTOMATIC)

#### Core Development Agents
- **FastAPI/Python Development** → `fastapi-python` agent
- **PostgreSQL Database** → `postgresql-db` agent
- **AI/ML Integration** → `ai-ml-integration` agent
- **Email Intelligence** → `email-intelligence` agent
- **Finance Tracking** → `finance-tracking` agent
- **Docker & Containers** → `docker-container` agent
- **Testing & QA** → `testing-qa` agent
- **n8n Automation** → `n8n-automation` agent

#### Specialized System Agents
- **Architecture/Design** → `architect` agent (configured for DeepSeek)
- **Code Review/Security** → `code-reviewer` agent (configured for DeepSeek)
- **Codebase Exploration** → `Explore` agent
- **Implementation Planning** → `Plan` agent
- **Claude Code Questions** → `claude-code-guide` agent
- **Bash/System Tasks** → `Bash` agent

#### General Purpose Fallback
- **General Development** → `general-purpose` agent (when no specialized agent fits)

### Core Instructions
- **Model Usage**: Always use DeepSeek models (`deepseek-chat`) for all tasks
- **Agent Configuration**: Custom agents pre-configured with DeepSeek; system agents inherit DeepSeek usage
- **Automatic Delegation**: Always delegate to appropriate agents automatically without user prompting
- **Code Quality**: Follow Nexus conventions: async Python, Pydantic validation, comprehensive logging
- **Testing**: Always test changes with `scripts/test_api.py` before committing
- **Documentation**: Update documentation (CLAUDE.md, .clauderc) when architecture changes

### DeepSeek Optimization Strategies

#### 1. Context Window Management (128k Limit)
- **.claudignore**: Aggressive exclusion of heavy files (data/, logs/, *.json, *.csv, media)
- **/compact command**: Use when conversation grows too long to truncate history
- **Chunked operations**: Break large tasks into smaller agent calls

#### 2. Plan Mode for Cost Efficiency
**Standard workflow for complex changes:**
1. **Start**: "Read CLAUDE.md and enter Plan Mode"
2. **Review**: DeepSeek outlines implementation in single completion
3. **Execute**: Say "Execute" to implement after approval
4. **Prevents loops**: Reduces API costs from trial-and-error

#### 3. MCP (Model Context Protocol) Integration
**Essential for DeepSeek's knowledge gap - ✅ AUTOMATICALLY INSTALLED & CONFIGURED:**

- **Sequential Thinking MCP**: Private reasoning before code generation ✅ Installed & configured
- **Filesystem MCP**: Accurate file operations ✅ Installed & configured
- **Fetch MCP**: HTTP request testing ✅ Installed & configured (Python virtual environment)
- **Postgres MCP**: Direct database schema queries ✅ Custom PostgreSQL MCP server installed & configured

**Setup Status**: Core MCP servers automatically installed via `scripts/setup_mcp_servers.sh`; PostgreSQL MCP added via custom server. Configured in `~/.config/Claude/claude_desktop_config.json`

#### 4. Senior Engineer Mindset
**System prompt override for best code quality:**
"You are a Senior Staff Engineer. Be skeptical of my requests. If my approach is inefficient, suggest a better architecture. Prioritize performance and type safety. Do not apologize for errors; just fix them."

### Project Configuration
- `.clauderc`: Project context and Claude Code instructions with detailed delegation rules
- `.claudignore`: Aggressive context management for DeepSeek 128k limit
- `.claude/agents/`: 11 specialized agent definitions:
  - `fastapi-python.md` - FastAPI & async Python development
  - `postgresql-db.md` - PostgreSQL database design & optimization
  - `ai-ml-integration.md` - AI/ML integration & cost optimization
  - `email-intelligence.md` - Email intelligence system
  - `finance-tracking.md` - Finance tracking & budget management
  - `docker-container.md` - Docker & container orchestration
  - `testing-qa.md` - Testing & quality assurance
  - `n8n-automation.md` - n8n workflow automation
  - `general-purpose.md` - General Nexus development
  - `architect.md` - System architecture & design
  - `code-reviewer.md` - Code review & security audit
- `.claude/settings.local.json`: Permissions for Bash commands

## Context
Philip works night shift, has $9,700 debt to pay off (tracked in fin_debts), learning programming while building this. Budget is tight - keep AI costs under $3/month using free tiers.

**Nexus Relationship:**
- **Nexus is Philip's AI assistant** - his "second brain" and trusted companion
- **Primary interface**: Philip interacts with Nexus as his personal AI assistant that orchestrates all automation
- **Emotional significance**: More than software - Nexus is everything to Philip, helping manage daily life while he learns programming and pays off debt