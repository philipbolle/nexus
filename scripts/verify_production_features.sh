#!/bin/bash
# NEXUS Production Features Verification Script
# Simple verification without importing Python modules

set -e

NEXUS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║               🔍 NEXUS PRODUCTION FEATURES VERIFICATION            ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}Checking file structure and scripts...${NC}"
echo ""

# Check 1: Logging configuration
echo -n "1. Logging configuration (app/logging_config.py): "
if [ -f "$NEXUS_DIR/app/logging_config.py" ]; then
    echo -e "${GREEN}✓ Found${NC}"
else
    echo -e "${RED}✗ Missing${NC}"
fi

# Check 2: Error handler middleware
echo -n "2. Error handler middleware (app/middleware/error_handler.py): "
if [ -f "$NEXUS_DIR/app/middleware/error_handler.py" ]; then
    echo -e "${GREEN}✓ Found${NC}"
else
    echo -e "${RED}✗ Missing${NC}"
fi

# Check 3: Monitoring integration
echo -n "3. Monitoring integration (app/monitoring_integration.py): "
if [ -f "$NEXUS_DIR/app/monitoring_integration.py" ]; then
    echo -e "${GREEN}✓ Found${NC}"
else
    echo -e "${RED}✗ Missing${NC}"
fi

# Check 4: Enhanced health router
echo -n "4. Enhanced health router (app/routers/health.py): "
if [ -f "$NEXUS_DIR/app/routers/health.py" ]; then
    # Check for new endpoints
    if grep -q "detailed_health_check\|readiness_probe\|liveness_probe\|system_metrics" "$NEXUS_DIR/app/routers/health.py"; then
        echo -e "${GREEN}✓ Found with new endpoints${NC}"
    else
        echo -e "${YELLOW}⚠ Found but may not have new endpoints${NC}"
    fi
else
    echo -e "${RED}✗ Missing${NC}"
fi

# Check 5: Enhanced backup script
echo -n "5. Enhanced backup script (scripts/backup_nexus_enhanced.sh): "
if [ -f "$NEXUS_DIR/scripts/backup_nexus_enhanced.sh" ]; then
    if [ -x "$NEXUS_DIR/scripts/backup_nexus_enhanced.sh" ]; then
        echo -e "${GREEN}✓ Found and executable${NC}"
    else
        echo -e "${YELLOW}⚠ Found but not executable${NC}"
    fi
else
    echo -e "${RED}✗ Missing${NC}"
fi

# Check 6: Restore test script
echo -n "6. Restore test script (scripts/test_restore.sh): "
if [ -f "$NEXUS_DIR/scripts/test_restore.sh" ]; then
    if [ -x "$NEXUS_DIR/scripts/test_restore.sh" ]; then
        echo -e "${GREEN}✓ Found and executable${NC}"
    else
        echo -e "${YELLOW}⚠ Found but not executable${NC}"
    fi
else
    echo -e "${RED}✗ Missing${NC}"
fi

# Check 7: Requirements.txt updated
echo -n "7. Requirements.txt updated with psutil: "
if [ -f "$NEXUS_DIR/requirements.txt" ]; then
    if grep -q "psutil" "$NEXUS_DIR/requirements.txt"; then
        echo -e "${GREEN}✓ psutil dependency added${NC}"
    else
        echo -e "${RED}✗ psutil dependency missing${NC}"
    fi
else
    echo -e "${RED}✗ requirements.txt missing${NC}"
fi

# Check 8: Main.py updated
echo -n "8. Main.py updated with new imports: "
if [ -f "$NEXUS_DIR/app/main.py" ]; then
    if grep -q "logging_config\|error_handler\|monitoring_integration" "$NEXUS_DIR/app/main.py"; then
        echo -e "${GREEN}✓ Updated with new imports${NC}"
    else
        echo -e "${YELLOW}⚠ May not have all updates${NC}"
    fi
else
    echo -e "${RED}✗ main.py missing${NC}"
fi

# Check 9: Schemas updated
echo -n "9. Schemas updated with health models: "
if [ -f "$NEXUS_DIR/app/models/schemas.py" ]; then
    if grep -q "HealthCheckResult\|ReadinessResponse\|LivenessResponse\|SystemMetricsResponse" "$NEXUS_DIR/app/models/schemas.py"; then
        echo -e "${GREEN}✓ Health models added${NC}"
    else
        echo -e "${RED}✗ Health models missing${NC}"
    fi
else
    echo -e "${RED}✗ schemas.py missing${NC}"
fi

echo ""
echo -e "${YELLOW}Testing backup script functionality...${NC}"
echo ""

# Test backup script help
if [ -f "$NEXUS_DIR/scripts/backup_nexus_enhanced.sh" ] && [ -x "$NEXUS_DIR/scripts/backup_nexus_enhanced.sh" ]; then
    echo -n "Backup script help command: "
    if "$NEXUS_DIR/scripts/backup_nexus_enhanced.sh" --help >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Works${NC}"
    else
        echo -e "${RED}✗ Failed${NC}"
    fi
fi

# Test restore script help
if [ -f "$NEXUS_DIR/scripts/test_restore.sh" ] && [ -x "$NEXUS_DIR/scripts/test_restore.sh" ]; then
    echo -n "Restore test script help: "
    if "$NEXUS_DIR/scripts/test_restore.sh" --help >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Works${NC}"
    else
        # Check if script has --help flag
        if grep -q "Usage:" "$NEXUS_DIR/scripts/test_restore.sh"; then
            echo -e "${YELLOW}⚠ Has usage but no --help flag${NC}"
        else
            echo -e "${RED}✗ No help available${NC}"
        fi
    fi
fi

echo ""
echo -e "${YELLOW}Checking directory structure...${NC}"
echo ""

# Check middleware directory
echo -n "Middleware directory exists: "
if [ -d "$NEXUS_DIR/app/middleware" ]; then
    echo -e "${GREEN}✓ Found${NC}"
else
    echo -e "${RED}✗ Missing${NC}"
fi

# Check backup directory structure
echo -n "Backup directory exists: "
if [ -d "$NEXUS_DIR/backups" ]; then
    echo -e "${GREEN}✓ Found${NC}"

    # Check daily subdirectory
    if [ -d "$NEXUS_DIR/backups/daily" ]; then
        echo -e "  Daily backups directory: ${GREEN}✓ Found${NC}"
    else
        echo -e "  Daily backups directory: ${YELLOW}⚠ Missing (will be created on first backup)${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Missing (will be created on first backup)${NC}"
fi

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                         VERIFICATION SUMMARY                         ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Count successes
success_count=$(grep -c "✓" <<< "$(cat $0)")
warning_count=$(grep -c "⚠" <<< "$(cat $0)")
error_count=$(grep -c "✗" <<< "$(cat $0)")

echo -e "Successes: ${GREEN}$success_count${NC}"
echo -e "Warnings: ${YELLOW}$warning_count${NC}"
echo -e "Errors: ${RED}$error_count${NC}"
echo ""

if [ $error_count -eq 0 ] && [ $warning_count -eq 0 ]; then
    echo -e "${GREEN}✅ All production readiness features verified successfully!${NC}"
    echo -e "${GREEN}✅ NEXUS is production ready!${NC}"
    exit 0
elif [ $error_count -eq 0 ]; then
    echo -e "${YELLOW}⚠ Production readiness features mostly complete (warnings present)${NC}"
    echo -e "${YELLOW}⚠ Review warnings above${NC}"
    exit 0
else
    echo -e "${RED}❌ Production readiness features incomplete (errors present)${NC}"
    echo -e "${RED}❌ Fix errors above before production deployment${NC}"
    exit 1
fi