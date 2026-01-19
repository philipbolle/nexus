#!/bin/bash
# NEXUS Session Startup Script
# Run this at the beginning of each coding session
# Usage: ~/nexus/scripts/start_session.sh

set -e  # Exit on error

NEXUS_DIR=~/nexus
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              🚀 NEXUS Development Session                     ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 1. Check if we're in the right directory
if [ ! -d "$NEXUS_DIR" ]; then
    echo -e "${RED}❌ NEXUS directory not found at $NEXUS_DIR${NC}"
    exit 1
fi

cd $NEXUS_DIR

# 2. Load environment variables
if [ -f "$NEXUS_DIR/.env" ]; then
    source $NEXUS_DIR/.env
    echo -e "${GREEN}✅ Environment loaded${NC}"
else
    echo -e "${YELLOW}⚠️  .env file not found - some checks may fail${NC}"
fi

# 3. Check Docker is running and accessible
echo ""
echo -e "${BLUE}📦 Docker Status${NC}"
if docker ps > /dev/null 2>&1; then
    RUNNING=$(docker ps --format "{{.Names}}" | wc -l)
    echo -e "   ${GREEN}✅ Docker accessible, $RUNNING containers running${NC}"
    
    # List containers with their status
    echo ""
    docker ps --format "   {{.Names}}: {{.Status}}" | head -10
    
    # Start containers if not all running
    if [ $RUNNING -lt 7 ]; then
        echo ""
        echo -e "   ${YELLOW}⚠️  Some containers not running. Starting...${NC}"
        docker compose -f $NEXUS_DIR/docker-compose.yml up -d
        sleep 3
        RUNNING=$(docker ps --format "{{.Names}}" | wc -l)
        echo -e "   ${GREEN}✅ Now $RUNNING containers running${NC}"
    fi
else
    echo -e "   ${RED}❌ Docker not accessible${NC}"
    echo -e "   ${YELLOW}   Try: newgrp docker${NC}"
    echo -e "   ${YELLOW}   Or:  sudo usermod -aG docker \$USER && logout${NC}"
fi

# 4. Check PostgreSQL
echo ""
echo -e "${BLUE}🐘 PostgreSQL Status${NC}"
if docker exec nexus-postgres pg_isready -U nexus > /dev/null 2>&1; then
    TABLE_COUNT=$(docker exec nexus-postgres psql -U nexus -d nexus_db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ' || echo "?")
    echo -e "   ${GREEN}✅ PostgreSQL ready${NC}"
    echo -e "   ${NC}   Tables in database: $TABLE_COUNT${NC}"
    
    # Check if schema fix is needed
    if [ "$TABLE_COUNT" -lt 100 ] 2>/dev/null; then
        echo -e "   ${YELLOW}⚠️  Less than 100 tables - schema fix may be needed${NC}"
        echo -e "   ${YELLOW}   Run: docker exec -i nexus-postgres psql -U nexus -d nexus_db < schema/01_NEXUS_SCHEMA_FIX.sql${NC}"
    fi
else
    echo -e "   ${RED}❌ PostgreSQL not responding${NC}"
    echo -e "   ${YELLOW}   Check: docker logs nexus-postgres${NC}"
fi

# 5. Check Redis
echo ""
echo -e "${BLUE}🔴 Redis Status${NC}"
if [ -n "$REDIS_PASSWORD" ]; then
    if docker exec nexus-redis redis-cli -a "$REDIS_PASSWORD" ping 2>/dev/null | grep -q "PONG"; then
        KEYS=$(docker exec nexus-redis redis-cli -a "$REDIS_PASSWORD" DBSIZE 2>/dev/null | awk '{print $2}' || echo "?")
        echo -e "   ${GREEN}✅ Redis ready${NC}"
        echo -e "   ${NC}   Keys in cache: $KEYS${NC}"
    else
        echo -e "   ${RED}❌ Redis not responding${NC}"
    fi
else
    echo -e "   ${YELLOW}⚠️  REDIS_PASSWORD not set in .env${NC}"
fi

# 6. Check Ollama
echo ""
echo -e "${BLUE}🤖 Ollama Status${NC}"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    MODELS=$(curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' | wc -l || echo "0")
    echo -e "   ${GREEN}✅ Ollama ready${NC}"
    echo -e "   ${NC}   Models available: $MODELS${NC}"
else
    echo -e "   ${YELLOW}⚠️  Ollama not responding (may need to pull a model)${NC}"
    echo -e "   ${YELLOW}   Run: docker exec nexus-ollama ollama pull llama3.2:3b${NC}"
fi

# 7. Git status
echo ""
echo -e "${BLUE}📝 Git Status${NC}"
if [ -d "$NEXUS_DIR/.git" ]; then
    BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
    CHANGES=$(git status --porcelain 2>/dev/null | wc -l || echo "?")
    LAST_COMMIT=$(git log --oneline -1 2>/dev/null || echo "no commits")
    
    echo -e "   Branch: ${GREEN}$BRANCH${NC}"
    echo -e "   Uncommitted changes: ${YELLOW}$CHANGES${NC}"
    echo -e "   Last commit: $LAST_COMMIT"
else
    echo -e "   ${YELLOW}⚠️  Git not initialized${NC}"
    echo -e "   ${YELLOW}   Run: git init${NC}"
fi

# 8. Python virtual environment
echo ""
echo -e "${BLUE}🐍 Python Environment${NC}"
if [ -d "$NEXUS_DIR/venv" ]; then
    echo -e "   ${GREEN}✅ Virtual environment exists${NC}"
    echo -e "   ${NC}   Activate: source venv/bin/activate${NC}"
else
    echo -e "   ${YELLOW}⚠️  No virtual environment${NC}"
    echo -e "   ${YELLOW}   Create: python3 -m venv venv${NC}"
fi

# 9. Show last session context if available
echo ""
echo -e "${BLUE}📋 Last Session Context${NC}"
if [ -f "$NEXUS_DIR/docs/session_log.md" ]; then
    echo -e "${NC}"
    tail -20 $NEXUS_DIR/docs/session_log.md | sed 's/^/   /'
else
    echo -e "   ${YELLOW}No session log yet${NC}"
fi

# 10. Summary
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "Ready to work! Next steps:"
echo -e "  1. ${GREEN}cd ~/nexus${NC}"
echo -e "  2. ${GREEN}source venv/bin/activate${NC}  (if using Python)"
echo -e "  3. ${GREEN}claude${NC}  (to start Claude Code)"
echo ""
echo -e "When done, run: ${YELLOW}~/nexus/scripts/end_session.sh${NC}"
echo ""
