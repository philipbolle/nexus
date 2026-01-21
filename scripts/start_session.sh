#!/bin/bash
# NEXUS Session Start - Fully Automated
# Usage: ~/nexus/scripts/start_session.sh

set -e

NEXUS_DIR=~/nexus
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

clear
echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                    🚀 NEXUS SESSION START                              ║${NC}"
echo -e "${CYAN}║                    $TIMESTAMP                              ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

cd $NEXUS_DIR

# Load environment
if [ -f "$NEXUS_DIR/.env" ]; then
    set -a
    source "$NEXUS_DIR/.env"
    set +a
    echo -e "${GREEN}✅ Environment loaded${NC}"
fi

# ═══════════════════════════════════════════════════════════════
# STEP 1: Start Docker containers if needed
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}📦 DOCKER STATUS${NC}"

if ! docker ps > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker not accessible. Run: newgrp docker${NC}"
    exit 1
fi

RUNNING=$(docker ps --format "{{.Names}}" | wc -l)
if [ $RUNNING -lt 7 ]; then
    echo -e "${YELLOW}   Starting containers...${NC}"
    docker compose up -d 2>/dev/null
    sleep 5
    RUNNING=$(docker ps --format "{{.Names}}" | wc -l)
fi
echo -e "${GREEN}   ✅ $RUNNING containers running${NC}"
docker ps --format "   • {{.Names}}: {{.Status}}" | head -8

# ═══════════════════════════════════════════════════════════════
# STEP 2: Clean up junk files automatically
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}🧹 AUTO-CLEANUP${NC}"

# Remove Python cache
PYCACHE_COUNT=$(find $NEXUS_DIR -type d -name "__pycache__" 2>/dev/null | wc -l)
if [ $PYCACHE_COUNT -gt 0 ]; then
    find $NEXUS_DIR -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    echo -e "${GREEN}   ✅ Removed $PYCACHE_COUNT __pycache__ folders${NC}"
fi

# Remove .pyc files
PYC_COUNT=$(find $NEXUS_DIR -name "*.pyc" 2>/dev/null | wc -l)
if [ $PYC_COUNT -gt 0 ]; then
    find $NEXUS_DIR -name "*.pyc" -delete 2>/dev/null || true
    echo -e "${GREEN}   ✅ Removed $PYC_COUNT .pyc files${NC}"
fi

# Remove empty directories in data/
find $NEXUS_DIR/data -type d -empty -delete 2>/dev/null || true

# Remove backup files older than 7 days
find $NEXUS_DIR -name "*.backup" -o -name "*.bak" -mtime +7 -delete 2>/dev/null || true

# Remove .DS_Store (Mac files)
find $NEXUS_DIR -name ".DS_Store" -delete 2>/dev/null || true

if [ $PYCACHE_COUNT -eq 0 ] && [ $PYC_COUNT -eq 0 ]; then
    echo -e "${GREEN}   ✅ Already clean${NC}"
fi

# ═══════════════════════════════════════════════════════════════
# STEP 3: Check database health
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}🐘 DATABASE${NC}"

if docker exec nexus-postgres pg_isready -U nexus > /dev/null 2>&1; then
    TABLE_COUNT=$(docker exec nexus-postgres psql -U nexus -d nexus_db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
    echo -e "${GREEN}   ✅ PostgreSQL ready - $TABLE_COUNT tables${NC}"
else
    echo -e "${RED}   ❌ PostgreSQL not responding${NC}"
fi

# ═══════════════════════════════════════════════════════════════
# STEP 4: Check Redis
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}🔴 CACHE${NC}"

if [ -n "$REDIS_PASSWORD" ]; then
    if docker exec nexus-redis redis-cli -a "$REDIS_PASSWORD" ping 2>/dev/null | grep -q "PONG"; then
        KEYS=$(docker exec nexus-redis redis-cli -a "$REDIS_PASSWORD" DBSIZE 2>/dev/null | awk '{print $2}')
        echo -e "${GREEN}   ✅ Redis ready - $KEYS cached keys${NC}"
    else
        echo -e "${RED}   ❌ Redis not responding${NC}"
    fi
else
    echo -e "${YELLOW}   ⚠️ REDIS_PASSWORD not set${NC}"
fi

# ═══════════════════════════════════════════════════════════════
# STEP 5: Git status
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}📝 GIT${NC}"

if [ -d "$NEXUS_DIR/.git" ]; then
    BRANCH=$(git branch --show-current 2>/dev/null)
    CHANGES=$(git status --porcelain 2>/dev/null | wc -l)
    LAST_COMMIT=$(git log --oneline -1 2>/dev/null)
    
    echo -e "   Branch: ${GREEN}$BRANCH${NC}"
    if [ $CHANGES -gt 0 ]; then
        echo -e "   Uncommitted: ${YELLOW}$CHANGES files${NC}"
    else
        echo -e "   Status: ${GREEN}Clean${NC}"
    fi
    echo -e "   Last: $LAST_COMMIT"
    
    # Pull latest if clean
    if [ $CHANGES -eq 0 ]; then
        echo -e "${YELLOW}   Pulling latest...${NC}"
        git pull origin main 2>/dev/null || echo -e "${YELLOW}   (offline or no changes)${NC}"
    fi
else
    echo -e "${YELLOW}   ⚠️ Git not initialized${NC}"
fi

# ═══════════════════════════════════════════════════════════════
# STEP 6: Generate fresh context file
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}📄 GENERATING CONTEXT${NC}"

$NEXUS_DIR/scripts/generate_context.sh

# Also update CLAUDE.md with timestamp
if [ -f "$NEXUS_DIR/CLAUDE.md" ]; then
    # Update the timestamp line if it exists
    sed -i "s/^> Last updated:.*/> Last updated: $TIMESTAMP/" $NEXUS_DIR/CLAUDE.md 2>/dev/null || true
fi

# ═══════════════════════════════════════════════════════════════
# STEP 7: Show session summary
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✅ NEXUS READY${NC}"
echo ""
echo -e "Context files updated:"
echo -e "  • ${GREEN}NEXUS_CONTEXT.md${NC} - Copy into Gemini/Grok/ChatGPT"
echo -e "  • ${GREEN}CLAUDE.md${NC} - For Claude Code"
echo ""
echo -e "Quick commands:"
echo -e "  ${CYAN}deepseek${NC}    - Start Claude Code with DeepSeek (cheap)"
echo -e "  ${CYAN}nexus-chat${NC}  - Quick AI query via Groq (free)"
echo -e "  ${CYAN}code .${NC}      - Open VS Code with Cline"
echo ""
echo -e "When done: ${YELLOW}~/nexus/scripts/end_session.sh${NC}"
echo ""

# Activate Python venv if exists
if [ -f "$NEXUS_DIR/venv/bin/activate" ]; then
    echo -e "${YELLOW}Run: source venv/bin/activate${NC}"
fi
