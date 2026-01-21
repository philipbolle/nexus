#!/bin/bash
# NEXUS Context Generator
# Generates a single file you can paste into ANY AI (Gemini, Grok, ChatGPT, DeepSeek)

NEXUS_DIR=~/nexus
OUTPUT_FILE="$NEXUS_DIR/NEXUS_CONTEXT.md"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "Generating NEXUS context..."

# Get current system state
TABLE_COUNT=$(docker exec nexus-postgres psql -U nexus -d nexus_db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ' || echo "?")
CONTAINER_COUNT=$(docker ps --format "{{.Names}}" | wc -l)
CONTAINER_LIST=$(docker ps --format "{{.Names}}: {{.Status}}" 2>/dev/null | tr '\n' ', ' | sed 's/, $//')

# Get git info
GIT_BRANCH=$(cd $NEXUS_DIR && git branch --show-current 2>/dev/null || echo "unknown")
LAST_COMMIT=$(cd $NEXUS_DIR && git log --oneline -1 2>/dev/null || echo "no commits")

# Get Python files count
PY_FILES=$(find $NEXUS_DIR/app -name "*.py" 2>/dev/null | wc -l)

# Get API endpoints from FastAPI
ENDPOINTS=""
if [ -d "$NEXUS_DIR/app/routers" ]; then
    ENDPOINTS=$(grep -r "@router\.\(get\|post\|put\|delete\)" $NEXUS_DIR/app/routers/ 2>/dev/null | grep -oP '"\K[^"]+' | sort -u | head -30 | tr '\n' ', ' | sed 's/, $//')
fi

# Get table names (first 50)
TABLE_NAMES=$(docker exec nexus-postgres psql -U nexus -d nexus_db -t -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename LIMIT 50;" 2>/dev/null | tr -d ' ' | tr '\n' ', ' | sed 's/, $//' || echo "unable to fetch")

# Generate the context file
cat > "$OUTPUT_FILE" << 'CONTEXT_START'
# NEXUS Project Context
> Auto-generated: TIMESTAMP_PLACEHOLDER
> Copy this entire file and paste it into any AI (Gemini, Grok, ChatGPT, DeepSeek)

## What is NEXUS?

NEXUS is Philip's personal AI operating system - a self-hosted system that manages his entire life through AI agents. It runs on his Ubuntu laptop (ThinkPad T14, 8GB RAM) and is accessible via Tailscale VPN from his iPhone.

## Current System State

- **PostgreSQL Tables**: TABLE_COUNT_PLACEHOLDER
- **Docker Containers**: CONTAINER_COUNT_PLACEHOLDER running
- **Containers**: CONTAINER_LIST_PLACEHOLDER
- **Python Files**: PY_FILES_PLACEHOLDER in app/
- **Git Branch**: GIT_BRANCH_PLACEHOLDER
- **Last Commit**: LAST_COMMIT_PLACEHOLDER

## Tech Stack

- **Backend**: FastAPI (Python 3.12, async)
- **Database**: PostgreSQL 16 with 193 tables
- **Cache**: Redis 7.4
- **Vector DB**: ChromaDB
- **Automation**: n8n workflows
- **Home Integration**: Home Assistant
- **File Sync**: Syncthing
- **Passwords**: Vaultwarden
- **Network**: Tailscale VPN (100.68.201.55)

## Key Services & Ports

| Service | Port | URL |
|---------|------|-----|
| FastAPI | 8080 | http://localhost:8080 |
| n8n | 5678 | http://localhost:5678 |
| Home Assistant | 8123 | http://localhost:8123 |
| PostgreSQL | 5432 | localhost:5432 |
| Redis | 6379 | localhost:6379 |
| ChromaDB | 8000 | http://localhost:8000 |
| Syncthing | 8384 | http://localhost:8384 |
| Vaultwarden | 8222 | http://localhost:8222 |

## API Endpoints

ENDPOINTS_PLACEHOLDER

## Database Tables (First 50)

TABLE_NAMES_PLACEHOLDER

## Project Structure
~/nexus/
├── app/                    # FastAPI application
│   ├── main.py            # Entry point
│   ├── config.py          # Settings
│   ├── database.py        # PostgreSQL connection
│   ├── routers/           # API endpoints
│   ├── services/          # Business logic
│   └── agents/            # AI agents
├── automation/            # n8n workflows
├── config/                # Service configs
├── data/                  # Docker volumes
├── docs/                  # Documentation
├── schema/                # SQL schema (00_NEXUS_ULTIMATE_SCHEMA.sql)
├── scripts/               # Automation scripts
├── tests/                 # Test files
├── docker-compose.yml     # Container config
├── requirements.txt       # Python deps
├── CLAUDE.md             # Claude Code context
└── NEXUS_CONTEXT.md      # This file (for any AI)
## Philip's Context

- Works night shift (janitor), learning programming
- Paying off $9,700 debt to mom
- Budget: Keep AI costs under $3/month
- Uses free tiers: Groq, Gemini, OpenRouter
- iPhone 12 on iOS, Apple Watch
- Tokyo Night theme preference (#1a1b26)

## AI Provider Strategy

| Provider | Use For | Daily Limit |
|----------|---------|-------------|
| Groq | Classification, quick tasks | 1000 req (free) |
| Gemini | Analysis, summarization | 1500 req (free) |
| DeepSeek | Code generation | Pay per use (~$0.001/req) |
| OpenRouter | Backup | 50 req (free) |

## Code Conventions

- Async everywhere (asyncpg, httpx)
- Pydantic models for validation
- Repository pattern for database
- All AI calls logged to api_usage table
- Semantic caching with 0.92 similarity threshold

## How to Help

When working on NEXUS:
1. Provide copy-paste ready code
2. Use async Python patterns
3. Keep costs minimal (free tiers first)
4. Follow existing patterns in the codebase
5. Be specific with file paths

## Current Goals

- Build wealth tracking agents
- Automate email management
- Create learning system (Neural Academy)
- Pay off debt faster

CONTEXT_START

# Replace placeholders
sed -i "s/TIMESTAMP_PLACEHOLDER/$TIMESTAMP/g" "$OUTPUT_FILE"
sed -i "s/TABLE_COUNT_PLACEHOLDER/$TABLE_COUNT/g" "$OUTPUT_FILE"
sed -i "s/CONTAINER_COUNT_PLACEHOLDER/$CONTAINER_COUNT/g" "$OUTPUT_FILE"
sed -i "s|CONTAINER_LIST_PLACEHOLDER|$CONTAINER_LIST|g" "$OUTPUT_FILE"
sed -i "s/PY_FILES_PLACEHOLDER/$PY_FILES/g" "$OUTPUT_FILE"
sed -i "s/GIT_BRANCH_PLACEHOLDER/$GIT_BRANCH/g" "$OUTPUT_FILE"
sed -i "s|LAST_COMMIT_PLACEHOLDER|$LAST_COMMIT|g" "$OUTPUT_FILE"
sed -i "s|ENDPOINTS_PLACEHOLDER|$ENDPOINTS|g" "$OUTPUT_FILE"
sed -i "s|TABLE_NAMES_PLACEHOLDER|$TABLE_NAMES|g" "$OUTPUT_FILE"

echo "✅ Generated: $OUTPUT_FILE"
echo "   Tables: $TABLE_COUNT | Containers: $CONTAINER_COUNT | Python files: $PY_FILES"
