#!/bin/bash
# NEXUS Session End - Fully Automated
# Updates all context, cleans up, commits to GitHub
# Usage: ~/nexus/scripts/end_session.sh

set -e

NEXUS_DIR=~/nexus
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
DATE_ONLY=$(date '+%Y-%m-%d')

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
echo -e "${CYAN}║                    💾 NEXUS SESSION END                                ║${NC}"
echo -e "${CYAN}║                    $TIMESTAMP                              ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

cd $NEXUS_DIR

# Load environment
if [ -f "$NEXUS_DIR/.env" ]; then
    set -a
    source "$NEXUS_DIR/.env"
    set +a
fi

# ═══════════════════════════════════════════════════════════════
# STEP 1: Deep cleanup
# ═══════════════════════════════════════════════════════════════
echo -e "${BLUE}🧹 DEEP CLEANUP${NC}"

# Remove Python cache
find $NEXUS_DIR -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find $NEXUS_DIR -name "*.pyc" -delete 2>/dev/null || true
find $NEXUS_DIR -name "*.pyo" -delete 2>/dev/null || true

# Remove editor temp files
find $NEXUS_DIR -name "*~" -delete 2>/dev/null || true
find $NEXUS_DIR -name "*.swp" -delete 2>/dev/null || true
find $NEXUS_DIR -name "*.swo" -delete 2>/dev/null || true
find $NEXUS_DIR -name ".DS_Store" -delete 2>/dev/null || true

# Remove old log files (keep last 7 days)
find $NEXUS_DIR/logs -name "*.log" -mtime +7 -delete 2>/dev/null || true

# Remove empty directories
find $NEXUS_DIR -type d -empty -delete 2>/dev/null || true

echo -e "${GREEN}   ✅ Cleanup complete${NC}"

# ═══════════════════════════════════════════════════════════════
# STEP 2: Regenerate all context files
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}📄 UPDATING CONTEXT FILES${NC}"

# Generate fresh NEXUS_CONTEXT.md
$NEXUS_DIR/scripts/generate_context.sh

# Update CLAUDE.md header with current state
TABLE_COUNT=$(docker exec nexus-postgres psql -U nexus -d nexus_db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ' || echo "?")
CONTAINER_COUNT=$(docker ps --format "{{.Names}}" | wc -l)

# Create/update header in CLAUDE.md
if [ -f "$NEXUS_DIR/CLAUDE.md" ]; then
    # Check if the first line has our marker, if not add it
    if ! head -1 "$NEXUS_DIR/CLAUDE.md" | grep -q "NEXUS - Philip's AI Operating System"; then
        echo "# NEXUS - Philip's AI Operating System" | cat - "$NEXUS_DIR/CLAUDE.md" > temp && mv temp "$NEXUS_DIR/CLAUDE.md"
    fi
fi

echo -e "${GREEN}   ✅ Context files updated${NC}"

# ═══════════════════════════════════════════════════════════════
# STEP 3: Get session summary
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${YELLOW}What did you accomplish? (Enter to skip)${NC}"
read -r SESSION_SUMMARY

if [ -z "$SESSION_SUMMARY" ]; then
    # Auto-generate summary from git diff
    CHANGED_FILES=$(git diff --name-only HEAD 2>/dev/null | head -5 | tr '\n' ', ' | sed 's/, $//')
    if [ -n "$CHANGED_FILES" ]; then
        SESSION_SUMMARY="Updated: $CHANGED_FILES"
    else
        SESSION_SUMMARY="Session checkpoint"
    fi
fi

# ═══════════════════════════════════════════════════════════════
# STEP 4: Update session log
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}📝 UPDATING SESSION LOG${NC}"

mkdir -p $NEXUS_DIR/docs

# Get current state
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
RECENT_COMMITS=$(git log --oneline -3 2>/dev/null || echo "no commits")
DOCKER_STATUS=$(docker ps --format "{{.Names}}: {{.Status}}" 2>/dev/null | tr '\n' '\n' || echo "Docker not accessible")

# Append to session log
cat >> $NEXUS_DIR/docs/session_log.md << ENDLOG

---

## $TIMESTAMP

**Summary:** $SESSION_SUMMARY

**Branch:** \`$BRANCH\` | **Tables:** $TABLE_COUNT | **Containers:** $CONTAINER_COUNT

<details>
<summary>Recent Commits</summary>

\`\`\`
$RECENT_COMMITS
\`\`\`

</details>

ENDLOG

echo -e "${GREEN}   ✅ Session logged${NC}"

# ═══════════════════════════════════════════════════════════════
# STEP 5: Git commit and push
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}🚀 GIT COMMIT & PUSH${NC}"

if [ -d "$NEXUS_DIR/.git" ]; then
    # Stage all changes
    git add -A
    
    # Check if there's anything to commit
    if git diff --cached --quiet; then
        echo -e "${GREEN}   ✅ No changes to commit${NC}"
    else
        # Show what's being committed
        STAGED=$(git diff --cached --stat | tail -1)
        echo -e "   Staging: $STAGED"
        
        # Commit with smart message
        COMMIT_MSG="session($DATE_ONLY): $SESSION_SUMMARY"
        git commit -m "$COMMIT_MSG" --quiet
        echo -e "${GREEN}   ✅ Committed${NC}"
        
        # Push to remote
        echo -e "   Pushing to GitHub..."
        if git push origin main 2>/dev/null; then
            echo -e "${GREEN}   ✅ Pushed to GitHub${NC}"
        else
            echo -e "${YELLOW}   ⚠️ Push failed (will sync next time)${NC}"
        fi
    fi
else
    echo -e "${YELLOW}   ⚠️ Git not initialized${NC}"
fi

# ═══════════════════════════════════════════════════════════════
# STEP 6: Final status
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✅ SESSION SAVED${NC}"
echo ""
echo -e "Updated files:"
echo -e "  • ${GREEN}NEXUS_CONTEXT.md${NC} - Fresh context for any AI"
echo -e "  • ${GREEN}CLAUDE.md${NC} - Claude Code context"
echo -e "  • ${GREEN}docs/session_log.md${NC} - Session history"
echo -e "  • ${GREEN}Git${NC} - Committed & pushed"
echo ""
echo -e "Next session: ${CYAN}~/nexus/scripts/start_session.sh${NC}"
echo ""
