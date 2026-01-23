#!/bin/bash
# View DeepSeek API configuration changes

echo "🔍 DeepSeek API Changes"
echo "======================"
echo ""
echo "DeepSeek is configured in these files:"
echo ""

DEEPSEEK_FILES="app/services/ai.py app/services/config.py app/config.py"

echo "1. Current DeepSeek configuration:"
echo "---------------------------------"
grep -n "deepseek" $DEEPSEEK_FILES -i 2>/dev/null | head -20 || echo "No DeepSeek configuration found"

echo ""
echo "2. Changes to DeepSeek files:"
echo "----------------------------"
for file in $DEEPSEEK_FILES; do
    if [ -f "$file" ]; then
        echo "📄 $file:"
        if git diff --quiet -- "$file"; then
            echo "   ✅ No unstaged changes"
        else
            echo "   📝 Has unstaged changes:"
            git diff -- "$file" | grep -A5 -B5 -i "deepseek" || echo "   (No DeepSeek-related changes)"
        fi
        
        if git diff --cached --quiet -- "$file"; then
            echo "   ✅ No staged changes"
        else
            echo "   📝 Has staged changes:"
            git diff --cached -- "$file" | grep -A5 -B5 -i "deepseek" || echo "   (No DeepSeek-related changes)"
        fi
    else
        echo "📄 $file: Not found"
    fi
    echo ""
done

echo "3. DeepSeek API Models (Chat endpoints):"
echo "---------------------------------------"
echo "DeepSeek is used through general chat endpoints."
echo "Relevant API models:"
python3 -c "
import ast
import sys

def extract_model(filepath, model_name):
    try:
        with open(filepath, 'r') as f:
            tree = ast.parse(f.read())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == model_name:
                print(f'  📋 {model_name}:')
                # Get docstring
                docstring = ast.get_docstring(node)
                if docstring:
                    print(f'     Description: {docstring}')
                # Count fields
                field_count = sum(1 for item in node.body if isinstance(item, ast.AnnAssign))
                print(f'     Fields: {field_count}')
                return True
        return False
    except Exception as e:
        return False

models_to_check = ['ChatRequest', 'ChatResponse']
schema_file = 'app/models/schemas.py'

for model in models_to_check:
    if extract_model(schema_file, model):
        print(f'     (Run: python3 scripts/view_api_models.py | grep -A20 \"MODEL: {model}\" for details)')
    else:
        print(f'  ❌ {model}: Not found in {schema_file}')
"

echo ""
echo "💡 Usage:"
echo "  ./scripts/view_deepseek_changes.sh           # View DeepSeek changes"
echo "  python3 scripts/view_api_models.py --simple  # View all API models"
echo "  git diff -- app/services/ai.py               # View ai.py changes"
