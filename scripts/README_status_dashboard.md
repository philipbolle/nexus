# NEXUS Status Dashboard Scripts

Two dashboard scripts for monitoring Nexus system status at a glance.

## Scripts

### 1. `nexus_status.py` (Full-featured)
**Features:**
- Colorful terminal output with emojis
- Async HTTP requests using `httpx`
- Concurrent data fetching for speed
- Detailed metrics display
- Progress bars for debt/budget
- Requires: `httpx` (installed in virtual environment)

**Usage:**
```bash
# Activate virtual environment first
source venv/bin/activate

# Run the dashboard
python scripts/nexus_status.py
```

### 2. `nexus_status_simple.py` (No dependencies)
**Features:**
- Uses only Python standard library (`urllib`)
- Simple, clean output
- No external dependencies
- Works anywhere Python 3 is installed
- Basic but essential information

**Usage:**
```bash
# No virtual environment needed
python3 scripts/nexus_status_simple.py
```

## What They Show

Both scripts display:

### System Health
- Overall API status (healthy/unhealthy/degraded)
- Individual service status (PostgreSQL, Redis, ChromaDB, n8n, Agent Framework)
- System metrics (CPU, memory, disk usage)
- Database table count

### Agent Framework
- Total number of registered agents
- Breakdown by agent type (domain, orchestrator, email_intelligence)
- Sample agent names and status

### Finance
- Current month and total spent
- Category breakdown (top spending categories)
- Budget status (if configured)

### Email Intelligence
- Total emails processed
- Processing statistics

## Quick Commands

From the simple dashboard footer:
```bash
# Check API health
curl http://localhost:8080/health

# View API documentation
open http://localhost:8080/docs  # or visit in browser

# Run dashboard again
python3 scripts/nexus_status_simple.py
```

## Integration with Nexus

The dashboards use these Nexus API endpoints:
- `/health` - Basic health check
- `/status` - Detailed service status
- `/metrics/system` - System metrics
- `/agents` - Agent list
- `/finance/budget-status` - Budget information
- `/email/stats` - Email processing stats

## Making Scripts Executable

Both scripts are already executable. If needed:
```bash
chmod +x scripts/nexus_status.py
chmod +x scripts/nexus_status_simple.py
```

## Troubleshooting

**"ModuleNotFoundError: No module named 'httpx'"**
- Use the simple version: `python3 scripts/nexus_status_simple.py`
- Or activate virtual environment: `source venv/bin/activate`

**"Connection refused" or timeout errors**
- Make sure Nexus API is running: `sudo systemctl status nexus-api`
- Start if needed: `sudo systemctl start nexus-api`

**No finance or email data shown**
- Some endpoints might return 404 if features aren't configured
- The script will show warnings but continue with other data

## Customization

You can modify the scripts to:
- Add more endpoints
- Change colors or formatting
- Add custom metrics
- Integrate with other monitoring tools

## Example Output

```
============================================================
    NEXUS STATUS DASHBOARD (Simple)
============================================================
📅 2026-01-24 01:56:15

🖥️ SYSTEM HEALTH
----------------------------------------
  Status: HEALTHY
  Overall: HEALTHY
  Services:
    • postgresql: healthy 223 tables
    • redis: healthy None
    • n8n: healthy None
    • chromadb: healthy None
    • agent_framework: healthy 55 agents registered
  CPU: 8.6%
  Memory: 68.0% used
  Disk: 17.8% used

🤖 AGENT FRAMEWORK
----------------------------------------
  Total Agents: 55
  By Type:
    • domain: 48
    • orchestrator: 5
    • email_intelligence: 2
  Sample Agents:
    🟡 finance
    🟡 learning
    🟡 health

💰 FINANCE
----------------------------------------
  Month: January 2026
  Total Spent: $27.50
  Categories:
    • Test: $15.00
    • Food: $12.50

📧 EMAIL INTELLIGENCE
----------------------------------------
  Email Processing:
    Total Processed: 0
```

These dashboards provide Philip with instant visibility into his Nexus system - perfect for quick checks during his night shifts!