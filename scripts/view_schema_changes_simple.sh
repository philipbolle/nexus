#!/bin/bash
# Simple script to view schema file changes

echo "🔍 Schema File Changes Viewer"
echo "============================="
echo ""
echo "This script shows changes to API schema files."
echo ""

# Check if we have any changes to schema files
SCHEMA_FILES="app/models/schemas.py app/models/agent_schemas.py"

echo "1. Checking for unstaged changes..."
echo "-----------------------------------"
for file in $SCHEMA_FILES; do
    if git diff --quiet -- "$file"; then
        echo "✅ $file: No unstaged changes"
    else
        echo "📝 $file: HAS UNSTAGED CHANGES"
        git diff -- "$file" | head -100
        echo "..."
    fi
done

echo ""
echo "2. Checking for staged changes..."
echo "--------------------------------"
for file in $SCHEMA_FILES; do
    if git diff --cached --quiet -- "$file"; then
        echo "✅ $file: No staged changes"
    else
        echo "📝 $file: HAS STAGED CHANGES"
        git diff --cached -- "$file" | head -100
        echo "..."
    fi
done

echo ""
echo "3. Recent commits affecting schema files..."
echo "------------------------------------------"
git log --oneline -n 5 -- $SCHEMA_FILES 2>/dev/null || echo "No recent commits found"

echo ""
echo "💡 Quick commands:"
echo "  git diff -- app/models/schemas.py                 # View changes"
echo "  python3 scripts/view_api_models.py --simple       # View all models"
echo "  python3 scripts/view_api_models.py --markdown     # View as markdown"
