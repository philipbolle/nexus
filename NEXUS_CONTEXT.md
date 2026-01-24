# NEXUS Project Context
> Auto-generated: 2026-01-24 02:37:10
> Copy this entire file and paste it into any AI (Gemini, Grok, ChatGPT, DeepSeek)

## What is NEXUS?

NEXUS is Philip's personal AI operating system - a self-hosted system that manages his entire life through AI agents. It runs on his Ubuntu laptop (ThinkPad T14, 8GB RAM) and is accessible via Tailscale VPN from his iPhone.

## Current System State

- **PostgreSQL Tables**: 223
- **Docker Containers**: 7 running
- **Containers**: nexus-homeassistant: Up 38 hours,nexus-n8n: Up 38 hours,nexus-chromadb: Up 38 hours,nexus-postgres: Up 38 hours (healthy),nexus-syncthing: Up 38 hours (healthy),nexus-vaultwarden: Up 38 hours (healthy),nexus-redis: Up 38 hours,
- **Python Files**: 70 in app/
- **Git Branch**: main
- **Last Commit**: 64284de session(2026-01-24): Updated: philip-tasks,

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

),/,/agents,/agents/{agent_id},/agents/{agent_id}/delegate,/agents/{agent_id}/errors,/agents/{agent_id}/errors/{error_id}/resolve,/agents/{agent_id}/performance,/agents/{agent_id}/start,/agents/{agent_id}/status,/agents/{agent_id}/stop,/budget-status,/cleanup,/debt/progress,/evolution/analysis/recent,/evolution/analyze/performance,/evolution/experiments,/evolution/experiments/{experiment_id}/rollback,/evolution/hypotheses,/evolution/hypotheses/generate,/evolution/refactor/code,/evolution/refactor/history,/evolution/status,/expense,/feedback,Get autonomous monitoring status,/health,/health/detailed,/insights,/insights/generate,

## Database Tables (First 50)

accounts,agent_collaborations,agent_events,agent_experiments,agent_handoffs,agent_learnings,agent_performance,agent_performance_metrics,agent_suggestions,agent_tool_assignments,agent_tools,agent_versions,agents,agents_backup,ai_models,ai_provider_usage,ai_providers,api_keys,api_usage,archives,areas,audit_trail,backup_logs,batch_job_items,batch_jobs,bottleneck_patterns,budgets,car_fuel_logs,car_insurance,car_maintenance_history,car_maintenance_schedule,car_mileage_logs,car_registration,car_vehicles,cascade_decisions,chunking_configs,code_quality_metrics,communication_templates,compound_time_savings,consensus_groups,consensus_log_entries,contact_interactions,contacts,context_snapshots,conversations,cost_alerts,credentials,curriculum,debt_payments,debts,,

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

