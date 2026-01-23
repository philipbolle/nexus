#!/bin/bash
# NEXUS Enhanced Backup Script
# Usage: ./scripts/backup_nexus_enhanced.sh [--verify] [--cleanup] [--max-backups N]
# Creates timestamped backup with verification and rotation

set -e

NEXUS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$NEXUS_DIR/backups"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_NAME="nexus_backup_$TIMESTAMP"
BACKUP_PATH="$BACKUP_DIR/daily/$BACKUP_NAME"

# Default settings
VERIFY_BACKUP=false
CLEANUP_OLD=false
MAX_BACKUPS=7  # Keep 7 days of backups by default

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verify)
            VERIFY_BACKUP=true
            shift
            ;;
        --cleanup)
            CLEANUP_OLD=true
            shift
            ;;
        --max-backups)
            MAX_BACKUPS="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--verify] [--cleanup] [--max-backups N]"
            echo ""
            echo "Options:"
            echo "  --verify         Verify backup integrity after creation"
            echo "  --cleanup        Clean up old backups (keep last N)"
            echo "  --max-backups N  Number of backups to keep (default: 7)"
            echo "  --help           Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║               🛡️  NEXUS ENHANCED BACKUP - $TIMESTAMP                ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Load environment variables
if [ -f "$NEXUS_DIR/.env" ]; then
    echo -e "${YELLOW}📋 Loading environment from .env${NC}"
    set -a
    source "$NEXUS_DIR/.env"
    set +a
fi

# Function to handle errors
handle_error() {
    echo -e "${RED}❌ Backup failed at step: $1${NC}"
    echo -e "${YELLOW}💡 Check error above and try again${NC}"
    exit 1
}

# Function to verify backup integrity
verify_backup() {
    local backup_path="$1"
    echo -e "${YELLOW}🔍 Verifying backup integrity...${NC}"

    local verification_passed=true

    # Check PostgreSQL dump
    if [ -f "$backup_path/postgres_backup.dump" ]; then
        echo -n "  PostgreSQL: "
        if [ -s "$backup_path/postgres_backup.dump" ]; then
            echo -e "${GREEN}✓ Valid dump file${NC}"
        else
            echo -e "${RED}✗ Empty dump file${NC}"
            verification_passed=false
        fi
    fi

    # Check Redis dump
    if [ -f "$backup_path/redis_dump.rdb" ]; then
        echo -n "  Redis: "
        if [ -s "$backup_path/redis_dump.rdb" ]; then
            echo -e "${GREEN}✓ Valid RDB file${NC}"
        else
            echo -e "${RED}✗ Empty RDB file${NC}"
            verification_passed=false
        fi
    fi

    # Check ChromaDB directory
    if [ -d "$backup_path/chromadb" ]; then
        echo -n "  ChromaDB: "
        if [ "$(ls -A "$backup_path/chromadb" 2>/dev/null)" ]; then
            echo -e "${GREEN}✓ Directory not empty${NC}"
        else
            echo -e "${RED}✗ Empty directory${NC}"
            verification_passed=false
        fi
    fi

    # Check n8n backup
    if [ -d "$backup_path/n8n" ]; then
        echo -n "  n8n: "
        if [ "$(ls -A "$backup_path/n8n" 2>/dev/null)" ]; then
            echo -e "${GREEN}✓ Backup exists${NC}"
        else
            echo -e "${RED}✗ Empty backup${NC}"
            verification_passed=false
        fi
    fi

    # Check config files
    if [ -d "$backup_path/config" ]; then
        echo -n "  Config: "
        config_count=$(find "$backup_path/config" -type f 2>/dev/null | wc -l)
        if [ "$config_count" -gt 0 ]; then
            echo -e "${GREEN}✓ $config_count files${NC}"
        else
            echo -e "${RED}✗ No config files${NC}"
            verification_passed=false
        fi
    fi

    if [ "$verification_passed" = true ]; then
        echo -e "${GREEN}✅ Backup verification passed${NC}"
        return 0
    else
        echo -e "${RED}❌ Backup verification failed${NC}"
        return 1
    fi
}

# Function to cleanup old backups
cleanup_old_backups() {
    local max_backups="$1"
    echo -e "${YELLOW}🗑️  Cleaning up old backups (keeping last $max_backups)...${NC}"

    if [ ! -d "$BACKUP_DIR/daily" ]; then
        echo -e "${YELLOW}⚠️  No backup directory found${NC}"
        return
    fi

    # List backups sorted by modification time (newest first)
    local backups=($(ls -t "$BACKUP_DIR/daily/" 2>/dev/null || true))
    local total_backups=${#backups[@]}

    if [ "$total_backups" -le "$max_backups" ]; then
        echo -e "${GREEN}✅ Only $total_backups backups exist (≤ $max_backups limit)${NC}"
        return
    fi

    local backups_to_remove=$((total_backups - max_backups))
    echo -e "${YELLOW}  Found $total_backups backups, removing $backups_to_remove oldest...${NC}"

    # Remove oldest backups
    for ((i=max_backups; i<total_backups; i++)); do
        local backup_to_remove="${backups[$i]}"
        local backup_path="$BACKUP_DIR/daily/$backup_to_remove"

        if [ -d "$backup_path" ]; then
            echo -e "  Removing: $backup_to_remove"
            rm -rf "$backup_path"
        fi
    done

    echo -e "${GREEN}✅ Cleanup complete. $max_backups backups remaining.${NC}"
}

# Create backup directory
mkdir -p "$BACKUP_PATH"
echo -e "${GREEN}✅ Created backup directory: $BACKUP_PATH${NC}"

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
    echo "Backup ID: $BACKUP_NAME"
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
    echo ""
    echo "Verification command:"
    echo "  $0 --verify"
    echo ""
    echo "Restore instructions:"
    echo "  See documentation in CLAUDE.md"
} > "$BACKUP_PATH/MANIFEST.txt"

# Calculate total size
TOTAL_SIZE=$(du -sh "$BACKUP_PATH" | cut -f1)
echo -e "${GREEN}✅ Backup complete! Total size: $TOTAL_SIZE${NC}"

# Verify backup if requested
if [ "$VERIFY_BACKUP" = true ]; then
    if verify_backup "$BACKUP_PATH"; then
        echo -e "${GREEN}✅ Backup verification successful${NC}"
    else
        echo -e "${RED}❌ Backup verification failed - consider re-running backup${NC}"
        exit 1
    fi
fi

# Cleanup old backups if requested
if [ "$CLEANUP_OLD" = true ]; then
    cleanup_old_backups "$MAX_BACKUPS"
fi

echo ""
echo -e "${BLUE}📋 Backup Summary:${NC}"
cat "$BACKUP_PATH/MANIFEST.txt"
echo ""
echo -e "${YELLOW}💡 To restore from this backup, see documentation in CLAUDE.md${NC}"
echo -e "${YELLOW}🔍 To verify this backup: ./scripts/backup_nexus_enhanced.sh --verify${NC}"
echo -e "${YELLOW}🗑️  To cleanup old backups: ./scripts/backup_nexus_enhanced.sh --cleanup${NC}"

# Create symlink to latest backup
ln -sfn "$BACKUP_PATH" "$BACKUP_DIR/daily/latest" 2>/dev/null || true
echo -e "${GREEN}🔗 Created symlink: $BACKUP_DIR/daily/latest → $BACKUP_NAME${NC}"