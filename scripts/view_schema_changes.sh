#!/bin/bash
# View schema file changes in git

set -e

SCHEMA_FILES="app/models/schemas.py app/models/agent_schemas.py"
COMMIT_RANGE=${1:-""}  # Optional commit range like HEAD~1..HEAD

echo "🔍 Viewing schema changes in NEXUS"
echo "=================================="

if [ -n "$COMMIT_RANGE" ]; then
    echo "Commit range: $COMMIT_RANGE"
    echo ""
    
    for file in $SCHEMA_FILES; do
        if git diff --name-only "$COMMIT_RANGE" | grep -q "$file"; then
            echo "📄 Changes in $file:"
            echo "-------------------"
            git diff "$COMMIT_RANGE" -- "$file"
            echo ""
        else
            echo "📄 No changes in $file"
            echo ""
        fi
    done
else
    echo "Showing unstaged changes:"
    echo "------------------------"
    
    for file in $SCHEMA_FILES; do
        if git diff --name-only -- "$file" | grep -q "$file"; then
            echo "📄 Unstaged changes in $file:"
            echo "----------------------------"
            git diff -- "$file"
            echo ""
        else
            echo "📄 No unstaged changes in $file"
            echo ""
        fi
    done
    
    echo "Showing staged changes:"
    echo "----------------------"
    
    for file in $SCHEMA_FILES; do
        if git diff --cached --name-only -- "$file" | grep -q "$file"; then
            echo "📄 Staged changes in $file:"
            echo "-------------------------"
            git diff --cached -- "$file"
            echo ""
        else
            echo "📄 No staged changes in $file"
            echo ""
        fi
    done
fi

# Also show summary of what models changed
echo ""
echo "📊 Model change summary:"
echo "======================="

# Simple Python script to extract model names from diff
python3 - << 'PYEOF'
import sys
import subprocess
import re

schema_files = ["app/models/schemas.py", "app/models/agent_schemas.py"]
commit_range = sys.argv[1] if len(sys.argv) > 1 else ""

for file in schema_files:
    try:
        if commit_range:
            cmd = ["git", "diff", commit_range, "--", file]
        else:
            cmd = ["git", "diff", "--", file]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        diff_output = result.stdout
        
        # Look for class definitions in diff
        class_pattern = r'^[+\-]\s*class\s+(\w+)\s*\(.*BaseModel'
        classes = re.findall(class_pattern, diff_output, re.MULTILINE)
        
        if classes:
            print(f"\n📄 {file}:")
            for cls in set(classes):
                # Check if added (+) or removed (-)
                added = False
                removed = False
                for line in diff_output.split('\n'):
                    if line.startswith('+') and f"class {cls}(" in line:
                        added = True
                    if line.startswith('-') and f"class {cls}(" in line:
                        removed = True
                
                if added and not removed:
                    print(f"  ➕ Added: {cls}")
                elif removed and not added:
                    print(f"  ➖ Removed: {cls}")
                else:
                    print(f"  🔄 Modified: {cls}")
        else:
            print(f"\n📄 {file}: No model changes")
            
    except Exception as e:
        print(f"\n📄 {file}: Error analyzing - {e}")
PYEOF "$COMMIT_RANGE"

echo ""
echo "💡 Usage:"
echo "  ./scripts/view_schema_changes.sh           # Show unstaged/staged changes"
echo "  ./scripts/view_schema_changes.sh HEAD~1    # Show changes in last commit"
echo "  ./scripts/view_schema_changes.sh main..HEAD # Show changes since main branch"
