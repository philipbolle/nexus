#!/bin/bash
# NEXUS Session End Script
# Run this before closing your coding session
# Usage: ~/nexus/scripts/end_session.sh

set -e

NEXUS_DIR=~/nexus
TIMESTAMP=$(date +%Y-%m-%d_%H:%M:%S)
DATE_ONLY=$(date +%Y-%m-%d)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              💾 NEXUS Session End                             ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

cd $NEXUS_DIR

# 1. Update session log
echo -e "${BLUE}📝 Updating session log...${NC}"

mkdir -p $NEXUS_DIR/docs

# Gather current state
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
CHANGES=$(git status --porcelain 2>/dev/null | wc -l || echo "0")
RECENT_COMMITS=$(git log --oneline -5 2>/dev/null || echo "no commits")
DOCKER_STATUS=$(docker ps --format "{{.Names}}: {{.Status}}" 2>/dev/null || echo "Docker not accessible")
TABLE_COUNT=$(docker exec nexus-postgres psql -U nexus -d nexus_db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ' || echo "?")

# Ask for session summary
echo ""
echo -e "${YELLOW}What did you accomplish this session? (or press Enter to skip)${NC}"
read -r SESSION_SUMMARY

if [ -z "$SESSION_SUMMARY" ]; then
    SESSION_SUMMARY="Session checkpoint"
fi

# Append to session log
cat >> $NEXUS_DIR/docs/session_log.md << ENDLOG

---

## Session: $TIMESTAMP

### Summary
$SESSION_SUMMARY

### Branch
\`$BRANCH\`

### Recent Commits
\`\`\`
$RECENT_COMMITS
\`\`\`

### Container Status
\`\`\`
$DOCKER_STATUS
\`\`\`

### Database
- Tables: $TABLE_COUNT

### Uncommitted Changes
$CHANGES files

ENDLOG

echo -e "${GREEN}   ✅ Session log updated${NC}"

# 2. Stage all changes
echo ""
echo -e "${BLUE}📦 Staging changes...${NC}"

if [ -d "$NEXUS_DIR/.git" ]; then
    # Add all changes
    git add -A
    
    STAGED=$(git diff --cached --stat | tail -1 || echo "nothing")
    echo -e "   $STAGED"
    
    # Check if there's anything to commit
    if [[ -n $(git status --porcelain) ]]; then
        echo ""
        echo -e "${BLUE}💾 Committing changes...${NC}"
        
        # Generate commit message
        COMMIT_MSG="session($DATE_ONLY): $SESSION_SUMMARY"
        
        git commit -m "$COMMIT_MSG"
        echo -e "${GREEN}   ✅ Changes committed${NC}"
        
        # Try to push
        echo ""
        echo -e "${BLUE}🚀 Pushing to remote...${NC}"
        if git push origin main 2>/dev/null; then
            echo -e "${GREEN}   ✅ Pushed to GitHub${NC}"
        else
            echo -e "${YELLOW}   ⚠️ Push failed (offline or no remote?)${NC}"
            echo -e "${YELLOW}      Run later: git push origin main${NC}"
        fi
    else
        echo -e "${GREEN}   ✅ No changes to commit${NC}"
    fi
else
    echo -e "${YELLOW}   ⚠️ Git not initialized${NC}"
fi

# 3. Update .clauderc goals if requested
echo ""
echo -e "${YELLOW}Update current goals in .clauderc? (y/N)${NC}"
read -r UPDATE_GOALS

if [[ "$UPDATE_GOALS" =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${YELLOW}What's the next priority? (or Enter to skip)${NC}"
    read -r NEXT_PRIORITY
    
    if [ -n "$NEXT_PRIORITY" ]; then
        # This is simplified - in practice you'd want to edit the file properly
        echo ""
        echo -e "${YELLOW}Remember to update the 'Current Goals' section in .clauderc${NC}"
        echo -e "${YELLOW}Add: $NEXT_PRIORITY${NC}"
    fi
fi

# 4. Final summary
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✅ Session saved!${NC}"
echo ""
echo -e "Session context preserved in:"
echo -e "  • ${GREEN}docs/session_log.md${NC} - Human-readable log"
echo -e "  • ${GREEN}Git commits${NC} - Code history"
echo -e "  • ${GREEN}.clauderc${NC} - Claude Code context"
echo ""
echo -e "Next session, run: ${GREEN}~/nexus/scripts/start_session.sh${NC}"
echo ""
