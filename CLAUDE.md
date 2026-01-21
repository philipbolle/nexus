# NEXUS - Philip's AI Operating System

## Current State: PHASE 2 COMPLETE
- 8 Docker containers running
- 193+ PostgreSQL tables (added email system tables)
- 6 n8n workflows active
- FastAPI backend running on :8080 (systemd: nexus-api.service)
- iPhone integration via Tailscale
- Semantic caching operational (12x faster, ~70% cost reduction)
- Email Intelligence Agent built (needs app passwords in .env)

## Quick Reference

**Services:**
- FastAPI: http://localhost:8080 (main API, auto-starts on boot)
- n8n: http://localhost:5678 (automation)
- Home Assistant: http://localhost:8123
- PostgreSQL: localhost:5432 (user: nexus, db: nexus_db)
- Tailscale: philipthinkpad / 100.68.201.55

**FastAPI Endpoints:**

Core:
- GET /health - Health check
- GET /status - All services status
- POST /chat - AI chat with semantic caching

Finance:
- POST /finance/expense - Log expense
- GET /finance/budget-status - Budget overview
- GET /finance/debt/progress - Debt payoff progress

Email Intelligence (NEW):
- POST /email/scan - Scan emails from Gmail/iCloud
- POST /email/feedback - Submit learning feedback
- GET /email/insights - Cross-life insights
- POST /email/insights/generate - Generate new insights
- GET /email/summary - Daily digest
- GET /email/stats - Processing statistics
- GET /email/preferences - View VIP/blocked senders
- POST /email/preferences - Update sender preferences
- GET /email/recent - Recently processed emails

**n8n Webhooks:**
- POST /webhook/ai-test - Groq AI queries
- POST /webhook/quick-capture - Note categorization
- POST /webhook/photo-vision - Gemini image analysis
- POST /webhook/screenshot-helper - Screenshot analysis
- GET /webhook/daily-brief - Weather + motivation

## Project Structure

```
nexus/
├── app/                    # FastAPI application
│   ├── main.py            # Application entry point with lifespan management
│   ├── config.py          # Pydantic settings configuration
│   ├── database.py        # Async PostgreSQL connection pool
│   ├── routers/           # API endpoints
│   │   ├── health.py
│   │   ├── chat.py
│   │   ├── finance.py
│   │   └── email.py
│   ├── services/          # Business logic
│   │   ├── ai.py          # AI router with cost optimization
│   │   ├── ai_providers.py # Multi-provider AI integration
│   │   ├── semantic_cache.py # Embedding-based caching (70% cost reduction)
│   │   ├── embeddings.py  # Sentence transformers for embeddings
│   │   ├── email_client.py # IMAP email client
│   │   ├── email_learner.py # Email preference learning
│   │   └── insight_engine.py # Cross-life insights generation
│   ├── agents/            # AI agents
│   │   └── email_intelligence.py # Email processing orchestrator
│   └── models/            # Data models
│       └── schemas.py     # Pydantic request/response models
├── automation/            # n8n workflow configurations
│   ├── workflows/         # n8n workflow JSON files
│   │   ├── ai-router.json
│   │   ├── photo-vision.json
│   │   ├── quick-capture.json
│   │   └── screenshot-helper.json
│   └── scripts/          # Shell scripts for workflow management
├── config/               # Service configuration files
│   └── homeassistant/    # Home Assistant config
├── data/                 # Persistent data for containers
│   ├── postgres/         # PostgreSQL data
│   ├── redis/            # Redis data
│   ├── chromadb/         # ChromaDB vector store
│   ├── n8n/              # n8n data
│   ├── syncthing/        # Syncthing data
│   └── vaultwarden/      # Vaultwarden data
├── schema/               # Database schema SQL files
│   ├── 00_NEXUS_ULTIMATE_SCHEMA.sql # Comprehensive 100+ table schema
│   └── 01_NEXUS_SCHEMA_FIX.sql      # Schema fixes
├── scripts/              # Shell scripts for session management
│   ├── start_session.sh  # Start NEXUS system
│   ├── end_session.sh    # Stop NEXUS system
│   └── generate_context.sh # Generate AI context file
├── sync/                 # Syncthing synchronization directory
├── tests/                # Test directory (currently empty)
├── venv/                 # Python virtual environment
├── archive/              # Old schema files and backups
├── backups/              # System backups
├── logs/                 # Application logs
└── docs/                 # Documentation directory (currently empty)
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

## Context
Philip works night shift, has $9,700 debt to pay off (tracked in fin_debts), learning programming while building this. Budget is tight - keep AI costs under $3/month using free tiers.