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
