#!/bin/bash
# Simple wrapper script for viewing NEXUS API models
# Usage: ./view_models.sh [format]
#   format: simple, markdown, or text (default)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/view_api_models.py"

# Default format
FORMAT="text"

# Parse command line arguments
if [ $# -gt 0 ]; then
    case "$1" in
        "simple"|"-s"|"--simple")
            FORMAT="simple"
            ;;
        "markdown"|"-m"|"--markdown")
            FORMAT="markdown"
            ;;
        "text"|"-t"|"--text")
            FORMAT="text"
            ;;
        "help"|"-h"|"--help")
            echo "NEXUS API Model Viewer"
            echo "Usage: $0 [format]"
            echo ""
            echo "Formats:"
            echo "  simple    - Simple summary of models"
            echo "  markdown  - Detailed markdown format"
            echo "  text      - Detailed text format (default)"
            echo ""
            echo "Examples:"
            echo "  $0              # Show all models in text format"
            echo "  $0 simple       # Show simple summary"
            echo "  $0 markdown     # Show markdown format"
            exit 0
            ;;
        *)
            echo "Unknown format: $1"
            echo "Use: simple, markdown, or text"
            exit 1
            ;;
    esac
fi

# Run the Python script with appropriate arguments
case "$FORMAT" in
    "simple")
        python3 "$PYTHON_SCRIPT" --simple
        ;;
    "markdown")
        python3 "$PYTHON_SCRIPT" --markdown
        ;;
    "text")
        python3 "$PYTHON_SCRIPT"
        ;;
esac