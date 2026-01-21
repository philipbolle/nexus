#!/bin/bash
# NEXUS iPhone Workflow Import Script
# Imports photo_vision and screenshot_helper workflows to n8n

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "  NEXUS iPhone Workflow Import Script"
echo "=========================================="
echo ""

# Check if n8n container is running
if ! docker ps | grep -q nexus-n8n; then
    echo -e "${RED}ERROR: nexus-n8n container is not running${NC}"
    echo "Start it with: cd ~/nexus && docker compose up -d"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} n8n container is running"
echo ""

# Import Photo Vision workflow
echo "Importing Photo Vision (Gemini 2.5 Flash)..."
if docker exec -i nexus-n8n n8n import:workflow --input=/dev/stdin < "$SCRIPT_DIR/photo_vision.json" 2>/dev/null; then
    echo -e "${GREEN}[OK]${NC} Photo Vision workflow imported"
else
    echo -e "${YELLOW}[WARN]${NC} Photo Vision may already exist or import had issues"
fi

# Import Screenshot Helper workflow
echo "Importing Screenshot Helper (Gemini 2.5 Flash)..."
if docker exec -i nexus-n8n n8n import:workflow --input=/dev/stdin < "$SCRIPT_DIR/screenshot_helper.json" 2>/dev/null; then
    echo -e "${GREEN}[OK]${NC} Screenshot Helper workflow imported"
else
    echo -e "${YELLOW}[WARN]${NC} Screenshot Helper may already exist or import had issues"
fi

echo ""
echo "=========================================="
echo "  Import Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Open n8n: http://localhost:5678"
echo "2. Activate both workflows (toggle in top-right)"
echo "3. Test endpoints:"
echo ""
echo "  Photo Vision (Gemini 2.5 Flash):"
echo "    POST http://localhost:5678/webhook/photo-vision"
echo "    Body: {\"image\": \"<base64>\", \"mime_type\": \"image/png\", \"prompt\": \"Describe this image\"}"
echo ""
echo "  Screenshot Helper (Gemini 2.5 Flash):"
echo "    POST http://localhost:5678/webhook/screenshot-helper"
echo "    Body: {\"image\": \"<base64>\", \"mime_type\": \"image/png\", \"prompt\": \"Help me with this screenshot\"}"
echo ""
echo "From iPhone via Tailscale, use: http://100.94.29.101:5678"
echo ""
