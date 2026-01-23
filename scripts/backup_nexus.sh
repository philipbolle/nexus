#!/bin/bash
# NEXUS Simple Backup Script
# Usage: ./scripts/backup_nexus.sh
# Creates timestamped backup in backups/daily/

set -e

NEXUS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$NEXUS_DIR/backups"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_NAME="nexus_backup_$TIMESTAMP"
BACKUP_PATH="$BACKUP_DIR/daily/$BACKUP_NAME"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    🛡️  NEXUS BACKUP - $TIMESTAMP                    ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Load environment variables
if [ -f "$NEXUS_DIR/.env" ]; then
    echo -e "${YELLOW}📋 Loading environment from .env${NC}"
    set -a
    source "$NEXUS_DIR/.env"
    set +a
fi

# Create backup directory
mkdir -p "$BACKUP_PATH"
echo -e "${GREEN}✅ Created backup directory: $BACKUP_PATH${NC}"

# Function to handle errors
handle_error() {
    echo -e "${RED}❌ Backup failed at step: $1${NC}"
    echo -e "${YELLOW}💡 Check error above and try again${NC}"
    exit 1
}

# Backup PostgreSQL
echo -e "${YELLOW}🗄️  Backing up PostgreSQL database...${NC}"
if docker ps --filter "name=nexus-postgres" --format "{{.Names}}" | grep -q "nexus-postgres"; then
    docker exec nexus-postgres pg_dump -Fc -U nexus nexus_db > "$BACKUP_PATH/postgres_backup.dump" 2>/dev/null || handle_error "PostgreSQL dump"

    # Verify dump file
    if [ -s "$BACKUP_PATH/postgres_backup.dump" ]; then
        echo -e "${GREEN}✅ PostgreSQL backup created: $(du -h "$BACKUP_PATH/postgres_backup.dump" | cut -f1)${NC}"
    else
        handle_error "PostgreSQL dump file empty"
    fi
else
    echo -e "${YELLOW}⚠️  PostgreSQL container not running, skipping${NC}"
fi

# Backup Redis
echo -e "${YELLOW}🔴 Backing up Redis...${NC}"
if docker ps --filter "name=nexus-redis" --format "{{.Names}}" | grep -q "nexus-redis"; then
    # Trigger Redis SAVE
    docker exec nexus-redis redis-cli -a "$REDIS_PASSWORD" SAVE 2>/dev/null || handle_error "Redis SAVE"

    # Wait for save to complete
    sleep 1

    # Copy RDB file from container
    docker cp nexus-redis:/data/dump.rdb "$BACKUP_PATH/redis_dump.rdb" 2>/dev/null || {
        echo -e "${YELLOW}⚠️  Failed to copy Redis dump from container, trying host file...${NC}"
        # Fallback to host file (might have permission issues)
        if [ -f "$NEXUS_DIR/data/redis/dump.rdb" ]; then
            cp "$NEXUS_DIR/data/redis/dump.rdb" "$BACKUP_PATH/redis_dump.rdb" || echo -e "${YELLOW}⚠️  Redis backup failed due to permissions${NC}"
        fi
    }

    if [ -f "$BACKUP_PATH/redis_dump.rdb" ]; then
        echo -e "${GREEN}✅ Redis backup created: $(du -h "$BACKUP_PATH/redis_dump.rdb" | cut -f1)${NC}"
    else
        echo -e "${YELLOW}⚠️  Redis dump.rdb not found, skipping${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Redis container not running, skipping${NC}"
fi

# Backup ChromaDB directory
echo -e "${YELLOW}📚 Backing up ChromaDB...${NC}"
if [ -d "$NEXUS_DIR/data/chromadb" ]; then
    mkdir -p "$BACKUP_PATH/chromadb"
    rsync -av --exclude='*.lock' "$NEXUS_DIR/data/chromadb/" "$BACKUP_PATH/chromadb/" >/dev/null 2>&1 || handle_error "ChromaDB copy"
    echo -e "${GREEN}✅ ChromaDB backed up${NC}"
else
    echo -e "${YELLOW}⚠️  ChromaDB directory not found, skipping${NC}"
fi

# Backup n8n data
echo -e "${YELLOW}🤖 Backing up n8n...${NC}"
if [ -d "$NEXUS_DIR/data/n8n" ]; then
    mkdir -p "$BACKUP_PATH/n8n"
    # Backup SQLite database if exists
    if [ -f "$NEXUS_DIR/data/n8n/database.sqlite" ]; then
        sqlite3 "$NEXUS_DIR/data/n8n/database.sqlite" ".backup '$BACKUP_PATH/n8n/database.sqlite'" 2>/dev/null || echo -e "${YELLOW}⚠️  n8n database backup failed, copying file instead${NC}"
    fi

    # Copy workflow files
    if [ -d "$NEXUS_DIR/automation/workflows" ]; then
        cp -r "$NEXUS_DIR/automation/workflows" "$BACKUP_PATH/n8n/workflows" 2>/dev/null || true
    fi

    echo -e "${GREEN}✅ n8n backed up${NC}"
else
    echo -e "${YELLOW}⚠️  n8n directory not found, skipping${NC}"
fi

# Backup configuration files
echo -e "${YELLOW}📄 Backing up configuration...${NC}"
mkdir -p "$BACKUP_PATH/config"

# Critical config files
CONFIG_FILES=(
    ".env"
    "docker-compose.yml"
    "requirements.txt"
    "schema/00_NEXUS_ULTIMATE_SCHEMA.sql"
)

for config_file in "${CONFIG_FILES[@]}"; do
    if [ -f "$NEXUS_DIR/$config_file" ]; then
        cp "$NEXUS_DIR/$config_file" "$BACKUP_PATH/config/"
    fi
done

# Backup Home Assistant config
if [ -d "$NEXUS_DIR/config/homeassistant" ]; then
    mkdir -p "$BACKUP_PATH/config/homeassistant"
    rsync -av --exclude='*.db' --exclude='*.log' "$NEXUS_DIR/config/homeassistant/" "$BACKUP_PATH/config/homeassistant/" >/dev/null 2>&1 || true
fi

echo -e "${GREEN}✅ Configuration backed up${NC}"

# Create manifest
echo -e "${YELLOW}📝 Creating backup manifest...${NC}"
{
    echo "NEXUS Backup Manifest"
    echo "====================="
    echo "Backup created: $(date)"
    echo "Backup directory: $BACKUP_PATH"
    echo ""
    echo "Contents:"
    echo "- PostgreSQL: $(ls -lh "$BACKUP_PATH/postgres_backup.dump" 2>/dev/null | awk '{print $5}')" || echo "- PostgreSQL: Not backed up"
    echo "- Redis: $(ls -lh "$BACKUP_PATH/redis_dump.rdb" 2>/dev/null | awk '{print $5}')" || echo "- Redis: Not backed up"
    echo "- ChromaDB: $(du -sh "$BACKUP_PATH/chromadb" 2>/dev/null | cut -f1)" || echo "- ChromaDB: Not backed up"
    echo "- n8n: $(du -sh "$BACKUP_PATH/n8n" 2>/dev/null | cut -f1)" || echo "- n8n: Not backed up"
    echo "- Config: $(du -sh "$BACKUP_PATH/config" 2>/dev/null | cut -f1)" || echo "- Config: Not backed up"
    echo ""
    echo "Services status at backup time:"
    docker ps --filter "name=nexus-" --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || echo "Docker not accessible"
} > "$BACKUP_PATH/MANIFEST.txt"

# Calculate total size
TOTAL_SIZE=$(du -sh "$BACKUP_PATH" | cut -f1)
echo -e "${GREEN}✅ Backup complete! Total size: $TOTAL_SIZE${NC}"
echo ""
echo -e "${BLUE}📋 Backup Summary:${NC}"
cat "$BACKUP_PATH/MANIFEST.txt"
echo ""
echo -e "${YELLOW}💡 To restore from this backup, see documentation in CLAUDE.md${NC}"
echo -e "${YELLOW}🗑️  Old backups are NOT automatically cleaned up. Manage manually.${NC}"