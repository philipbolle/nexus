#!/bin/bash
NEXUS_DIR=~/nexus
TIMESTAMP=$(date +%Y-%m-%d_%H:%M)
cd $NEXUS_DIR

echo "💾 NEXUS Session Ending..."
echo ""

# Ask for summary
echo "What did you accomplish? (Enter to skip)"
read -r SUMMARY
[ -z "$SUMMARY" ] && SUMMARY="Session checkpoint"

# Update session log
mkdir -p docs
echo -e "\n---\n## $TIMESTAMP\n$SUMMARY\n" >> docs/session_log.md

# Git commit
if [ -d ".git" ]; then
    git add -A
    if [[ -n $(git status --porcelain) ]]; then
        git commit -m "session: $SUMMARY"
        git push origin main 2>/dev/null || echo "⚠️ Push failed (offline?)"
        echo "✅ Changes committed"
    else
        echo "✅ No changes to commit"
    fi
fi

echo ""
echo "✅ Session saved!"
