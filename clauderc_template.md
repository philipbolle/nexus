# NEXUS - Autonomous AI Operating System
# Owner: Philip (pbolle123@gmail.com)
# Location: ~/nexus on PhilipThinkpad (100.68.201.55)

## Tech Stack
- **Backend:** Python 3.12 + FastAPI (async)
- **Database:** PostgreSQL 16 + ChromaDB + Redis
- **Containers:** Docker Compose (8 services)
- **AI Providers:** Ollama (local) → Groq (free) → DeepSeek → Anthropic
- **Automation:** n8n + Home Assistant + Cron
- **Interfaces:** iPhone Shortcuts, Scriptable widgets, Ubuntu desktop

## Architecture Pattern
- **Multi-agent orchestration** with hierarchical supervision
- **Privacy Shield** intercepts all queries, redacts secrets locally via Ollama
- **Cost cascade routing:** always use cheapest capable model first
- **Event sourcing** for complete audit trail
- **Semantic caching** for 60-70% cost reduction

## Database
- **186 tables** across 14 domains (finance, health, learning, etc.)
- Schema location: `schema/`
- Critical fix needed: `schema/01_NEXUS_SCHEMA_FIX.sql`
- Uses **UUID primary keys** throughout
- PostgreSQL container: `nexus-postgres`

## Key Files
- `app/main.py` - FastAPI entry point (port 8080)
- `app/services/` - Business logic + AI routing
- `app/agents/` - Domain-specific AI agents
- `docker-compose.yml` - Container definitions
- `.env` - Secrets (NEVER commit or show contents)

## Current Goals (Update Weekly)
1. ✅ Infrastructure running (8 Docker containers)
2. ✅ Cost optimization services created
3. ⏳ Apply schema fix (01_NEXUS_SCHEMA_FIX.sql)
4. ⏳ Test and verify cost optimization layer
5. 🔲 Build Finance Agent first
6. 🔲 Create iPhone Quick Expense shortcut

## Container Status (Expected)
- `nexus-postgres` - PostgreSQL 16 (:5432)
- `nexus-redis` - Redis 7.4 (:6379)
- `nexus-chromadb` - ChromaDB (:8000)
- `nexus-ollama` - Ollama (:11434)
- `nexus-homeassistant` - Home Assistant (:8123)
- `nexus-n8n` - n8n automation (:5678)
- `nexus-syncthing` - File sync (:8384)
- `nexus-vaultwarden` - Secrets (:8222)

## Code Conventions

### Database Query Pattern
```python
async with get_db() as conn:
    result = await conn.fetch("SELECT * FROM table WHERE id = $1", uuid)
```

### AI Call Pattern (ALWAYS use router)
```python
from app.services.model_cascade import route_query
response = await route_query(
    query="...",
    complexity="simple",  # simple|medium|complex
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

### Logging Pattern
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Action completed", extra={"agent": "finance", "tokens": 123})
```

## DO NOT Modify Without Explicit Request
- `.env` file (contains secrets)
- `data/` directory (container persistent state)
- `docker-compose.yml` (stable infrastructure)
- Any file in `data/postgres/` (database files)

## Philip's Context
- **Work:** Night shift janitor at BMR, 6PM-12AM most days (off Fri/Sat)
- **Budget:** ~$1,800/month income, $300-400/month to debt
- **Debt:** $9,700 owed to mom
- **Health:** Ex-smoker (lungs healing), esophagitis
- **Supplements:** NAC, D3, Magnesium Glycinate, Algae Oil, Creatine
- **Goal:** Financial independence through AI automation
- **Skill Level:** Beginner programmer (learning Linux/Python)

## Model Usage Rules
- **Simple queries** → Ollama local (FREE)
- **Medium complexity** → Groq free tier (FREE)
- **Complex reasoning** → DeepSeek ($0.28/M tokens)
- **Critical/architecture** → Opus 4.5 (expensive, use sparingly)
- **NEVER** send secrets to external AI (Privacy Shield handles this)

## Cost Budget
- **Target:** <$3/month total AI costs
- **Cache hit rate target:** >60%
- **Local processing target:** >50% of queries

## Common Commands
```bash
# Check containers
docker ps

# View PostgreSQL tables
docker exec -it nexus-postgres psql -U nexus -d nexus_db -c "\dt"

# View API logs
sudo journalctl -u nexus-api -f

# Run FastAPI dev server
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Test health endpoint
curl http://localhost:8080/health
```
