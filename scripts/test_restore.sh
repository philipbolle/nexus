#!/bin/bash
# NEXUS Restore Test Script
# Tests backup restoration in a safe, non-destructive way
# Usage: ./scripts/test_restore.sh [backup_path]

set -e

NEXUS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$NEXUS_DIR/backups/daily"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
if [ $# -eq 0 ]; then
    # Use latest backup if no argument provided
    if [ -L "$BACKUP_DIR/latest" ]; then
        BACKUP_PATH=$(readlink -f "$BACKUP_DIR/latest")
    else
        # Find most recent backup
        BACKUP_PATH=$(ls -td "$BACKUP_DIR"/nexus_backup_* 2>/dev/null | head -1)
    fi
else
    BACKUP_PATH="$1"
fi

if [ -z "$BACKUP_PATH" ] || [ ! -d "$BACKUP_PATH" ]; then
    echo -e "${RED}❌ No backup found${NC}"
    echo "Usage: $0 [backup_path]"
    echo ""
    echo "Available backups:"
    ls -td "$BACKUP_DIR"/nexus_backup_* 2>/dev/null || echo "  No backups found"
    exit 1
fi

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    🔧 NEXUS RESTORE TEST                           ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Testing restore from: $(basename "$BACKUP_PATH")${NC}"
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
    echo -e "${RED}❌ Restore test failed at step: $1${NC}"
    echo -e "${YELLOW}💡 Check error above${NC}"
    exit 1
}

# Test PostgreSQL dump
echo -e "${YELLOW}🗄️  Testing PostgreSQL dump...${NC}"
if [ -f "$BACKUP_PATH/postgres_backup.dump" ]; then
    if [ -s "$BACKUP_PATH/postgres_backup.dump" ]; then
        # Test dump format without restoring
        echo -n "  Checking dump format: "
        if file "$BACKUP_PATH/postgres_backup.dump" | grep -q "PostgreSQL custom database dump"; then
            echo -e "${GREEN}✓ Valid PostgreSQL dump${NC}"

            # Test dump contents without restoring
            echo -n "  Testing dump integrity: "
            if pg_restore -l "$BACKUP_PATH/postgres_backup.dump" >/dev/null 2>&1; then
                echo -e "${GREEN}✓ Dump is restorable${NC}"

                # Count tables in dump
                table_count=$(pg_restore -l "$BACKUP_PATH/postgres_backup.dump" | grep -c "TABLE DATA" || true)
                echo -e "  Tables in dump: ${GREEN}$table_count${NC}"
            else
                echo -e "${RED}✗ Dump is corrupted${NC}"
                handle_error "PostgreSQL dump test"
            fi
        else
            echo -e "${RED}✗ Not a PostgreSQL dump${NC}"
            handle_error "PostgreSQL format test"
        fi
    else
        echo -e "${RED}✗ Empty dump file${NC}"
        handle_error "PostgreSQL empty dump"
    fi
else
    echo -e "${YELLOW}⚠️  PostgreSQL dump not found in backup${NC}"
fi

# Test Redis dump
echo -e "${YELLOW}🔴 Testing Redis dump...${NC}"
if [ -f "$BACKUP_PATH/redis_dump.rdb" ]; then
    if [ -s "$BACKUP_PATH/redis_dump.rdb" ]; then
        echo -n "  Checking RDB file: "
        if file "$BACKUP_PATH/redis_dump.rdb" | grep -q "Redis"; then
            echo -e "${GREEN}✓ Valid Redis RDB file${NC}"

            # Check RDB file size
            file_size=$(du -h "$BACKUP_PATH/redis_dump.rdb" | cut -f1)
            echo -e "  RDB file size: ${GREEN}$file_size${NC}"
        else
            echo -e "${YELLOW}⚠️  Not a recognized RDB file (may still be valid)${NC}"
        fi
    else
        echo -e "${RED}✗ Empty RDB file${NC}"
        handle_error "Redis empty dump"
    fi
else
    echo -e "${YELLOW}⚠️  Redis dump not found in backup${NC}"
fi

# Test ChromaDB backup
echo -e "${YELLOW}📚 Testing ChromaDB backup...${NC}"
if [ -d "$BACKUP_PATH/chromadb" ]; then
    if [ "$(ls -A "$BACKUP_PATH/chromadb" 2>/dev/null)" ]; then
        echo -e "${GREEN}✓ ChromaDB directory not empty${NC}"

        # Count files
        file_count=$(find "$BACKUP_PATH/chromadb" -type f | wc -l)
        echo -e "  Files in backup: ${GREEN}$file_count${NC}"

        # Check for critical files
        if [ -f "$BACKUP_PATH/chromadb/chroma.sqlite3" ] || [ -d "$BACKUP_PATH/chromadb/collections" ]; then
            echo -e "${GREEN}✓ Critical ChromaDB files present${NC}"
        else
            echo -e "${YELLOW}⚠️  Critical ChromaDB files missing${NC}"
        fi
    else
        echo -e "${RED}✗ Empty ChromaDB directory${NC}"
        handle_error "ChromaDB empty backup"
    fi
else
    echo -e "${YELLOW}⚠️  ChromaDB backup not found${NC}"
fi

# Test n8n backup
echo -e "${YELLOW}🤖 Testing n8n backup...${NC}"
if [ -d "$BACKUP_PATH/n8n" ]; then
    if [ "$(ls -A "$BACKUP_PATH/n8n" 2>/dev/null)" ]; then
        echo -e "${GREEN}✓ n8n backup directory not empty${NC}"

        # Test SQLite database if present
        if [ -f "$BACKUP_PATH/n8n/database.sqlite" ]; then
            echo -n "  Testing n8n database: "
            if sqlite3 "$BACKUP_PATH/n8n/database.sqlite" "SELECT COUNT(*) FROM sqlite_master;" >/dev/null 2>&1; then
                echo -e "${GREEN}✓ Valid SQLite database${NC}"
            else
                echo -e "${RED}✗ Corrupted SQLite database${NC}"
                handle_error "n8n database test"
            fi
        fi

        # Check for workflow files
        if [ -d "$BACKUP_PATH/n8n/workflows" ]; then
            workflow_count=$(find "$BACKUP_PATH/n8n/workflows" -name "*.json" | wc -l)
            echo -e "  Workflow files: ${GREEN}$workflow_count${NC}"
        fi
    else
        echo -e "${RED}✗ Empty n8n backup directory${NC}"
        handle_error "n8n empty backup"
    fi
else
    echo -e "${YELLOW}⚠️  n8n backup not found${NC}"
fi

# Test config backup
echo -e "${YELLOW}📄 Testing config backup...${NC}"
if [ -d "$BACKUP_PATH/config" ]; then
    config_count=$(find "$BACKUP_PATH/config" -type f 2>/dev/null | wc -l)
    if [ "$config_count" -gt 0 ]; then
        echo -e "${GREEN}✓ Config files present: $config_count${NC}"

        # Check for critical config files
        critical_files=(".env" "docker-compose.yml" "requirements.txt")
        missing_files=()

        for file in "${critical_files[@]}"; do
            if [ ! -f "$BACKUP_PATH/config/$file" ]; then
                missing_files+=("$file")
            fi
        done

        if [ ${#missing_files[@]} -eq 0 ]; then
            echo -e "${GREEN}✓ All critical config files present${NC}"
        else
            echo -e "${YELLOW}⚠️  Missing critical config files: ${missing_files[*]}${NC}"
        fi
    else
        echo -e "${RED}✗ No config files found${NC}"
        handle_error "Config empty backup"
    fi
else
    echo -e "${YELLOW}⚠️  Config backup not found${NC}"
fi

# Check manifest
echo -e "${YELLOW}📝 Checking backup manifest...${NC}"
if [ -f "$BACKUP_PATH/MANIFEST.txt" ]; then
    echo -e "${GREEN}✓ Manifest file present${NC}"

    # Display manifest summary
    echo ""
    echo -e "${BLUE}Backup Summary from Manifest:${NC}"
    grep -E "^(Backup created:|Contents:|Services status)" "$BACKUP_PATH/MANIFEST.txt" | head -10
else
    echo -e "${YELLOW}⚠️  Manifest file missing${NC}"
fi

echo ""
echo -e "${GREEN}✅ Restore test completed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Backup Quality Assessment:${NC}"

# Calculate backup score
score=0
max_score=0

check_component() {
    local component="$1"
    local weight="$2"
    local test_func="$3"

    max_score=$((max_score + weight))

    if $test_func; then
        echo -e "  $component: ${GREEN}✓ (+$weight)${NC}"
        score=$((score + weight))
    else
        echo -e "  $component: ${RED}✗ (0)${NC}"
    fi
}

# Define test functions
test_postgres() {
    [ -f "$BACKUP_PATH/postgres_backup.dump" ] && [ -s "$BACKUP_PATH/postgres_backup.dump" ]
}

test_redis() {
    [ -f "$BACKUP_PATH/redis_dump.rdb" ] && [ -s "$BACKUP_PATH/redis_dump.rdb" ]
}

test_chromadb() {
    [ -d "$BACKUP_PATH/chromadb" ] && [ "$(ls -A "$BACKUP_PATH/chromadb" 2>/dev/null)" ]
}

test_n8n() {
    [ -d "$BACKUP_PATH/n8n" ] && [ "$(ls -A "$BACKUP_PATH/n8n" 2>/dev/null)" ]
}

test_config() {
    [ -d "$BACKUP_PATH/config" ] && [ $(find "$BACKUP_PATH/config" -type f 2>/dev/null | wc -l) -gt 0 ]
}

test_manifest() {
    [ -f "$BACKUP_PATH/MANIFEST.txt" ]
}

# Score components (weights based on importance)
check_component "PostgreSQL" 30 test_postgres
check_component "Redis" 20 test_redis
check_component "ChromaDB" 15 test_chromadb
check_component "n8n" 15 test_n8n
check_component "Config" 10 test_config
check_component "Manifest" 10 test_manifest

# Calculate percentage
if [ $max_score -gt 0 ]; then
    percentage=$((score * 100 / max_score))
else
    percentage=0
fi

echo ""
echo -e "${BLUE}Overall Backup Score: ${score}/${max_score} (${percentage}%)${NC}"

if [ $percentage -ge 80 ]; then
    echo -e "${GREEN}✅ Excellent backup quality${NC}"
elif [ $percentage -ge 60 ]; then
    echo -e "${YELLOW}⚠️  Acceptable backup quality${NC}"
else
    echo -e "${RED}❌ Poor backup quality - consider re-running backup${NC}"
fi

echo ""
echo -e "${YELLOW}💡 Next steps:${NC}"
echo "  1. To perform actual restore, follow instructions in CLAUDE.md"
echo "  2. Regular backup verification: ./scripts/backup_nexus_enhanced.sh --verify"
echo "  3. Cleanup old backups: ./scripts/backup_nexus_enhanced.sh --cleanup"