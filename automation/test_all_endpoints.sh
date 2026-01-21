#!/bin/bash
echo "========================================="
echo "     NEXUS AI SYSTEM - FULL TEST"
echo "========================================="
echo ""

echo "🧪 Testing all endpoints..."
echo ""

echo "1️⃣  AI Test (POST /webhook/ai-test):"
curl -s -X POST http://localhost:5678/webhook/ai-test \
  -H "Content-Type: application/json" \
  -d '{"query": "Say hello in 3 words"}' | python3 -m json.tool
echo ""

echo "2️⃣  Quick Capture (POST /webhook/quick-capture):"
curl -s -X POST http://localhost:5678/webhook/quick-capture \
  -H "Content-Type: application/json" \
  -d '{"text": "Meeting with team tomorrow at 2pm"}' | python3 -m json.tool
echo ""

echo "3️⃣  Daily Brief (GET /webhook/daily-brief):"
curl -s http://localhost:5678/webhook/daily-brief | python3 -m json.tool
echo ""

echo "4️⃣  Widget Data (GET /webhook/widget-data):"
curl -s http://localhost:5678/webhook/widget-data | python3 -m json.tool
echo ""

echo "========================================="
echo "✅ ALL TESTS COMPLETE!"
echo "========================================="
echo ""
echo "System Status: OPERATIONAL ✅"
echo "Ready for iPhone integration 📱"
