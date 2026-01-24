#!/bin/bash
# NEXUS Quick Status - One-liner dashboard
# Philip can run this anytime for instant status

echo "=== NEXUS QUICK STATUS ==="
echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo

# Check if API is running
if curl -s http://localhost:8080/health > /dev/null; then
    echo "✅ API: RUNNING"

    # Get basic health
    HEALTH=$(curl -s http://localhost:8080/health | jq -r '.status' 2>/dev/null || echo "unknown")
    echo "   Health: $HEALTH"

    # Get agent count
    AGENTS=$(curl -s http://localhost:8080/agents | jq -r '.agents | length' 2>/dev/null || echo "0")
    echo "   Agents: $AGENTS"

    # Get finance spending
    BUDGET=$(curl -s http://localhost:8080/finance/budget-status 2>/dev/null || echo '{"total_spent":"0"}')
    SPENT=$(echo "$BUDGET" | jq -r '.total_spent' 2>/dev/null || echo "0")
    echo "   Spent this month: \$$SPENT"

    # Get system metrics
    METRICS=$(curl -s http://localhost:8080/metrics/system 2>/dev/null || echo '{}')
    CPU=$(echo "$METRICS" | jq -r '.cpu.percent' 2>/dev/null || echo "0")
    MEM=$(echo "$METRICS" | jq -r '.memory.used_percent' 2>/dev/null || echo "0")
    echo "   System: CPU ${CPU}%, Mem ${MEM}%"

else
    echo "❌ API: NOT RUNNING"
    echo "   Run: sudo systemctl start nexus-api"
fi

echo
echo "=== QUICK COMMANDS ==="
echo "• Full dashboard: python3 scripts/nexus_status_simple.py"
echo "• Check logs: sudo journalctl -u nexus-api -f"
echo "• Restart API: sudo systemctl restart nexus-api"
echo "• View docs: http://localhost:8080/docs"